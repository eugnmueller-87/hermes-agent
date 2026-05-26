import logging
import os
import threading
from contextlib import asynccontextmanager
from difflib import get_close_matches

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hermes")

from config.suppliers import SUPPLIERS
from crawlers.rss_crawler import crawl_rss
from crawlers.tavily_crawler import crawl_tavily
from notifications.zeus_notifier import notify_zeus_if_significant
from processors.signal_detector import detect_signals
from storage.redis_store import RedisStore

AI_CATEGORIES = {
    "ai_foundation_labs", "ai_infrastructure_chips", "ai_agents_orchestration",
    "ai_developer_tools", "ai_coding", "ai_search_research", "ai_voice_multimodal",
    "ai_rising_stars",
}
AI_SUPPLIERS = [s for cat, suppliers in SUPPLIERS.items() if cat in AI_CATEGORIES for s in suppliers]

store = RedisStore()
scheduler = BackgroundScheduler(timezone="Europe/Berlin")

HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")
if not HERMES_API_KEY:
    log.warning("HERMES_API_KEY is not set - API is unauthenticated")


def _auth(x_api_key: str = Header(default=None)):
    if HERMES_API_KEY and x_api_key != HERMES_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def run_rss_cycle():
    log.info(f"RSS cycle starting - {len(AI_SUPPLIERS)} AI suppliers")
    items = crawl_rss(store, suppliers_override=AI_SUPPLIERS)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"RSS cycle complete - {len(enriched)} items stored, {sig} significant")
        notify_zeus_if_significant(enriched)
    else:
        log.info("RSS cycle complete - 0 new items")


def run_tavily_weekly():
    log.info("Tavily cycle starting (Tier 1 AI only)")
    items = crawl_tavily(store, tier=1)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"Tavily cycle complete - {len(enriched)} items stored, {sig} significant")
        notify_zeus_if_significant(enriched)
    else:
        log.info("Tavily cycle complete - 0 new items")


def run_weekly_digest():
    log.info("Weekly digest generation starting")
    try:
        from intelligence.digest import build_weekly_digest, store_digest
        digest = build_weekly_digest(store)
        store_digest(store.r, digest)
        log.info("Weekly digest stored successfully")
    except Exception as e:
        log.error(f"Weekly digest failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Hermes starting - tracking {len(AI_SUPPLIERS)} AI suppliers")
    scheduler.add_job(run_rss_cycle, CronTrigger(day_of_week="fri", hour=5, minute=0))
    scheduler.add_job(run_weekly_digest, CronTrigger(day_of_week="sun", hour=18, minute=0))
    scheduler.start()
    log.info("Scheduler running - AI RSS Fri @05:00, Digest Sun @18:00")
    yield
    scheduler.shutdown()
    log.info("Hermes shutdown")


app = FastAPI(title="Hermes Agent", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "suppliers": len(AI_SUPPLIERS)}


@app.get("/greet")
def greet():
    total_items = store.count_items()
    significant = store.get_significant_items(limit=500)
    sig_count = len(significant)
    top_signal = significant[0] if significant else None
    top_line = (
        f"Latest signal: {top_signal['supplier']} - {top_signal['title'][:80]}"
        if top_signal else "No signals yet."
    )
    return {
        "from": "Hermes",
        "to": "Icarus",
        "message": (
            f"Hermes online. Tracking {len(AI_SUPPLIERS)} AI suppliers across 8 categories. "
            f"{total_items} signals in memory, {sig_count} significant. "
            f"Crawlers: RSS every Friday at 05:00. Digest every Sunday at 18:00."
        ),
        "stats": {"suppliers": len(AI_SUPPLIERS), "total_items": total_items, "significant_items": sig_count},
        "latest": top_line,
    }


@app.post("/crawl/rss")
def trigger_rss(x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    threading.Thread(target=run_rss_cycle, daemon=True).start()
    return {"status": "started", "crawler": "rss"}


@app.post("/crawl/tavily")
def trigger_tavily(x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    threading.Thread(target=run_tavily_weekly, daemon=True).start()
    return {"status": "started", "crawler": "tavily"}


@app.get("/query/{company}")
def query_company(company: str, limit: int = 5, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    known_slugs = store.list_supplier_slugs()
    if slug not in known_slugs:
        matches = get_close_matches(slug, known_slugs, n=1, cutoff=0.6)
        if not matches:
            return {"company": company, "signals": [], "message": f"No data for '{company}' - not tracked yet."}
        slug = matches[0]
    signals = store.get_items_by_slug(slug, limit=limit)
    return {"company": slug.replace("_", " ").title(), "signals": signals}


@app.get("/briefing")
def briefing(limit: int = 10, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    items = store.get_significant_items(limit=limit)
    return {"count": len(items), "signals": items}


@app.get("/search")
def semantic_search(q: str, limit: int = 10, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    if not store.index:
        raise HTTPException(status_code=503, detail="Vector index not configured")
    results = store.semantic_search(q, limit=limit)
    return {"query": q, "count": len(results), "results": results}


@app.get("/watchlist")
def get_watchlist(x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    slugs = store.watchlist_get()
    return {"watchlist": slugs, "count": len(slugs)}


@app.post("/watchlist/{company}")
def add_to_watchlist(company: str, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    store.watchlist_add(slug)
    return {"status": "added", "slug": slug}


@app.delete("/watchlist/{company}")
def remove_from_watchlist(company: str, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    store.watchlist_remove(slug)
    return {"status": "removed", "slug": slug}


@app.get("/digest")
def get_digest(refresh: bool = False, x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    if refresh:
        threading.Thread(target=run_weekly_digest, daemon=True).start()
        return {"status": "regenerating", "message": "Digest rebuild started - check back in ~30 seconds."}
    from intelligence.digest import get_latest_digest
    digest = get_latest_digest(store.r)
    if not digest:
        return {"digest": None, "message": "No digest yet - will generate Sunday at 18:00 or use ?refresh=true."}
    return {"digest": digest}


@app.post("/flush")
def flush(x_api_key: str = Header(default=None)):
    _auth(x_api_key)
    store.flush()
    return {"status": "flushed", "message": "All hermes data cleared. Ready for a fresh crawl."}
