import os
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Header
from dotenv import load_dotenv

load_dotenv()

from config.suppliers import ALL_SUPPLIERS
from crawlers.rss_crawler import crawl_rss
from crawlers.tavily_crawler import crawl_tavily
from crawlers.edgar_crawler import crawl_edgar
from processors.signal_detector import detect_signals
from storage.redis_store import RedisStore

store = RedisStore()
scheduler = BackgroundScheduler(timezone="Europe/Berlin")

HERMES_API_KEY = os.environ.get("HERMES_API_KEY", "")


def _auth(x_api_key: str = Header(default=None)):
    if HERMES_API_KEY and x_api_key != HERMES_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def run_rss_cycle():
    print("[Main] Running RSS cycle...")
    items = crawl_rss(store)
    if items:
        store.store_items(detect_signals(items))


def run_edgar_cycle():
    print("[Main] Running EDGAR cycle...")
    items = crawl_edgar(store)
    if items:
        store.store_items(detect_signals(items))


def run_tavily_weekly():
    # Tier 1+2 only — ~177 searches/week, ~700/month, within Tavily free tier
    print("[Main] Running Tavily weekly cycle (Tier 1+2)...")
    items = crawl_tavily(store, tier=2)
    if items:
        store.store_items(detect_signals(items))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[Hermes] Starting — monitoring {len(ALL_SUPPLIERS)} suppliers")
    run_rss_cycle()
    run_edgar_cycle()
    scheduler.add_job(run_rss_cycle,     CronTrigger(hour="0,6,12,18", minute=0))
    scheduler.add_job(run_edgar_cycle,   CronTrigger(hour="7",          minute=30))
    scheduler.add_job(run_tavily_weekly, CronTrigger(day_of_week="mon", hour="9", minute=0))
    scheduler.start()
    print("[Hermes] Scheduler running")
    yield
    scheduler.shutdown()


app = FastAPI(title="Hermes Agent", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "suppliers": len(ALL_SUPPLIERS)}


@app.get("/greet")
def greet():
    """Hermes introduces himself to Icarus with live stats."""
    total_items = len(store.r.keys("hermes:item:*"))
    significant = store.get_significant_items(limit=500)
    sig_count = len(significant)
    top_signal = significant[0] if significant else None
    top_line = (
        f"Latest signal: {top_signal['supplier']} — {top_signal['title'][:80]}"
        if top_signal else "No signals yet."
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
    import threading
    threading.Thread(target=run_rss_cycle, daemon=True).start()
    return {"status": "started", "crawler": "rss"}


@app.post("/crawl/edgar")
def trigger_edgar(x_api_key: str = Header(default=None)):
    """Trigger an immediate EDGAR crawl cycle (runs in background)."""
    _auth(x_api_key)
    import threading
    threading.Thread(target=run_edgar_cycle, daemon=True).start()
    return {"status": "started", "crawler": "edgar"}


@app.get("/query/{company}")
def query_company(company: str, limit: int = 5, x_api_key: str = Header(default=None)):
    """Return recent signals for a specific company."""
    _auth(x_api_key)
    from difflib import get_close_matches
    slug = company.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")
    if not store.r.exists(f"hermes:supplier:{slug}"):
        keys = store.r.keys("hermes:supplier:*")
        known = [k.replace("hermes:supplier:", "") for k in keys]
        matches = get_close_matches(slug, known, n=1, cutoff=0.6)
        if not matches:
            return {"company": company, "signals": [], "message": f"No data for '{company}' — not tracked yet."}
        slug = matches[0]
    ids = store.r.lrange(f"hermes:supplier:{slug}", 0, limit - 1)
    signals = []
    for item_id in ids:
        raw = store.r.get(f"hermes:item:{item_id}")
        if raw:
            import json
            signals.append(json.loads(raw))
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


@app.post("/miro/landscape")
def miro_landscape(category: str = None, x_api_key: str = Header(default=None)):
    """Build a Miro landscape board. Pass ?category=AI+Foundation+Labs to filter."""
    _auth(x_api_key)
    from miro.boards import build_landscape_board
    url = build_landscape_board(store, category_filter=category)
    return {"url": url, "category": category or "All Categories"}


@app.post("/miro/signals")
def miro_signals(x_api_key: str = Header(default=None)):
    """Build a Miro signal board from today's significant Hermes items."""
    _auth(x_api_key)
    from miro.boards import build_signal_board
    url = build_signal_board(store)
    return {"url": url}
