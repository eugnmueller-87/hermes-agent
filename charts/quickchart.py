import logging
from collections import defaultdict

import httpx

from config.suppliers import SUPPLIERS
from storage.redis_store import RedisStore

log = logging.getLogger("hermes.charts")

_QUICKCHART_URL = "https://quickchart.io/chart/create"


def _post_chart(config: dict, width: int = 600, height: int = 400) -> str:
    try:
        resp = httpx.post(
            _QUICKCHART_URL,
            json={"chart": config, "width": width, "height": height, "backgroundColor": "white"},
            timeout=10,
        )
        resp.raise_for_status()
        url = resp.json()["url"]
        return url
    except httpx.TimeoutException:
        log.error("QuickChart request timed out after 10s")
        raise
    except httpx.HTTPStatusError as e:
        log.error(f"QuickChart HTTP error {e.response.status_code}: {e.response.text[:200]}")
        raise
    except Exception as e:
        log.error(f"QuickChart unexpected error: {e}")
        raise


def build_signals_chart(store: RedisStore) -> str:
    """Bar chart of significant signals grouped by urgency (HIGH / MEDIUM / LOW)."""
    log.info("Building signals chart")
    try:
        items = store.get_significant_items(limit=500)
        log.info(f"Signals chart: {len(items)} significant items fetched")

        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in items:
            urgency = item.get("urgency", "LOW")
            if urgency in counts:
                counts[urgency] += 1
        log.info(f"Signals chart: urgency breakdown — {counts}")

        config = {
            "type": "bar",
            "data": {
                "labels": ["HIGH", "MEDIUM", "LOW"],
                "datasets": [
                    {
                        "label": "Significant Signals",
                        "data": [counts["HIGH"], counts["MEDIUM"], counts["LOW"]],
                        "backgroundColor": ["#e53e3e", "#f6ad55", "#68d391"],
                    }
                ],
            },
            "options": {
                "title": {"display": True, "text": "Hermes — Signals by Urgency"},
                "legend": {"display": False},
                "scales": {"yAxes": [{"ticks": {"beginAtZero": True, "precision": 0}}]},
            },
        }
        url = _post_chart(config)
        log.info(f"Signals chart ready: {url}")
        return url
    except Exception as e:
        log.error(f"build_signals_chart failed: {e}")
        raise


def build_landscape_chart(store: RedisStore) -> str:
    """Horizontal bar chart of item counts per category (top 10)."""
    log.info("Building landscape chart")
    try:
        sup_to_cat = {}
        for cat, sups in SUPPLIERS.items():
            label = cat.replace("_", " ").title()
            for s in sups:
                sup_to_cat[s["name"].lower()] = label

        all_items = store.get_all_items(limit=500)
        log.info(f"Landscape chart: {len(all_items)} items fetched")

        category_counts: dict[str, int] = defaultdict(int)
        for item in all_items:
            cat = sup_to_cat.get(item.get("supplier", "").lower(), "Other")
            category_counts[cat] += 1

        sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        log.info(f"Landscape chart: {len(sorted_cats)} categories — top: {sorted_cats[:3]}")
        if not sorted_cats:
            sorted_cats = [("No data yet", 0)]

        labels = [c[0] for c in sorted_cats]
        data = [c[1] for c in sorted_cats]

        config = {
            "type": "horizontalBar",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Items",
                        "data": data,
                        "backgroundColor": "rgba(66, 153, 225, 0.8)",
                    }
                ],
            },
            "options": {
                "title": {"display": True, "text": "Hermes — Items by Category (Top 10)"},
                "legend": {"display": False},
                "scales": {"xAxes": [{"ticks": {"beginAtZero": True, "precision": 0}}]},
            },
        }
        url = _post_chart(config, height=500)
        log.info(f"Landscape chart ready: {url}")
        return url
    except Exception as e:
        log.error(f"build_landscape_chart failed: {e}")
        raise
