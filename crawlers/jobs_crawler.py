"""
Job postings crawler.

Uses Tavily to search for open roles at Tier 1+2 suppliers on Lever, Greenhouse,
and Workday. Hiring spikes are 6-month leading indicators — a company building
a 50-person AI chip team is a signal long before any press release.

Runs weekly (same budget envelope as Tavily news). Uses 2 Tavily searches per
company (Lever + Greenhouse), so Tier 1+2 (~177 companies) ≈ 354 searches/run.
Scheduled separately to avoid competing with the main Tavily window.
"""

import hashlib
import logging
import os
from datetime import UTC, datetime

from tavily import TavilyClient

from config.suppliers import TIER_1, TIER_2

log = logging.getLogger("hermes.jobs")

_JOB_BOARDS = ["site:lever.co", "site:greenhouse.io", "site:workday.com"]


def _hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def crawl_jobs(redis_store, tier: int = 2) -> list[dict]:
    """
    Search for job postings for Tier 1 (tier=1) or Tier 1+2 (tier=2) suppliers.
    Returns new items ready for signal detection.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        log.error("TAVILY_API_KEY not set — jobs crawl skipped")
        return []

    client = TavilyClient(api_key=api_key)
    suppliers = TIER_1 if tier == 1 else TIER_1 + TIER_2
    new_items = []
    boards_str = " OR ".join(_JOB_BOARDS)

    for supplier in suppliers:
        query = f"{supplier['name']} jobs hiring ({boards_str})"
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=False,
            )
            for result in response.get("results", []):
                url = result.get("url", "")
                item_id = _hash(url)
                if redis_store.is_seen(item_id):
                    continue
                redis_store.mark_seen(item_id)
                new_items.append(
                    {
                        "id": item_id,
                        "supplier": supplier["name"],
                        "title": result.get("title", ""),
                        "url": url,
                        "summary": result.get("content", "")[:500],
                        "published": datetime.now(UTC).isoformat(),
                        "source": "jobs",
                    }
                )
        except Exception as e:
            log.warning(f"Jobs search failed — {supplier['name']}: {e}")

    log.info(f"Jobs crawl done — {len(new_items)} new postings from {len(suppliers)} suppliers")
    return new_items
