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
from crawlers.jobs_crawler import crawl_jobs
from crawlers.rss_crawler import crawl_rss
from crawlers.tavily_crawler import crawl_tavily
from crawlers.transcripts_crawler import crawl_transcripts
from notifications.zeus_notifier import notify_zeus_if_significant
from processors.signal_detector import detect_signals
from storage.redis_store import RedisStore

store = RedisStore()
scheduler = BackgroundScheduler(timezone="Europe/Berlin")

HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")
if not HERMES_API_KEY:
    log.warning("HERMES_API_KEY is not set — API is unauthenticated and open to anyone")


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
        notify_zeus_if_significant(enriched)
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
        notify_zeus_if_significant(enriched)
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
        notify_zeus_if_significant(enriched)
    else:
        log.info("Tavily cycle complete — 0 new items")


def run_jobs_weekly():
    log.info("Jobs crawl starting (Tier 1+2)")
    items = crawl_jobs(store, tier=2)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"Jobs crawl complete — {len(enriched)} items stored, {sig} significant")
        notify_zeus_if_significant(enriched)
    else:
        log.info("Jobs crawl complete — 0 new postings")


def run_watchlist_rss():
    """High-frequency RSS crawl scoped to watchlisted companies only."""
    slugs = store.watchlist_get()
    if not slugs:
        return
    from config.suppliers import ALL_SUPPLIERS

    watched = [s for s in ALL_SUPPLIERS if s["name"].lower().replace(" ", "_") in slugs]
    if not watched:
        return
    log.info(f"Watchlist RSS crawl — {len(watched)} companies")
    items = crawl_rss(store, suppliers_override=watched)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        notify_zeus_if_significant(enriched)
        log.info(
            f"Watchlist RSS done — {len(enriched)} items, {sum(1 for i in enriched if i.get('is_significant'))} significant"
        )


def run_weekly_digest():
    """Generate and store the weekly digest every Sunday at 18:00."""
    log.info("Weekly digest generation starting")
    try:
        from intelligence.digest import build_weekly_digest, store_digest

        digest = build_weekly_digest(store)
        store_digest(store.r, digest)
        log.info("Weekly digest stored successfully")
    except Exception as e:
        log.error(f"Weekly digest failed: {e}")


def run_transcripts_weekly():
    log.info("Earnings transcripts crawl starting (Tier 1+2)")
    items = crawl_transcripts(store)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)
        sig = sum(1 for i in enriched if i.get("is_significant"))
        log.info(f"Transcripts crawl complete — {len(enriched)} items stored, {sig} significant")
    else:
        log.info("Transcripts crawl complete — 0 new filings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Hermes starting — monitoring {len(ALL_SUPPLIERS)} suppliers")
    scheduler.add_job(run_rss_cycle, CronTrigger(hour="0,6,12,18", minute=0))
    scheduler.add_job(run_edgar_cycle, CronTrigger(hour="7", minute=30))
    scheduler.add_job(run_tavily_weekly, CronTrigger(day_of_week="mon", hour="9", minute=0))
    scheduler.add_job(run_jobs_weekly, CronTrigger(day_of_week="wed", hour="9", minute=0))
    scheduler.add_job(run_transcripts_weekly, CronTrigger(day_of_week="thu", hour="8", minute=0))
    scheduler.add_job(
        run_watchlist_rss, CronTrigger(hour="1,3,5,7,9,11,13,15,17,19,21,23", minute=0)
    )
    scheduler.add_job(run_weekly_digest, CronTrigger(day_of_week="sun", hour="18", minute=0))
    scheduler.start()
    log.info(
        "Scheduler running — RSS @0/6/12/18h, EDGAR @07:30, "
        "Tavily Mon @09:00, Jobs Wed @09:00, Transcripts Thu @08:00, "
        "Watchlist @odd hours, Digest Sun @18:00"
    )
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


@app.post("/crawl/jobs")
def trigger_jobs(x_api_key: str = Header(default=None)):
    """Trigger an immediate job postings crawl (runs in background)."""
    _auth(x_api_key)
    threading.Thread(target=run_jobs_weekly, daemon=True).start()
    return {"status": "started", "crawler": "jobs"}


@app.post("/crawl/transcripts")
def trigger_transcripts(x_api_key: str = Header(default=None)):
    """Trigger an immediate earnings transcripts crawl (runs in background)."""
    _auth(x_api_key)
    threading.Thread(target=run_transcripts_weekly, daemon=True).start()
    return {"status": "started", "crawler": "transcripts"}


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


@app.get("/clusters")
def get_clusters(refresh: bool = False, x_api_key: str = Header(default=None)):
    """
    Return macro theme clusters across recent significant signals.
    Results are cached in Redis for 6 hours. Pass ?refresh=true to force rebuild.
    """
    _auth(x_api_key)
    import json as _json
    from datetime import date

    cache_key = f"hermes:clusters:{date.today().isoformat()}"
    if not refresh:
        cached = store.r.get(cache_key)
        if cached:
            log.info("Clusters: returning cached result")
            return {"clusters": _json.loads(cached), "cached": True}

    from intelligence.clusters import build_clusters
    from intelligence.trends import save_weekly_snapshot

    clusters = build_clusters(store)
    store.r.set(cache_key, _json.dumps(clusters), ex=60 * 60 * 6)  # 6h TTL
    try:
        save_weekly_snapshot(store.r, clusters)
    except Exception as e:
        log.warning(f"Weekly snapshot save failed: {e}")
    return {"clusters": clusters, "cached": False}


@app.get("/digest")
def get_digest(refresh: bool = False, x_api_key: str = Header(default=None)):
    """Return the latest weekly digest. Pass ?refresh=true to regenerate now."""
    _auth(x_api_key)
    if refresh:
        threading.Thread(target=run_weekly_digest, daemon=True).start()
        return {
            "status": "regenerating",
            "message": "Digest rebuild started — check back in ~30 seconds.",
        }
    from intelligence.digest import get_latest_digest

    digest = get_latest_digest(store.r)
    if not digest:
        return {
            "digest": None,
            "message": "No digest yet — will generate Sunday at 18:00 or use ?refresh=true.",
        }
    return {"digest": digest}


@app.get("/trends/delta")
def trends_delta(x_api_key: str = Header(default=None)):
    """Compare this week's clusters to last week's — new, continuing, resolved."""
    _auth(x_api_key)
    from intelligence.trends import build_delta

    return build_delta(store.r)


@app.get("/watchlist")
def get_watchlist(x_api_key: str = Header(default=None)):
    """Return all watchlisted company slugs."""
    _auth(x_api_key)
    slugs = store.watchlist_get()
    return {"watchlist": slugs, "count": len(slugs)}


@app.post("/watchlist/{company}")
def add_to_watchlist(company: str, x_api_key: str = Header(default=None)):
    """Add a company to the watchlist for high-frequency crawling."""
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    store.watchlist_add(slug)
    return {"status": "added", "slug": slug}


@app.delete("/watchlist/{company}")
def remove_from_watchlist(company: str, x_api_key: str = Header(default=None)):
    """Remove a company from the watchlist."""
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    store.watchlist_remove(slug)
    return {"status": "removed", "slug": slug}


@app.post("/enrich/{company}")
def enrich_company(company: str, x_api_key: str = Header(default=None)):
    """Enrich a company profile with structured intelligence extracted by Claude Haiku."""
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    known = store.list_profile_slugs()
    if slug not in known:
        matches = get_close_matches(slug, known, n=1, cutoff=0.6)
        if not matches:
            raise HTTPException(status_code=404, detail=f"No profile for '{company}' yet.")
        slug = matches[0]
    from intelligence.enrichment import enrich_profile

    profile = enrich_profile(store, slug)
    return {"company": slug.replace("_", " ").title(), "profile": profile}


@app.get("/profile/{company}")
def get_profile(company: str, x_api_key: str = Header(default=None)):
    """Return accumulated knowledge profile for a company."""
    _auth(x_api_key)
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    known = store.list_profile_slugs()
    if slug not in known:
        matches = get_close_matches(slug, known, n=1, cutoff=0.6)
        if not matches:
            return {
                "company": company,
                "profile": None,
                "message": f"No profile for '{company}' yet — will build as crawlers run.",
            }
        slug = matches[0]
    profile = store.get_profile(slug)
    return {"company": slug.replace("_", " ").title(), "profile": profile}


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
