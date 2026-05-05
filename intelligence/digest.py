"""
Weekly Hermes digest.

Every Sunday at 18:00 Berlin, scans the week's significant signals,
groups them by category, and asks Claude Sonnet to write a one-paragraph
summary per category plus an overall verdict.

Stored at hermes:digest:weekly:{iso_week} — 30-day TTL.
Exposed via GET /digest for Icarus to fetch and forward to Telegram.
"""

import json
import logging
import os
from datetime import UTC, datetime

import anthropic

log = logging.getLogger("hermes.digest")

_MODEL = "claude-sonnet-4-5"
_MAX_SIGNALS = 150


def _iso_week() -> str:
    return datetime.now(UTC).strftime("%Y-W%W")


def _build_prompt(signals_by_category: dict[str, list[dict]]) -> str:
    lines = []
    for category, sigs in signals_by_category.items():
        lines.append(f"\n### {category} ({len(sigs)} signals)")
        for s in sigs[:10]:
            lines.append(
                f"  - [{s.get('urgency', 'LOW')}] {s.get('supplier', '?')}: "
                f"{s.get('title', '')[:90]} — {s.get('significance_reason', '')[:100]}"
            )
    signal_block = "\n".join(lines)

    return (
        "You are a market intelligence analyst writing a weekly digest for a procurement professional.\n\n"
        "Below are this week's significant signals grouped by category.\n\n"
        "For each category with signals, write:\n"
        "1. A 2–3 sentence summary of what moved this week in that category\n"
        "2. The single most important signal and why it matters\n\n"
        "Then write a 2-sentence overall verdict: what is the most important thing "
        "a procurement professional should know from this week's intelligence.\n\n"
        "Return ONLY a JSON object:\n"
        '{"week": "...", "overall": "...", "categories": ['
        '{"name": "...", "signal_count": 0, "summary": "...", "top_signal": "..."}]}\n\n'
        f"Signals:\n{signal_block}"
    )


def _parse_response(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def build_weekly_digest(store) -> dict:
    """
    Generate a weekly digest from this week's significant signals.
    Returns the digest dict. Raises on API or data failure.
    """
    signals = store.get_significant_items(limit=_MAX_SIGNALS)
    if not signals:
        log.info("Weekly digest: no significant signals this week")
        return {
            "week": _iso_week(),
            "overall": "No significant signals this week.",
            "categories": [],
            "generated_at": datetime.now(UTC).isoformat(),
        }

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for s in signals:
        cat = s.get("category", "Uncategorised")
        by_category.setdefault(cat, []).append(s)

    # Sort each category by published date descending
    for cat in by_category:
        by_category[cat].sort(key=lambda x: x.get("published", ""), reverse=True)

    log.info(f"Weekly digest: {len(signals)} signals across {len(by_category)} categories")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(by_category)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    digest = _parse_response(message.content[0].text.strip())
    digest["week"] = _iso_week()
    digest["generated_at"] = datetime.now(UTC).isoformat()
    digest["total_signals"] = len(signals)
    log.info(f"Weekly digest generated — {len(digest.get('categories', []))} categories")
    return digest


def store_digest(r, digest: dict):
    """Persist the digest in Redis with a 30-day TTL."""
    week = digest.get("week", _iso_week())
    key = f"hermes:digest:weekly:{week}"
    r.set(key, json.dumps(digest), ex=60 * 60 * 24 * 30)
    log.info(f"Digest stored at {key}")


def get_latest_digest(r) -> dict | None:
    """Return the most recent stored digest, or None."""
    week = _iso_week()
    raw = r.get(f"hermes:digest:weekly:{week}")
    if raw:
        return json.loads(raw)
    # Fall back to previous week
    from datetime import timedelta

    prev_week = (datetime.now(UTC) - timedelta(weeks=1)).strftime("%Y-W%W")
    raw = r.get(f"hermes:digest:weekly:{prev_week}")
    return json.loads(raw) if raw else None
