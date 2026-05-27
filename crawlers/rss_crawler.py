import hashlib
import logging
from datetime import UTC, datetime

import feedparser
import httpx

from config.suppliers import AI_EXTRA_SOURCES, ALL_SUPPLIERS, INDUSTRY_FEEDS

log = logging.getLogger("hermes.rss")

FEED_TIMEOUT = 8  # seconds per HTTP request
MAX_FEED_BYTES = 512_000  # 512KB max — prevents feedparser hanging on huge feeds


def _hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_feed(feed_url: str, supplier_name: str) -> list[dict]:
    try:
        with httpx.Client(
            timeout=FEED_TIMEOUT, follow_redirects=True, headers={"User-Agent": "Hermes-Agent/1.0"}
        ) as client:
            response = client.get(feed_url)
            response.raise_for_status()
            content = response.text[:MAX_FEED_BYTES]
        feed = feedparser.parse(content)
        results = []
        for entry in feed.entries[:10]:
            results.append(
                {
                    "id": _hash(entry.get("link", entry.get("id", ""))),
                    "supplier": supplier_name,
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:500],
                    "published": entry.get("published", datetime.now(UTC).isoformat()),
                    "source": "rss",
                }
            )
        return results
    except Exception as e:
        log.warning(f"Feed failed — {supplier_name}: {e}")
        return []


def crawl_rss(
    redis_store,
    suppliers_override: list[dict] | None = None,
    require_ticker: bool = False,
) -> list[dict]:
    if suppliers_override is not None:
        sources = [s for s in suppliers_override if s.get("rss")]
    else:
        sources = [s for s in ALL_SUPPLIERS if s.get("rss")] + AI_EXTRA_SOURCES + INDUSTRY_FEEDS

    # require_ticker: only keep items from sources that have a known stock ticker
    if require_ticker:
        sources = [s for s in sources if s.get("ticker")]

    new_items = []
    failed = 0

    for source in sources:
        name = source["name"]
        rss_url = source["rss"]
        ticker = source.get("ticker")
        items = _parse_feed(rss_url, name)
        if not items:
            failed += 1
        for item in items:
            if ticker:
                item.setdefault("ticker", ticker)
            if not redis_store.is_seen(item["id"]):
                redis_store.mark_seen(item["id"])
                new_items.append(item)

    log.info(f"RSS crawl done — {len(new_items)} new items, {failed}/{len(sources)} feeds failed")
    return new_items
