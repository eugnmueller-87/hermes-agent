import json
import logging
import os

import anthropic

log = logging.getLogger("hermes.signal")


def parse_llm_json(raw: str) -> dict:
    """Strip a ```json ... ``` (or bare ```) fence if present and parse as JSON.

    This is the single canonical parser for LLM responses across Hermes (previously the
    same fence-stripping was copy-pasted, untested, in 5 files). Pure + deterministic so
    it can be unit-tested without a network call. Raises ValueError on unparseable input.
    """
    if raw is None:
        raise ValueError("empty LLM response")
    s = raw.strip()
    if s.startswith("```"):
        # take the content between the first pair of fences
        parts = s.split("```")
        s = parts[1] if len(parts) >= 2 else s.strip("`")
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}") from e

SIGNAL_TYPES = {
    "FUNDING": "💰",
    "ACQUISITION": "🤝",
    "PRODUCT_RELEASE": "🆕",
    "PRICING_CHANGE": "💲",
    "SUPPLY_CHAIN": "⚠️",
    "EARNINGS": "📊",
    "PARTNERSHIP": "🔗",
    "REGULATORY": "⚖️",
    "LAYOFFS_HIRING": "👥",
    "RESEARCH_PAPER": "🔬",
    "OTHER": "📰",
}

PROMPT = """You are a supplier market-intelligence analyst for a PROCUREMENT team. Classify this news item about an (actual or potential) supplier and assess what it means for procurement risk and negotiation leverage — NOT for stock trading.

Source: {source}
Company/Feed: {supplier}
Title: {title}
Summary: {summary}
Pre-mapped supplier (if any): {ticker}

Respond with JSON only:
{{
  "signal_type": "<one of: FUNDING, ACQUISITION, PRODUCT_RELEASE, PRICING_CHANGE, SUPPLY_CHAIN, EARNINGS, PARTNERSHIP, REGULATORY, LAYOFFS_HIRING, RESEARCH_PAPER, OTHER>",
  "is_significant": <true or false>,
  "significance_reason": "<one sentence on what this means for procurement — supplier risk, pricing/leverage, continuity, or lock-in — or empty string if not significant>",
  "urgency": "<HIGH, MEDIUM, LOW>",
  "affected_suppliers": ["<list of supplier/vendor company names named in the item — empty list if none>"]
}}

Mark is_significant=true ONLY for hard, discrete events that change how a buyer should treat this supplier: large funding rounds ($100M+, shifts leverage), completed acquisitions (ownership/continuity change), confirmed pricing/licensing changes, confirmed supply-chain disruptions at a named supplier, regulatory/compliance actions against a named supplier, mass layoffs (>500, continuity risk), or major product launches that change the buy/build/switch calculus.

Mark is_significant=false for: opinion pieces, commentary, analysis without new facts, how-to guides, blog posts, tutorials, research papers without commercial impact, minor product updates, speculation, predictions, lifestyle articles, and anything without a specific named supplier company as the subject.

signal_type rules:
- SUPPLY_CHAIN: only for actual disruptions at a named supplier's supply chain (not general commodity commentary)
- PRICING_CHANGE: license/subscription/SaaS pricing moves, new tiers, or discount-policy changes at a named supplier
- REGULATORY: sanctions, fines, data-protection or compliance actions against a named supplier (procurement-relevant risk)
- EARNINGS: only actual reported financial results that signal supplier health/continuity, not estimates
- OTHER: opinion, commentary, analysis, lifestyle

IMPORTANT: affected_suppliers must contain real company/vendor names as named in the item (e.g. "Datadog", "Snowflake", "SAP"). This is procurement intelligence — do NOT emit stock tickers or assess stock-price impact.
"""


def detect_signals(items: list[dict]) -> list[dict]:
    if not items:
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set — all items will be unclassified")
        for item in items:
            item.setdefault("signal_type", "OTHER")
            item.setdefault("is_significant", False)
            item.setdefault("significance_reason", "")
            item.setdefault("urgency", "LOW")
            item.setdefault("emoji", "📰")
        return items

    client = anthropic.Anthropic(api_key=api_key)
    enriched = []

    for item in items:
        try:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                messages=[
                    {
                        "role": "user",
                        "content": PROMPT.format(
                            supplier=item["supplier"],
                            title=item["title"],
                            summary=item["summary"],
                            source=item["source"],
                            ticker=item.get("ticker") or "none",
                        ),
                    }
                ],
            )
            result = parse_llm_json(message.content[0].text)
            item["signal_type"] = result.get("signal_type", "OTHER")
            item["is_significant"] = result.get("is_significant", False)
            item["significance_reason"] = result.get("significance_reason", "")
            item["urgency"] = result.get("urgency", "LOW")
            item["emoji"] = SIGNAL_TYPES.get(item["signal_type"], "📰")
            # Procurement classifier emits `affected_suppliers`; fall back to the legacy
            # `affected_tickers` key for compatibility. We store the result under BOTH keys
            # so downstream sinks (supabase) and any existing data keep working during the
            # procurement realignment. `affected_suppliers` is the canonical field going forward.
            named = [s for s in (result.get("affected_suppliers") or result.get("affected_tickers") or []) if s]
            if named:
                item["affected_suppliers"] = named
                item["affected_tickers"] = named  # legacy mirror
                if not item.get("ticker"):
                    item["ticker"] = named[0]
            elif item.get("ticker"):
                item["affected_suppliers"] = [item["ticker"]]
                item["affected_tickers"] = [item["ticker"]]
            else:
                item["affected_suppliers"] = []
                item["affected_tickers"] = []
            enriched.append(item)
        except Exception as e:
            log.error(f"Classification failed — '{item['title'][:60]}': {e}")
            item["signal_type"] = "OTHER"
            item["is_significant"] = False
            item["significance_reason"] = ""
            item["urgency"] = "LOW"
            item["emoji"] = "📰"
            fallback = [item["ticker"]] if item.get("ticker") else []
            item["affected_suppliers"] = fallback
            item["affected_tickers"] = fallback
            enriched.append(item)

    significant = [i for i in enriched if i["is_significant"]]
    log.info(f"Signal detection done — {len(significant)}/{len(enriched)} significant")
    return enriched
