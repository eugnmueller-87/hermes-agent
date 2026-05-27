import json
import logging
import os
import time as _time
from email.utils import parsedate_to_datetime

from upstash_redis import Redis

log = logging.getLogger("hermes.store")


def _parse_ts(published: str) -> float:
    """Parse a date string to a Unix timestamp.
    Handles both ISO 8601 ('2026-05-27T...') and RFC 2822 ('Wed, 27 May 2026 07:00:00 GMT').
    Falls back to current time on any parse error.
    """
    if not published:
        return _time.time()
    try:
        # ISO 8601
        from datetime import datetime
        return datetime.fromisoformat(published.replace("Z", "+00:00")).timestamp()
    except ValueError:
        pass
    try:
        # RFC 2822 (used by RSS feeds)
        return parsedate_to_datetime(published).timestamp()
    except Exception:
        pass
    return _time.time()

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
        # Maintain O(1) count and sorted index of significant items
        self.r.incr("hermes:meta:item_count")
        if item.get("is_significant"):
            published = item.get("published", "")
            score = _time.time() if not published else _parse_ts(published)
            self.r.zadd("hermes:index:significant", {item["id"]: score})
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
        try:
            self._update_profile(item)
        except Exception as e:
            log.warning(f"Profile update failed for {item.get('supplier', '?')}: {e}")

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

    def _scan_keys(self, pattern: str, max_keys: int = 5000) -> list[str]:
        keys = []
        cursor = 0
        while True:
            result = self.r.scan(cursor, match=pattern, count=200)
            cursor = result[0]
            keys.extend(result[1])
            if cursor == 0 or len(keys) >= max_keys:
                break
        return keys[:max_keys]

    def count_items(self) -> int:
        count = self.r.get("hermes:meta:item_count")
        return int(count) if count else 0

    def get_items_by_slug(self, slug: str, limit: int = 10) -> list[dict]:
        ids = self.r.lrange(f"hermes:supplier:{slug}", 0, limit - 1)
        items = []
        for item_id in ids:
            raw = self.r.get(f"hermes:item:{item_id}")
            if raw:
                items.append(json.loads(raw))
        return items

    def list_supplier_slugs(self) -> list[str]:
        keys = self._scan_keys("hermes:supplier:*")
        return [k.replace("hermes:supplier:", "") for k in keys]

    def get_significant_items(self, limit: int = 20) -> list[dict]:
        # Use the sorted index for O(log n) lookup instead of full scan
        ids = self.r.zrevrange("hermes:index:significant", 0, limit - 1)
        items = []
        for item_id in ids:
            raw = self.r.get(f"hermes:item:{item_id}")
            if raw:
                items.append(json.loads(raw))
        return items

    def get_all_items(self, limit: int = 500) -> list[dict]:
        keys = self._scan_keys("hermes:item:*", max_keys=limit)
        items = []
        for key in keys:
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

    # ── Profile layer ──────────────────────────────────────────────────────────

    @staticmethod
    def _supplier_meta(supplier_name: str) -> tuple[str, int]:
        """Return (category, tier) for a supplier name, or ('', 0) if unknown."""
        try:
            from config.suppliers import SUPPLIERS

            for category, companies in SUPPLIERS.items():
                for s in companies:
                    if s["name"].lower() == supplier_name.lower():
                        return category, s.get("tier", 0)
        except Exception:
            pass
        return "", 0

    def _update_profile(self, item: dict):
        supplier = item.get("supplier", "")
        if not supplier:
            return
        slug = supplier.lower().replace(" ", "_").replace("-", "_").replace(".", "_")
        key = f"hermes:profile:{slug}"
        raw = self.r.get(key)
        if raw:
            profile = json.loads(raw)
        else:
            category, tier = self._supplier_meta(supplier)
            profile = {
                "slug": slug,
                "name": supplier,
                "category": category,
                "tier": tier,
                "first_seen": item.get("published", ""),
                "last_updated": "",
                "total_signals": 0,
                "significant_signals": 0,
                "recent_signals": [],
                "signal_type_counts": {},
                "urgency_counts": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "risk_flags": [],
            }
        profile["last_updated"] = item.get("published", "")
        profile["total_signals"] = profile.get("total_signals", 0) + 1
        if item.get("is_significant"):
            profile["significant_signals"] = profile.get("significant_signals", 0) + 1
        signal_summary = {
            "id": item["id"],
            "title": item.get("title", "")[:100],
            "published": item.get("published", ""),
            "urgency": item.get("urgency", ""),
            "signal_type": item.get("signal_type", ""),
            "is_significant": item.get("is_significant", False),
        }
        recent = profile.get("recent_signals", [])
        recent.insert(0, signal_summary)
        profile["recent_signals"] = recent[:10]
        sig_type = item.get("signal_type", "UNKNOWN")
        counts = profile.get("signal_type_counts", {})
        counts[sig_type] = counts.get(sig_type, 0) + 1
        profile["signal_type_counts"] = counts
        urgency = item.get("urgency", "LOW")
        urg = profile.get("urgency_counts", {"HIGH": 0, "MEDIUM": 0, "LOW": 0})
        urg[urgency] = urg.get(urgency, 0) + 1
        profile["urgency_counts"] = urg
        if item.get("urgency") == "HIGH" and item.get("is_significant"):
            flags = profile.get("risk_flags", [])
            flags.insert(
                0,
                {
                    "title": item.get("title", "")[:100],
                    "published": item.get("published", ""),
                    "reason": item.get("significance_reason", "")[:150],
                },
            )
            profile["risk_flags"] = flags[:5]
        self.r.set(key, json.dumps(profile))  # no TTL — profiles are permanent

        # Auto-enrich once profile reaches the significance threshold
        try:
            from intelligence.enrichment import enrich_profile, should_auto_enrich

            if should_auto_enrich(profile):
                log.info(f"Auto-enriching profile for {supplier}")
                enrich_profile(self, slug)
        except Exception as e:
            log.warning(f"Auto-enrichment failed for {supplier}: {e}")

    def get_profile(self, slug: str) -> dict | None:
        raw = self.r.get(f"hermes:profile:{slug}")
        return json.loads(raw) if raw else None

    def list_profile_slugs(self) -> list[str]:
        keys = self.r.keys("hermes:profile:*")
        return [k.replace("hermes:profile:", "") for k in keys]

    # ── Watchlist ──────────────────────────────────────────────────────────────

    _WATCHLIST_KEY = "hermes:watchlist"

    def watchlist_add(self, slug: str):
        self.r.sadd(self._WATCHLIST_KEY, slug)

    def watchlist_remove(self, slug: str):
        self.r.srem(self._WATCHLIST_KEY, slug)

    def watchlist_get(self) -> list[str]:
        members = self.r.smembers(self._WATCHLIST_KEY)
        return list(members) if members else []

    # ── Flush ──────────────────────────────────────────────────────────────────

    def flush(self):
        """Delete all hermes item/supplier/seen/profile keys and reset the vector index."""
        deleted = 0
        for prefix in ("hermes:item:*", "hermes:supplier:*", "hermes:seen:*", "hermes:profile:*", "hermes:index:*", "hermes:meta:*"):
            try:
                keys = self._scan_keys(prefix, max_keys=10000)
                if keys:
                    # delete in batches of 100 to avoid Upstash limits
                    for i in range(0, len(keys), 100):
                        batch = keys[i:i+100]
                        self.r.delete(*batch)
                        deleted += len(batch)
            except Exception as e:
                log.warning(f"Flush partial failure for {prefix}: {e}")
        log.info(f"Flush complete — {deleted} keys deleted")
        if self.index:
            try:
                self.index.reset()
            except Exception as e:
                log.warning(f"Vector reset failed: {e}")
