"""
Cross-signal cluster detection.

Scans recent significant signals, sends them to Claude Sonnet, and returns
a list of macro theme clusters — each with a label, synthesis paragraph,
companies involved, and urgency distribution.

Completely isolated: reads from Redis, calls Anthropic API, returns JSON.
Never touches crawlers, storage writes, or other endpoints.
"""

import json
import logging
import os

import anthropic

log = logging.getLogger("hermes.clusters")

_MODEL = "claude-sonnet-4-6"
_MAX_SIGNALS = 80  # cap to stay within a single prompt


def _build_prompt(signals: list[dict]) -> str:
    lines = []
    for s in signals:
        lines.append(
            f"- [{s.get('urgency', 'LOW')}] {s.get('supplier', '?')} | "
            f"{s.get('signal_type', '?')} | {s.get('title', '')[:100]} | "
            f"{s.get('significance_reason', '')[:120]}"
        )
    signal_block = "\n".join(lines)
    return (
        "You are a market intelligence analyst. Below are recent significant signals "
        "from a set of tech suppliers and companies. Group them into macro themes — "
        "patterns or trends that appear across multiple companies.\n\n"
        "For each cluster:\n"
        "1. Give it a short label (3-6 words)\n"
        "2. Write one paragraph (2-4 sentences) synthesising what the signals collectively suggest\n"
        "3. List the companies involved\n"
        "4. Note the urgency distribution (HIGH/MEDIUM/LOW counts)\n\n"
        "Return ONLY a JSON array. Each element:\n"
        '{"label": "...", "synthesis": "...", "companies": ["..."], '
        '"urgency": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}, "signal_count": 0}\n\n'
        "Signals:\n"
        f"{signal_block}\n\n"
        "If fewer than 3 signals share a theme, skip that cluster. "
        "Return an empty array [] if no meaningful clusters exist."
    )


def build_clusters(store) -> list[dict]:
    """
    Fetch recent significant signals, cluster them with Claude Sonnet,
    and return a list of cluster dicts. Raises on API failure.
    """
    signals = store.get_significant_items(limit=_MAX_SIGNALS)
    if not signals:
        log.info("Cluster detection: no significant signals available")
        return []

    log.info(f"Cluster detection: analysing {len(signals)} significant signals")
    prompt = _build_prompt(signals)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    clusters = json.loads(raw)
    log.info(f"Cluster detection: {len(clusters)} clusters identified")
    return clusters
