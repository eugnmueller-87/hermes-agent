"""
Trend memory — weekly cluster delta.

Compares this week's macro theme clusters to last week's and labels each
cluster as NEW, CONTINUING, or RESOLVED (last week but gone this week).

Weekly cluster snapshots are stored at hermes:clusters:weekly:{iso_week}
with a 30-day TTL so we can look back one week reliably.

GET /trends/delta returns the structured comparison.
Isolated: reads cluster cache from Redis, does string comparison, no LLM call.
"""

import json
import logging
from datetime import UTC, datetime, timedelta

log = logging.getLogger("hermes.trends")


def _iso_week(offset_weeks: int = 0) -> str:
    dt = datetime.now(UTC) - timedelta(weeks=offset_weeks)
    return dt.strftime("%Y-W%W")


def save_weekly_snapshot(r, clusters: list[dict]):
    """Persist a weekly cluster snapshot with 30-day TTL."""
    week = _iso_week()
    key = f"hermes:clusters:weekly:{week}"
    r.set(key, json.dumps(clusters), ex=60 * 60 * 24 * 30)
    log.info(f"Weekly cluster snapshot saved: {key}")


def _load_week(r, offset: int) -> list[dict]:
    week = _iso_week(offset)
    raw = r.get(f"hermes:clusters:weekly:{week}")
    return json.loads(raw) if raw else []


def _label_similarity(a: str, b: str) -> bool:
    """Simple word-overlap check — True if labels share 2+ significant words."""
    stopwords = {"and", "the", "of", "in", "for", "a", "an", "to", "with", "by"}
    words_a = {w.lower() for w in a.split() if w.lower() not in stopwords}
    words_b = {w.lower() for w in b.split() if w.lower() not in stopwords}
    return len(words_a & words_b) >= 2


def build_delta(r) -> dict:
    """
    Compare this week's clusters to last week's.
    Returns a dict with new, continuing, and resolved cluster lists.
    """
    this_week = _load_week(r, 0)
    last_week = _load_week(r, 1)

    continuing = []
    new_clusters = []
    resolved = []

    for cluster in this_week:
        matched = any(_label_similarity(cluster["label"], prev["label"]) for prev in last_week)
        if matched:
            continuing.append(cluster)
        else:
            new_clusters.append(cluster)

    for prev in last_week:
        still_present = any(_label_similarity(prev["label"], cur["label"]) for cur in this_week)
        if not still_present:
            resolved.append(prev)

    return {
        "week": _iso_week(),
        "this_week_clusters": len(this_week),
        "last_week_clusters": len(last_week),
        "new": new_clusters,
        "continuing": continuing,
        "resolved": resolved,
        "has_history": bool(last_week),
    }
