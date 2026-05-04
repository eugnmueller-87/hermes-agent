import os
import hashlib
from datetime import datetime, timezone
from tavily import TavilyClient
from config.suppliers import TIER_1, TIER_2, TIER_3


def _hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def crawl_tavily(redis_store, tier: int = 1) -> list[dict]:
    client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    tier_map = {1: TIER_1, 2: TIER_1 + TIER_2, 3: TIER_1 + TIER_2 + TIER_3}
    suppliers = tier_map.get(tier, TIER_1)

    new_items = []

    for supplier in suppliers:
        query = f"{supplier['name']} news announcement 2026"
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=5,
                include_answer=False,
            )
            for result in response.get("results", []):
                item_id = _hash(result.get("url", ""))
                if redis_store.is_seen(item_id):
                    continue
                redis_store.mark_seen(item_id)
                new_items.append({
                    "id": item_id,
                    "supplier": supplier["name"],
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "summary": result.get("content", "")[:500],
                    "published": datetime.now(timezone.utc).isoformat(),
                    "source": "tavily",
                })
        except Exception as e:
            print(f"[Tavily] Failed {supplier['name']}: {e}")

    print(f"[Tavily] Found {len(new_items)} new items (tier {tier})")
    return new_items
