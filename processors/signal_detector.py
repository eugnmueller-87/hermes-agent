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

PROMPT = """You are a market intelligence analyst for an algorithmic trading system. Classify this news item and extract any tradeable stock tickers mentioned.

Source: {source}
Company/Feed: {supplier}
Title: {title}
Summary: {summary}
Pre-mapped ticker (if any): {ticker}

Respond with JSON only:
{{
  "signal_type": "<one of: FUNDING, ACQUISITION, PRODUCT_RELEASE, PRICING_CHANGE, SUPPLY_CHAIN, EARNINGS, PARTNERSHIP, REGULATORY, LAYOFFS_HIRING, RESEARCH_PAPER, OTHER>",
  "is_significant": <true or false>,
  "significance_reason": "<one sentence why this matters for stock price, or empty string if not significant>",
  "urgency": "<HIGH, MEDIUM, LOW>",
  "affected_tickers": ["<list of US-listed stock tickers mentioned, e.g. NVDA, MSFT, AAPL — empty list if none>"]
}}

Mark is_significant=true ONLY for hard, discrete events: earnings beats/misses with specific numbers, completed acquisitions, confirmed major product launches, large funding rounds ($100M+), confirmed supply chain disruptions at a named company, regulatory actions with named company, mass layoffs (>500 people) with named employer, guidance changes with specific figures.

Mark is_significant=false for: opinion pieces, commentary, analysis without new facts, rate/mortgage/consumer finance articles, how-to guides, blog posts, tutorials, research papers without commercial impact, minor product updates, speculation, predictions, lifestyle articles, anything without a specific named public company as the subject.

signal_type rules:
- SUPPLY_CHAIN: only for actual disruptions at a named company's supply chain (not general commodity commentary)
- EARNINGS: only for actual reported earnings numbers, not estimates or previews
- OTHER: use for opinion, commentary, analysis, consumer finance, personal finance, lifestyle

IMPORTANT: affected_tickers must only contain real US-listed ticker symbols (NYSE/NASDAQ). If a company is private (OpenAI, Anthropic, etc.) but has a listed parent/backer, include that instead (e.g. OpenAI → MSFT). Consumer finance articles (mortgages, HELOCs, credit cards, personal loans) almost never have affected_tickers — return empty list.
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
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```", 2)[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            result = json.loads(raw)
            item["signal_type"] = result.get("signal_type", "OTHER")
            item["is_significant"] = result.get("is_significant", False)
            item["significance_reason"] = result.get("significance_reason", "")
            item["urgency"] = result.get("urgency", "LOW")
            item["emoji"] = SIGNAL_TYPES.get(item["signal_type"], "📰")
            # Use LLM-extracted tickers, falling back to pre-mapped ticker
            llm_tickers = result.get("affected_tickers", [])
            if llm_tickers:
                item["affected_tickers"] = llm_tickers
                item["ticker"] = llm_tickers[0]  # primary ticker
            elif item.get("ticker"):
                item["affected_tickers"] = [item["ticker"]]
            else:
                item["affected_tickers"] = []
            enriched.append(item)
        except Exception as e:
            log.error(f"Classification failed — '{item['title'][:60]}': {e}")
            item["signal_type"] = "OTHER"
            item["is_significant"] = False
            item["significance_reason"] = ""
            item["urgency"] = "LOW"
            item["emoji"] = "📰"
            item.setdefault("affected_tickers", [item["ticker"]] if item.get("ticker") else [])
            enriched.append(item)

    significant = [i for i in enriched if i["is_significant"]]
    log.info(f"Signal detection done — {len(significant)}/{len(enriched)} significant")
    return enriched
