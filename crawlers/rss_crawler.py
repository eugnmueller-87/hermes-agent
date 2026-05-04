import feedparser
import hashlib
import httpx
from datetime import datetime, timezone
from config.suppliers import ALL_SUPPLIERS, AI_EXTRA_SOURCES


def _hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_feed(feed_url: str, supplier_name: str) -> list[dict]:
    try:
        feed = feedparser.parse(feed_url)
        results = []
        for entry in feed.entries[:10]:
            results.append({
                "id": _hash(entry.get("link", entry.get("id", ""))),
                "supplier": supplier_name,
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", "")[:500],
                "published": entry.get("published", datetime.now(timezone.utc).isoformat()),
                "source": "rss",
            })
        return results
    except Exception as e:
        print(f"[RSS] Failed {supplier_name}: {e}")
        return []


def crawl_rss(redis_store) -> list[dict]:
    sources = [s for s in ALL_SUPPLIERS if s.get("rss")] + AI_EXTRA_SOURCES
    new_items = []

    for source in sources:
        name = source["name"]
        rss_url = source["rss"]
        items = _parse_feed(rss_url, name)

        for item in items:
            if not redis_store.is_seen(item["id"]):
                redis_store.mark_seen(item["id"])
                new_items.append(item)

    print(f"[RSS] Found {len(new_items)} new items")
    return new_items
