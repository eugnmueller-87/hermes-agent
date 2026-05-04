import os
import json
from datetime import timedelta
from upstash_redis import Redis


class RedisStore:
    def __init__(self):
        self.r = Redis(
            url=os.environ["UPSTASH_REDIS_REST_URL"],
            token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
        )
        self.seen_ttl = 60 * 60 * 24 * 30   # 30 days
        self.item_ttl = 60 * 60 * 24 * 7    # 7 days

    def is_seen(self, item_id: str) -> bool:
        return self.r.exists(f"hermes:seen:{item_id}") == 1

    def mark_seen(self, item_id: str):
        self.r.set(f"hermes:seen:{item_id}", "1", ex=self.seen_ttl)

    def store_item(self, item: dict):
        key = f"hermes:item:{item['id']}"
        self.r.set(key, json.dumps(item), ex=self.item_ttl)
        # Add to supplier-specific list
        list_key = f"hermes:supplier:{item['supplier'].lower().replace(' ', '_')}"
        self.r.lpush(list_key, item["id"])
        self.r.ltrim(list_key, 0, 49)  # keep last 50 per supplier
        self.r.expire(list_key, self.item_ttl)

    def store_items(self, items: list[dict]):
        for item in items:
            self.store_item(item)

    def get_supplier_items(self, supplier_name: str, limit: int = 10) -> list[dict]:
        list_key = f"hermes:supplier:{supplier_name.lower().replace(' ', '_')}"
        ids = self.r.lrange(list_key, 0, limit - 1)
        items = []
        for item_id in ids:
            raw = self.r.get(f"hermes:item:{item_id}")
            if raw:
                items.append(json.loads(raw))
        return items

    def get_significant_items(self, limit: int = 20) -> list[dict]:
        keys = self.r.keys("hermes:item:*")
        items = []
        for key in keys[:200]:
            raw = self.r.get(key)
            if raw:
                item = json.loads(raw)
                if item.get("is_significant"):
                    items.append(item)
        items.sort(key=lambda x: x.get("published", ""), reverse=True)
        return items[:limit]
