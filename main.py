import os
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.suppliers import ALL_SUPPLIERS
from crawlers.rss_crawler import crawl_rss
from crawlers.tavily_crawler import crawl_tavily
from crawlers.edgar_crawler import crawl_edgar
from processors.signal_detector import detect_signals
from storage.redis_store import RedisStore


store = RedisStore()


def run_rss_cycle():
    print("[Main] Running RSS cycle...")
    items = crawl_rss(store)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)


def run_edgar_cycle():
    print("[Main] Running EDGAR cycle...")
    items = crawl_edgar(store)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)


def run_tavily_weekly():
    # Tier 1+2 only — ~177 searches/week, ~700/month, within Tavily free tier
    print("[Main] Running Tavily weekly cycle (Tier 1+2)...")
    items = crawl_tavily(store, tier=2)
    if items:
        enriched = detect_signals(items)
        store.store_items(enriched)


if __name__ == "__main__":
    print(f"[Hermes] Starting — monitoring {len(ALL_SUPPLIERS)} suppliers")

    run_rss_cycle()
    run_edgar_cycle()

    scheduler = BlockingScheduler(timezone="Europe/Berlin")
    scheduler.add_job(run_rss_cycle,      CronTrigger(hour="0,6,12,18", minute=0))
    scheduler.add_job(run_edgar_cycle,    CronTrigger(hour="7", minute=30))
    scheduler.add_job(run_tavily_weekly,  CronTrigger(day_of_week="mon", hour="9", minute=0))

    print("[Hermes] Scheduler running")
    scheduler.start()
