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
