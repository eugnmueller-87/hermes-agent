import json
import logging
import os

from upstash_redis import Redis

log = logging.getLogger("hermes.store")


class RedisStore:
    def __init__(self):
        self.r = Redis(
            url=os.environ["UPSTASH_REDIS_REST_URL"],
            token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
        )
        self.seen_ttl = 60 * 60 * 24 * 30  # 30 days
        self.item_ttl = 60 * 60 * 24 * 7  # 7 days
        self.index = None
        vector_url = os.environ.get("UPSTASH_VECTOR_REST_URL")
        vector_token = os.environ.get("UPSTASH_VECTOR_REST_TOKEN")
        if vector_url and vector_token:
            try:
                from upstash_vector import Index

                self.index = Index(url=vector_url, token=vector_token)
                log.info("Vector index connected")
            except Exception as e:
                log.warning(f"Vector index init failed: {e}")

    def is_seen(self, item_id: str) -> bool:
        return self.r.exists(f"hermes:seen:{item_id}") == 1

    def mark_seen(self, item_id: str):
        self.r.set(f"hermes:seen:{item_id}", "1", ex=self.seen_ttl)

    def store_item(self, item: dict):
        key = f"hermes:item:{item['id']}"
        self.r.set(key, json.dumps(item), ex=self.item_ttl)
        list_key = f"hermes:supplier:{item['supplier'].lower().replace(' ', '_')}"
        self.r.lpush(list_key, item["id"])
        self.r.ltrim(list_key, 0, 2999)
        self.r.expire(list_key, self.item_ttl)
        if self.index:
            try:
                text = (
                    f"{item['supplier']} ({item.get('category', '')}): "
                    f"{item['title']}. {item.get('significance_reason', '')}"
                )
                self.index.upsert(
                    [
                        {
                            "id": item["id"],
                            "data": text,
                            "metadata": {
                                "supplier": item["supplier"],
                                "category": item.get("category", ""),
                                "published": item.get("published", ""),
                                "is_significant": item.get("is_significant", False),
                                "urgency": item.get("urgency", ""),
                            },
                        }
                    ]
                )
            except Exception as e:
                log.warning(f"Vector upsert failed for {item['id']}: {e}")

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

    def count_items(self) -> int:
        return len(self.r.keys("hermes:item:*"))

    def get_items_by_slug(self, slug: str, limit: int = 10) -> list[dict]:
        ids = self.r.lrange(f"hermes:supplier:{slug}", 0, limit - 1)
        items = []
        for item_id in ids:
            raw = self.r.get(f"hermes:item:{item_id}")
            if raw:
                items.append(json.loads(raw))
        return items

    def list_supplier_slugs(self) -> list[str]:
        keys = self.r.keys("hermes:supplier:*")
        return [k.replace("hermes:supplier:", "") for k in keys]

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

    def get_all_items(self, limit: int = 500) -> list[dict]:
        keys = self.r.keys("hermes:item:*")
        items = []
        for key in keys[:limit]:
            raw = self.r.get(key)
            if raw:
                items.append(json.loads(raw))
        return items

    def semantic_search(self, query: str, limit: int = 10) -> list[dict]:
        if not self.index:
            return []
        try:
            results = self.index.query(data=query, top_k=limit, include_metadata=True)
            items = []
            for r in results:
                raw = self.r.get(f"hermes:item:{r.id}")
                if raw:
                    item = json.loads(raw)
                    item["_score"] = round(r.score, 3)
                    items.append(item)
            return items
        except Exception as e:
            log.warning(f"Vector search failed: {e}")
            return []

    def flush(self):
        """Delete all hermes item/supplier/seen keys from Redis and reset the vector index."""
        for prefix in ("hermes:item:*", "hermes:supplier:*", "hermes:seen:*"):
            keys = self.r.keys(prefix)
            for key in keys:
                self.r.delete(key)
        if self.index:
            try:
                self.index.reset()
            except Exception as e:
                log.warning(f"Vector reset failed: {e}")
