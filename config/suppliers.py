SUPPLIERS = {
    "ai_foundation_labs": [
        {"name": "Anthropic", "ticker": None, "rss": "https://www.anthropic.com/rss.xml", "tier": 1},
        {"name": "OpenAI", "ticker": None, "rss": "https://openai.com/blog/rss.xml", "tier": 1},
        {"name": "Google DeepMind", "ticker": "GOOGL", "rss": "https://deepmind.google/blog/rss.xml", "tier": 1},
        {"name": "Meta AI", "ticker": "META", "rss": "https://ai.meta.com/blog/rss/", "tier": 1},
        {"name": "Mistral AI", "ticker": None, "rss": "https://mistral.ai/news/rss", "tier": 1},
        {"name": "xAI (Grok)", "ticker": None, "rss": None, "tier": 1},
        {"name": "Cohere", "ticker": None, "rss": None, "tier": 1},
        {"name": "AI21 Labs", "ticker": None, "rss": None, "tier": 2},
        {"name": "Aleph Alpha", "ticker": None, "rss": None, "tier": 2},
        {"name": "Baidu AI", "ticker": "BIDU", "rss": None, "tier": 2},
    ],
    "ai_infrastructure_chips": [
        {"name": "NVIDIA", "ticker": "NVDA", "rss": "https://nvidianews.nvidia.com/releases.xml", "tier": 1},
        {"name": "Groq", "ticker": None, "rss": None, "tier": 1},
        {"name": "Cerebras Systems", "ticker": None, "rss": None, "tier": 1},
        {"name": "Tenstorrent", "ticker": None, "rss": None, "tier": 1},
        {"name": "Amazon Trainium (AWS)", "ticker": "AMZN", "rss": None, "tier": 1},
        {"name": "Google TPU", "ticker": "GOOGL", "rss": None, "tier": 1},
        {"name": "Microsoft Maia", "ticker": "MSFT", "rss": None, "tier": 1},
        {"name": "SambaNova Systems", "ticker": None, "rss": None, "tier": 2},
        {"name": "Graphcore", "ticker": None, "rss": None, "tier": 2},
    ],
    "ai_agents_orchestration": [
        {"name": "LangChain", "ticker": None, "rss": "https://blog.langchain.dev/rss/", "tier": 1},
        {"name": "LlamaIndex", "ticker": None, "rss": None, "tier": 1},
        {"name": "CrewAI", "ticker": None, "rss": None, "tier": 1},
        {"name": "AutoGen (Microsoft)", "ticker": "MSFT", "rss": None, "tier": 1},
        {"name": "Dify", "ticker": None, "rss": None, "tier": 2},
        {"name": "n8n", "ticker": None, "rss": None, "tier": 2},
        {"name": "Zapier AI", "ticker": None, "rss": None, "tier": 2},
    ],
    "ai_developer_tools": [
        {"name": "Hugging Face", "ticker": None, "rss": "https://huggingface.co/blog/feed.xml", "tier": 1},
        {"name": "Replicate", "ticker": None, "rss": None, "tier": 1},
        {"name": "Weights & Biases", "ticker": None, "rss": None, "tier": 1},
        {"name": "Scale AI", "ticker": None, "rss": None, "tier": 1},
        {"name": "Together AI", "ticker": None, "rss": None, "tier": 1},
        {"name": "Fireworks AI", "ticker": None, "rss": None, "tier": 2},
        {"name": "Anyscale", "ticker": None, "rss": None, "tier": 2},
    ],
    "ai_coding": [
        {"name": "Cursor", "ticker": None, "rss": "https://www.cursor.com/blog/rss.xml", "tier": 1},
        {"name": "GitHub Copilot", "ticker": "MSFT", "rss": None, "tier": 1},
        {"name": "Cognition (Devin)", "ticker": None, "rss": None, "tier": 1},
        {"name": "Replit", "ticker": None, "rss": None, "tier": 1},
        {"name": "Windsurf (Codeium)", "ticker": None, "rss": None, "tier": 2},
        {"name": "Sourcegraph (Cody)", "ticker": None, "rss": None, "tier": 2},
    ],
    "ai_search_research": [
        {"name": "Perplexity AI", "ticker": None, "rss": None, "tier": 1},
        {"name": "Exa AI", "ticker": None, "rss": None, "tier": 2},
        {"name": "Brave Search", "ticker": None, "rss": None, "tier": 2},
        {"name": "Tavily", "ticker": None, "rss": None, "tier": 2},
    ],
    "ai_voice_multimodal": [
        {"name": "ElevenLabs", "ticker": None, "rss": None, "tier": 1},
        {"name": "Deepgram", "ticker": None, "rss": None, "tier": 2},
        {"name": "HeyGen", "ticker": None, "rss": None, "tier": 2},
        {"name": "Synthesia", "ticker": None, "rss": None, "tier": 2},
        {"name": "Whisper (OpenAI)", "ticker": None, "rss": None, "tier": 1},
    ],
    "ai_rising_stars": [
        {"name": "Pika Labs", "ticker": None, "rss": None, "tier": 1},
        {"name": "Runway ML", "ticker": None, "rss": None, "tier": 1},
        {"name": "Midjourney", "ticker": None, "rss": None, "tier": 1},
        {"name": "Physical Intelligence", "ticker": None, "rss": None, "tier": 1},
        {"name": "Figure AI", "ticker": None, "rss": None, "tier": 1},
        {"name": "Character.AI", "ticker": None, "rss": None, "tier": 2},
        {"name": "Stability AI", "ticker": None, "rss": None, "tier": 2},
        {"name": "Glean", "ticker": None, "rss": None, "tier": 2},
    ],
}

ALL_SUPPLIERS = [s for category in SUPPLIERS.values() for s in category]
_seen = set()
_deduped = []
for s in ALL_SUPPLIERS:
    if s["name"] not in _seen:
        _seen.add(s["name"])
        _deduped.append(s)
ALL_SUPPLIERS = _deduped

TIER_1 = [s for s in ALL_SUPPLIERS if s["tier"] == 1]
TIER_2 = [s for s in ALL_SUPPLIERS if s["tier"] == 2]
TIER_3 = [s for s in ALL_SUPPLIERS if s["tier"] == 3]

# ── Tier A: Financial news feeds — high volume, crawl every 4h ───────────────
# These publish market-moving stories with tradeable tickers.
# require_ticker=False — signal_detector extracts tickers from article content.
NEWS_FEEDS = [
    # Financial news — direct market relevance
    {"name": "Reuters Markets",       "ticker": None, "rss": "https://feeds.reuters.com/reuters/businessNews",                           "tier": "news"},
    {"name": "Reuters Technology",    "ticker": None, "rss": "https://feeds.reuters.com/reuters/technologyNews",                          "tier": "news"},
    {"name": "Yahoo Finance",         "ticker": None, "rss": "https://finance.yahoo.com/news/rss/",                                      "tier": "news"},
    {"name": "Seeking Alpha",         "ticker": None, "rss": "https://seekingalpha.com/feed.xml",                                        "tier": "news"},
    {"name": "MarketWatch",           "ticker": None, "rss": "https://feeds.marketwatch.com/marketwatch/topstories/",                    "tier": "news"},
    {"name": "Investing.com Tech",    "ticker": None, "rss": "https://www.investing.com/rss/news_25.rss",                                "tier": "news"},
    # Tech news with strong ticker signal
    {"name": "TechCrunch",           "ticker": None, "rss": "https://techcrunch.com/feed/",                                             "tier": "news"},
    {"name": "VentureBeat AI",       "ticker": None, "rss": "https://venturebeat.com/category/ai/feed/",                                "tier": "news"},
]

# ── Tier B: Company IR / press releases — direct ticker mapping ───────────────
# Every post from these sources maps directly to a ticker — high signal quality.
COMPANY_BLOGS = [
    # Chip & hardware — core AI infrastructure plays
    {"name": "NVIDIA",               "ticker": "NVDA",  "rss": "https://nvidianews.nvidia.com/releases.xml",           "tier": "company"},
    {"name": "AMD",                  "ticker": "AMD",   "rss": "https://ir.amd.com/news-releases/rss",                 "tier": "company"},
    {"name": "Intel",                "ticker": "INTC",  "rss": "https://www.intel.com/content/www/us/en/newsroom/rss-tech-innovation.xml", "tier": "company"},
    {"name": "TSMC",                 "ticker": "TSM",   "rss": "https://www.tsmc.com/english/news/rss",                 "tier": "company"},
    # Big tech AI
    {"name": "Google DeepMind",      "ticker": "GOOGL", "rss": "https://deepmind.google/blog/rss.xml",                 "tier": "company"},
    {"name": "Microsoft AI",         "ticker": "MSFT",  "rss": "https://blogs.microsoft.com/ai/feed/",                 "tier": "company"},
    {"name": "Meta AI",              "ticker": "META",  "rss": "https://ai.meta.com/blog/rss/",                        "tier": "company"},
    {"name": "Apple ML",             "ticker": "AAPL",  "rss": "https://machinelearning.apple.com/rss.xml",            "tier": "company"},
    {"name": "AWS AI",               "ticker": "AMZN",  "rss": "https://aws.amazon.com/blogs/machine-learning/feed/",  "tier": "company"},
    # Cloud & software
    {"name": "Salesforce",           "ticker": "CRM",   "rss": "https://www.salesforce.com/blog/feed/",                "tier": "company"},
    {"name": "Palantir",             "ticker": "PLTR",  "rss": "https://blog.palantir.com/feed",                       "tier": "company"},
    {"name": "Snowflake",            "ticker": "SNOW",  "rss": "https://www.snowflake.com/blog/feed/",                 "tier": "company"},
    {"name": "Datadog",              "ticker": "DDOG",  "rss": "https://www.datadoghq.com/blog/feed.xml",              "tier": "company"},
    {"name": "Cloudflare",           "ticker": "NET",   "rss": "https://blog.cloudflare.com/rss/",                     "tier": "company"},
    # Private AI — routed to listed parent/beneficiary
    {"name": "OpenAI",               "ticker": "MSFT",  "rss": "https://openai.com/blog/rss.xml",                     "tier": "company"},
]

# ── Tier C: Tavily deep search — weekly, covers suppliers with no RSS ─────────
# All 56 suppliers in SUPPLIERS dict are covered here via Tavily.

INDUSTRY_FEEDS = []
