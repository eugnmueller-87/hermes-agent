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

AI_EXTRA_SOURCES = [
    {"name": "Import AI Newsletter", "rss": "https://importai.substack.com/feed"},
    {"name": "The Batch (DeepLearning.AI)", "rss": "https://www.deeplearning.ai/the-batch/feed/"},
    {"name": "Hugging Face Blog", "rss": "https://huggingface.co/blog/feed.xml"},
    {"name": "arXiv cs.AI", "rss": "https://rss.arxiv.org/rss/cs.AI"},
    {"name": "arXiv cs.LG", "rss": "https://rss.arxiv.org/rss/cs.LG"},
    {"name": "TechCrunch AI", "rss": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "VentureBeat AI", "rss": "https://venturebeat.com/category/ai/feed/"},
    {"name": "The Verge AI", "rss": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "MIT Technology Review AI", "rss": "https://www.technologyreview.com/feed/"},
]

INDUSTRY_FEEDS = []
