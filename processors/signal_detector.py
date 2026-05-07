import json
import logging
import os

import anthropic

log = logging.getLogger("hermes.signal")

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

PROMPT = """You are a market intelligence analyst. Classify this news item and decide if it is significant enough to alert a business user.

Company: {supplier}
Title: {title}
Summary: {summary}
Source: {source}

Respond with JSON only:
{{
  "signal_type": "<one of: FUNDING, ACQUISITION, PRODUCT_RELEASE, PRICING_CHANGE, SUPPLY_CHAIN, EARNINGS, PARTNERSHIP, REGULATORY, LAYOFFS_HIRING, RESEARCH_PAPER, OTHER>",
  "is_significant": <true or false>,
  "significance_reason": "<one sentence why this matters, or empty string if not significant>",
  "urgency": "<HIGH, MEDIUM, LOW>"
}}

Mark is_significant=true only for: funding rounds, acquisitions, major product launches, pricing changes, supply chain disruptions, earnings surprises, major partnerships, regulatory actions, large layoffs, or breakthrough research.
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
                max_tokens=256,
                messages=[
                    {
                        "role": "user",
                        "content": PROMPT.format(
                            supplier=item["supplier"],
                            title=item["title"],
                            summary=item["summary"],
                            source=item["source"],
                        ),
                    }
                ],
            )
            result = json.loads(message.content[0].text)
            item["signal_type"] = result.get("signal_type", "OTHER")
            item["is_significant"] = result.get("is_significant", False)
            item["significance_reason"] = result.get("significance_reason", "")
            item["urgency"] = result.get("urgency", "LOW")
            item["emoji"] = SIGNAL_TYPES.get(item["signal_type"], "📰")
            enriched.append(item)
        except Exception as e:
            log.error(f"Classification failed — '{item['title'][:60]}': {e}")
            item["signal_type"] = "OTHER"
            item["is_significant"] = False
            item["significance_reason"] = ""
            item["urgency"] = "LOW"
            item["emoji"] = "📰"
            enriched.append(item)

    significant = [i for i in enriched if i["is_significant"]]
    log.info(f"Signal detection done — {len(significant)}/{len(enriched)} significant")
    return enriched
