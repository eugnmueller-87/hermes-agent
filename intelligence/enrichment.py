"""
Profile enrichment.

Reads a company's accumulated signals and asks Claude Haiku to extract
structured intelligence: key products, pricing notes, and a risk summary.
Writes the result back to the profile in Redis.

Triggered manually via POST /enrich/{company} or automatically when a
profile crosses 10 significant signals for the first time.

Isolated: reads profile + items, calls Haiku, writes enrichment fields.
Never touches crawlers, the vector index, or other profiles.
"""

import json
import logging
import os

import anthropic

log = logging.getLogger("hermes.enrichment")

_MODEL = "claude-haiku-4-5-20251001"
_MIN_SIGNALS_FOR_AUTO = 10  # auto-enrich threshold


def _build_prompt(profile: dict, signals: list[dict]) -> str:
    name = profile.get("name", "this company")
    lines = []
    for s in signals[:20]:
        lines.append(
            f"- [{s.get('urgency', 'LOW')}] [{s.get('signal_type', '?')}] "
            f"{s.get('title', '')[:100]} — {s.get('significance_reason', '')[:120]}"
        )
    signal_block = "\n".join(lines)
    return (
        f"You are a procurement intelligence analyst. Based on the signals below for {name}, "
        "extract three pieces of structured intelligence.\n\n"
        "Return ONLY a JSON object with exactly these fields:\n"
        '{"key_products": ["product or service 1", "product or service 2", ...],\n'
        ' "pricing_notes": "one sentence on pricing trends, contract risk, or cost signals. '
        'Empty string if no pricing signals.",\n'
        ' "risk_summary": "one sentence summarising the biggest risk or watch-point for this vendor. '
        'Empty string if no risk signals."}\n\n'
        "Rules:\n"
        "- key_products: max 5 items, be specific (model names, product lines)\n"
        "- pricing_notes: only if pricing/cost signals exist, otherwise empty string\n"
        "- risk_summary: focus on supply chain, regulatory, or financial risk\n\n"
        f"Signals for {name}:\n{signal_block}"
    )


def _parse_response(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def enrich_profile(store, slug: str) -> dict | None:
    """
    Enrich a company profile with structured intelligence extracted by Haiku.
    Returns the updated profile, or None if the profile doesn't exist.
    Raises on API failure.
    """
    profile = store.get_profile(slug)
    if not profile:
        log.warning(f"Enrichment: profile not found for slug '{slug}'")
        return None

    # Fetch the actual signal items for this supplier
    signals = store.get_items_by_slug(slug, limit=20)
    significant = [s for s in signals if s.get("is_significant")]
    if not significant:
        significant = signals  # fall back to all signals if none are flagged significant

    if not significant:
        log.info(f"Enrichment: no signals available for {slug}")
        return profile

    log.info(f"Enrichment: enriching {profile['name']} from {len(significant)} signals")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(profile, significant)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    enrichment = _parse_response(message.content[0].text.strip())

    profile["key_products"] = enrichment.get("key_products", [])
    profile["pricing_notes"] = enrichment.get("pricing_notes", "")
    profile["risk_summary"] = enrichment.get("risk_summary", "")
    profile["enriched_at"] = (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    )

    store.r.set(f"hermes:profile:{slug}", json.dumps(profile))
    log.info(f"Enrichment: {profile['name']} profile updated")
    return profile


def should_auto_enrich(profile: dict) -> bool:
    """True if this profile has enough signals and hasn't been enriched yet."""
    return profile.get("significant_signals", 0) >= _MIN_SIGNALS_FOR_AUTO and not profile.get(
        "enriched_at"
    )
