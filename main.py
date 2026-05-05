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
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("hermes")

from config.suppliers import ALL_SUPPLIERS
from crawlers.edgar_crawler import crawl_edgar
from crawlers.rss_crawler import crawl_rss
from crawlers.tavily_crawler import crawl_tavily
from processors.signal_detector import detect_signals
from storage.redis_store import RedisStore

store = RedisStore()
scheduler = BackgroundScheduler(timezone="Europe/Berlin")

HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")


def _auth(x_api_key: str = Header(default=None)):
    if HERMES_API_KEY and x_api_key != HERMES_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def run_rss_cycle():
    log.info("RSS cycle starting")
    items = crawl_rss(store)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"RSS cycle complete — {len(enriched)} items stored, {sig} significant")
    else:
        log.info("RSS cycle complete — 0 new items")


def run_edgar_cycle():
    log.info("EDGAR cycle starting")
    items = crawl_edgar(store)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"EDGAR cycle complete — {len(enriched)} items stored, {sig} significant")
    else:
        log.info("EDGAR cycle complete — 0 new filings")


def run_tavily_weekly():
    log.info("Tavily weekly cycle starting (Tier 1+2)")
    items = crawl_tavily(store, tier=2)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"Tavily cycle complete — {len(enriched)} items stored, {sig} significant")
    else:
        log.info("Tavily cycle complete — 0 new items")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Hermes starting — monitoring {len(ALL_SUPPLIERS)} suppliers")
    scheduler.add_job(run_rss_cycle, CronTrigger(hour="0,6,12,18", minute=0))
    scheduler.add_job(run_edgar_cycle, CronTrigger(hour="7", minute=30))
    scheduler.add_job(run_tavily_weekly, CronTrigger(day_of_week="mon", hour="9", minute=0))
    scheduler.start()
    log.info("Scheduler running — RSS @0/6/12/18h, EDGAR @07:30, Tavily Mon @09:00")
    yield
    scheduler.shutdown()
    log.info("Hermes shutdown")


app = FastAPI(title="Hermes Agent", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "suppliers": len(ALL_SUPPLIERS)}


@app.get("/greet")
def greet():
    """Hermes introduces himself to Icarus with live stats."""
    total_items = store.count_items()
    significant = store.get_significant_items(limit=500)
    sig_count = len(significant)
    top_signal = significant[0] if significant else None
    top_line = (
        f"Latest signal: {top_signal['supplier']} — {top_signal['title'][:80]}"
        if top_signal
        else "No signals yet."
    )
    return {
        "from": "Hermes",
        "to": "Icarus",
        "message": (
            f"Hermes online. I'm tracking {len(ALL_SUPPLIERS)} suppliers across 17 categories. "
            f"{total_items} signals in memory, {sig_count} significant. "
            f"Crawlers: RSS every 6h, EDGAR daily at 07:30, Tavily weekly on Mondays. "
            f"I store everything in Redis and wait to be asked. Ready to serve."
        ),
        "stats": {
            "suppliers": len(ALL_SUPPLIERS),
            "total_items": total_items,
            "significant_items": sig_count,
        },
        "latest": top_line,
    }


@app.post("/crawl/rss")
def trigger_rss(x_api_key: str = Header(default=None)):
    """Trigger an immediate RSS crawl cycle (runs in background)."""
    _auth(x_api_key)
    threading.Thread(target=run_rss_cycle, daemon=True).start()
    return {"status": "started", "crawler": "rss"}


@app.post("/crawl/tavily")
def trigger_tavily(x_api_key: str = Header(default=None)):
    """Trigger an immediate Tavily crawl cycle (runs in background)."""
    _auth(x_api_key)
    threading.Thread(target=run_tavily_weekly, daemon=True).start()
    return {"status": "started", "crawler": "tavily"}


@app.post("/crawl/edgar")
def trigger_edgar(x_api_key: str = Header(default=None)):
    """Trigger an immediate EDGAR crawl cycle (runs in background)."""
    _auth(x_api_key)
    threading.Thread(target=run_edgar_cycle, daemon=True).start()
    return {"status": "started", "crawler": "edgar"}


@app.get("/query/{company}")
def query_company(company: str, limit: int = 5, x_api_key: str = Header(default=None)):
    """Return recent signals for a specific company."""
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    known_slugs = store.list_supplier_slugs()
    if slug not in known_slugs:
        matches = get_close_matches(slug, known_slugs, n=1, cutoff=0.6)
        if not matches:
            return {
                "company": company,
                "signals": [],
                "message": f"No data for '{company}' — not tracked yet.",
            }
        slug = matches[0]
    signals = store.get_items_by_slug(slug, limit=limit)
    return {"company": slug.replace("_", " ").title(), "signals": signals}


@app.get("/briefing")
def briefing(limit: int = 10, x_api_key: str = Header(default=None)):
    """Return top significant signals across all suppliers."""
    _auth(x_api_key)
    items = store.get_significant_items(limit=limit)
    return {"count": len(items), "signals": items}


@app.get("/search")
def semantic_search(q: str, limit: int = 10, x_api_key: str = Header(default=None)):
    """Semantic search across all stored signals using natural language."""
    _auth(x_api_key)
    if not store.index:
        raise HTTPException(status_code=503, detail="Vector index not configured")
    results = store.semantic_search(q, limit=limit)
    return {"query": q, "count": len(results), "results": results}


@app.post("/flush")
def flush(x_api_key: str = Header(default=None)):
    """Delete all stored items from Redis and the vector index for a clean start."""
    _auth(x_api_key)
    store.flush()
    return {"status": "flushed", "message": "All hermes data cleared. Ready for a fresh crawl."}


@app.get("/chart/signals")
def chart_signals(x_api_key: str = Header(default=None)):
    """QuickChart image URL — significant signals by urgency. Send as photo in Telegram."""
    _auth(x_api_key)
    from charts.quickchart import build_signals_chart

    url = build_signals_chart(store)
    return {"url": url, "chart_type": "signals"}


@app.get("/chart/landscape")
def chart_landscape(x_api_key: str = Header(default=None)):
    """QuickChart image URL — item counts by category (top 10). Send as photo in Telegram."""
    _auth(x_api_key)
    from charts.quickchart import build_landscape_chart

    url = build_landscape_chart(store)
    return {"url": url, "chart_type": "landscape"}


