"""
Hermes Client — standalone integration module for SpendLens.

Drop this file into SpendLens. Only dependency: upstash-redis + python-dotenv.
Set UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN in SpendLens .env —
same credentials as Hermes (shared Redis instance).

Usage:
    from integrations.hermes_client import HermesClient
    hermes = HermesClient()

    # Get procurement signals for a vendor
    signals = hermes.get_signals("TSMC")

    # Get risk flags (significant + HIGH/MEDIUM urgency only)
    flags = hermes.get_risk_flags("NVIDIA")

    # Enrich a full vendor list from SpendLens spend data
    risk_map = hermes.enrich_vendor_list(["TSMC", "Intel", "Arrow Electronics"])

    # Get all significant procurement signals across all tracked suppliers
    briefing = hermes.get_procurement_briefing()
"""

import os
import json
from difflib import get_close_matches
from upstash_redis import Redis

PROCUREMENT_SIGNALS = {
    "SUPPLY_CHAIN",
    "PRICING_CHANGE",
    "EARNINGS",
    "REGULATORY",
    "ACQUISITION",
    "LAYOFFS_HIRING",
}

SIGNAL_EMOJI = {
    "SUPPLY_CHAIN":   "⚠️",
    "PRICING_CHANGE": "💲",
    "EARNINGS":       "📊",
    "REGULATORY":     "⚖️",
    "ACQUISITION":    "🤝",
    "LAYOFFS_HIRING": "👥",
}


class HermesClient:
    """
    Read-only client for querying Hermes market intelligence from SpendLens.
    Connects to the shared Upstash Redis instance using hermes:* keys.
    """

    def __init__(self):
        self.r = Redis(
            url=os.environ["UPSTASH_REDIS_REST_URL"],
            token=os.environ["UPSTASH_REDIS_REST_TOKEN"],
        )
        self._slug_cache = None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _slug(self, name: str) -> str:
        return name.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")

    def _known_slugs(self) -> list[str]:
        if self._slug_cache is None:
            keys = self.r.keys("hermes:supplier:*")
            self._slug_cache = [k.replace("hermes:supplier:", "") for k in keys]
        return self._slug_cache

    def _resolve(self, vendor_name: str) -> str | None:
        """Resolve a vendor name to a Hermes slug. Falls back to fuzzy match."""
        direct = self._slug(vendor_name)
        if self.r.exists(f"hermes:supplier:{direct}"):
            return direct
        known = self._known_slugs()
        matches = get_close_matches(direct, known, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def _fetch_items(self, slug: str, limit: int) -> list[dict]:
        ids = self.r.lrange(f"hermes:supplier:{slug}", 0, limit - 1)
        items = []
        for item_id in ids:
            raw = self.r.get(f"hermes:item:{item_id}")
            if raw:
                items.append(json.loads(raw))
        return items

    # ── Public API ────────────────────────────────────────────────────────────

    def get_signals(self, vendor_name: str, limit: int = 10, procurement_only: bool = True) -> list[dict]:
        """
        Get recent Hermes signals for a vendor.
        procurement_only=True filters to supply chain, pricing, earnings, regulatory, M&A, hiring.
        Returns empty list if vendor is not tracked by Hermes.
        """
        slug = self._resolve(vendor_name)
        if not slug:
            return []
        items = self._fetch_items(slug, limit)
        if procurement_only:
            items = [i for i in items if i.get("signal_type") in PROCUREMENT_SIGNALS]
        return items

    def get_risk_flags(self, vendor_name: str) -> list[dict]:
        """
        Get significant HIGH/MEDIUM urgency signals for a vendor.
        Use this to populate the SpendLens flag engine with external risk data.
        """
        items = self.get_signals(vendor_name, limit=20, procurement_only=True)
        return [
            i for i in items
            if i.get("is_significant") and i.get("urgency") in ("HIGH", "MEDIUM")
        ]

    def enrich_vendor_list(self, vendor_names: list[str]) -> dict[str, dict]:
        """
        Bulk-enrich a list of vendor names from SpendLens spend data.
        Returns a dict keyed by vendor name with risk summary per vendor.

        Example output:
        {
            "TSMC": {
                "tracked": True,
                "hermes_slug": "tsmc",
                "risk_level": "HIGH",
                "signal_count": 3,
                "top_signal": { ...item dict... },
                "signals": [ ...list of items... ]
            },
            "Some Unknown Vendor": {
                "tracked": False,
                ...
            }
        }
        """
        result = {}
        for name in vendor_names:
            slug = self._resolve(name)
            if not slug:
                result[name] = {"tracked": False, "risk_level": "UNKNOWN", "signal_count": 0, "signals": []}
                continue
            signals = self.get_risk_flags(name)
            if any(s.get("urgency") == "HIGH" for s in signals):
                risk = "HIGH"
            elif signals:
                risk = "MEDIUM"
            else:
                risk = "LOW"
            result[name] = {
                "tracked": True,
                "hermes_slug": slug,
                "risk_level": risk,
                "signal_count": len(signals),
                "top_signal": signals[0] if signals else None,
                "signals": signals,
            }
        return result

    def get_procurement_briefing(self, limit: int = 20) -> list[dict]:
        """
        Get the most recent significant procurement signals across all tracked suppliers.
        Use this for a SpendLens market intelligence briefing or dashboard widget.
        """
        keys = self.r.keys("hermes:item:*")
        items = []
        for key in keys[:300]:
            raw = self.r.get(key)
            if raw:
                item = json.loads(raw)
                if item.get("is_significant") and item.get("signal_type") in PROCUREMENT_SIGNALS:
                    items.append(item)
        items.sort(key=lambda x: x.get("published", ""), reverse=True)
        return items[:limit]

    def format_signal_for_display(self, item: dict) -> str:
        """Format a single Hermes signal as a clean one-liner for SpendLens UI."""
        emoji = SIGNAL_EMOJI.get(item.get("signal_type", ""), "📰")
        urgency = item.get("urgency", "LOW")
        supplier = item.get("supplier", "")
        title = item.get("title", "")[:80]
        date = item.get("published", "")[:10]
        reason = item.get("significance_reason", "")
        line = f"{emoji} [{urgency}] {supplier} — {title} ({date})"
        if reason:
            line += f"\n   → {reason}"
        return line
