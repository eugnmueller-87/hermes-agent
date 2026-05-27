"""
notifications/supabase_sink.py

Writes enriched Hermes signals directly to the Supabase `signals` table
so Icarus can read them without polling the Hermes REST API.

Uses httpx (already in requirements) — no new dependency needed.
Calls the upsert_hermes_signal() Postgres function so duplicates
(same hermes_id) are silently skipped.

Env vars (already set in Railway):
  SUPABASE_URL              — https://YOUR_PROJECT.supabase.co
  SUPABASE_SERVICE_ROLE_KEY — service role key
"""

import logging
import os
import threading
from datetime import datetime, timezone

import httpx

log = logging.getLogger("hermes.supabase_sink")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Hermes signal_type → Supabase signal_category enum
_CATEGORY_MAP = {
    "SUPPLY_CHAIN":    "supplier_disruption",
    "REGULATORY":      "regulatory_action",
    "EARNINGS":        "earnings_surprise",
    "PRICING_CHANGE":  "supplier_disruption",
    "LAYOFFS_HIRING":  "macro_shift",
    "ACQUISITION":     "positive_news",
    "FUNDING":         "positive_news",
    "PRODUCT_RELEASE": "positive_news",
    "PARTNERSHIP":     "positive_news",
    "RESEARCH_PAPER":  "neutral",
    "OTHER":           "neutral",
}

# Only push actionable categories — skip neutral
_SKIP_CATEGORIES = {"neutral"}

# Urgency → severity_level enum
_SEVERITY_MAP = {
    "HIGH":   "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW":    "LOW",
}


def _push_to_supabase(items: list[dict]) -> None:
    """Sync worker — called in a daemon thread."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning("[SupabaseSink] SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set — skipping.")
        return

    headers = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }

    pushed = 0
    skipped = 0

    with httpx.Client(timeout=10) as client:
        for item in items:
            signal_type = item.get("signal_type", "OTHER")
            category    = _CATEGORY_MAP.get(signal_type, "neutral")
            if category in _SKIP_CATEGORIES:
                skipped += 1
                continue

            # Build published_at — items have 'published' as ISO string or epoch
            published_raw = item.get("published") or item.get("published_at", "")
            try:
                if isinstance(published_raw, (int, float)):
                    published_at = datetime.fromtimestamp(published_raw, tz=timezone.utc).isoformat()
                else:
                    published_at = datetime.fromisoformat(
                        str(published_raw).replace("Z", "+00:00")
                    ).isoformat()
            except Exception:
                published_at = datetime.now(timezone.utc).isoformat()

            urgency  = item.get("urgency", "LOW")
            severity = _SEVERITY_MAP.get(urgency, "LOW")

            # hermes_id — prefer the item's own id field, fall back to url hash
            hermes_id = (
                item.get("id")
                or item.get("hermes_id")
                or item.get("url", "")
            )

            payload = {
                "p_hermes_id":          str(hermes_id),
                "p_source_url":         item.get("url", item.get("source", "")),
                "p_headline":           item.get("title", ""),
                "p_summary":            item.get("summary", ""),
                "p_published_at":       published_at,
                "p_category":           category,
                "p_severity":           severity,
                "p_affected_tickers":   item.get("affected_tickers", []),
                "p_raw_text":           f"{item.get('title', '')} {item.get('summary', '')}",
                "p_supplier":           item.get("supplier", ""),
                "p_hermes_signal_type": signal_type,
                "p_urgency":            urgency,
                "p_is_significant":     bool(item.get("is_significant", False)),
            }

            try:
                resp = client.post(
                    f"{SUPABASE_URL}/rest/v1/rpc/upsert_hermes_signal",
                    headers=headers,
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    pushed += 1
                else:
                    log.warning(
                        "[SupabaseSink] upsert failed for '%s': %s %s",
                        item.get("title", "?")[:60], resp.status_code, resp.text[:200],
                    )
            except Exception as exc:
                log.warning("[SupabaseSink] httpx error for '%s': %s", item.get("title", "?")[:60], exc)

    log.info("[SupabaseSink] %d signal(s) pushed, %d neutral skipped.", pushed, skipped)


def sink_to_supabase(enriched: list[dict]) -> None:
    """
    Call this after detect_signals() + store_items().
    Runs async in a daemon thread — never blocks the crawl cycle.
    """
    if not enriched:
        return
    threading.Thread(target=_push_to_supabase, args=(enriched,), daemon=True).start()
