import hashlib
import logging
from datetime import UTC, datetime

import feedparser
import httpx

from config.suppliers import ALL_SUPPLIERS, INDUSTRY_FEEDS

log = logging.getLogger("hermes.rss")

FEED_TIMEOUT = 15  # seconds per HTTP request
MAX_FEED_BYTES = 2_000_000  # 2MB max — large enough for any RSS feed (OpenAI is ~574KB)

# Title/summary keywords that reliably indicate non-market-moving content.
# These burn LLM tokens and produce low-quality signals — filter before classify.
_JUNK_TITLE_KEYWORDS = [
    # Consumer / personal finance (very common in Yahoo Finance, MarketWatch)
    "mortgage", "heloc", "home equity", "credit card", "auto loan", "car loan",
    "personal loan", "student loan", "savings account", "cd rate", "interest rate today",
    "best rate", "refinance your", "how to save", "how to invest", "retire",
    "social security", "medicare", "tax refund", "tax return",
    # Opinion / lifestyle
    "you need to", "you should", "why you", "here's why", "here are",
    "the best ", "best stocks to", "stocks to buy", "stocks to watch",
    "analyst says", "according to", "experts say", "opinion:", "column:",
    "commentary:", "editorial:", "perspective:",
    # Generic how-to / explainer
    "what is a ", "what is the ", "how does ", "guide to", "explained",
    "everything you need", "beginner", "101:",
]


def _is_junk(title: str, summary: str) -> bool:
    """Return True if this article is almost certainly non-market-moving junk."""
    text = (title + " " + summary).lower()
    return any(kw in text for kw in _JUNK_TITLE_KEYWORDS)


def _hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _parse_feed(feed_url: str, supplier_name: str) -> list[dict]:
    try:
        with httpx.Client(
            timeout=FEED_TIMEOUT, follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Hermes-Agent/1.0)"}
        ) as client:
            response = client.get(feed_url)
            response.raise_for_status()
            # Use raw bytes to avoid encoding issues, limit to 2MB
            content_bytes = response.content[:MAX_FEED_BYTES]
        feed = feedparser.parse(content_bytes)
        if not feed.entries:
            log.warning(f"Feed returned 0 entries — {supplier_name} ({feed_url}), bozo={feed.get('bozo')}")
            return []
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
        log.info(f"Feed OK — {supplier_name}: {len(results)} entries")
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
        sources = [s for s in ALL_SUPPLIERS if s.get("rss")] + INDUSTRY_FEEDS

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
        junk_count = 0
        for item in items:
            if ticker:
                item.setdefault("ticker", ticker)
            if _is_junk(item.get("title", ""), item.get("summary", "")):
                # Mark seen so we don't re-evaluate it next crawl cycle
                redis_store.mark_seen(item["id"])
                junk_count += 1
                continue
            if not redis_store.is_seen(item["id"]):
                redis_store.mark_seen(item["id"])
                new_items.append(item)
        if junk_count:
            log.info(f"Pre-filter dropped {junk_count} junk item(s) from {name}")

    log.info(f"RSS crawl done — {len(new_items)} new items, {failed}/{len(sources)} feeds failed")
    return new_items
