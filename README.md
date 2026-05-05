# Hermes Agent

> See [HANDOVER.md](HANDOVER.md) for the full technical reference and [ROADMAP.md](ROADMAP.md) for the phased plan.

Hermes is a market intelligence crawler and sub-agent of **Icarus AI** — a personal Telegram bot. He watches ~590 suppliers across 17 categories, classifies every signal with Claude Haiku, stores everything in two purpose-built databases, and answers natural language questions including **semantic topic search powered by RAG**.

---

## Role in the System

```
You (Telegram)
     │
     ▼
 ICARUS AI  ──── HTTP API ──→  HERMES AGENT
 (master bot)   (authenticated)  (sub-agent)
     │                                │
     │                     RSS · EDGAR · Tavily
     │                     + 18 industry feeds
     │                                │
     │                     Claude Haiku (signal detection)
     │                                │
     │                   ┌────────────┴────────────┐
     │                   ▼                         ▼
     │            Upstash Redis            Upstash Vector
     │          (exact lookup)            (semantic RAG)
     └──────── pulls on demand ──────────────────────┘
```

**Icarus is master. Hermes never pushes, never alerts, never accesses personal data.**

---

## What Hermes Does

- Crawls ~590 companies via RSS, EDGAR, and Tavily on an automated schedule
- Pulls 18 industry RSS feeds (Supply Chain Dive, Semiconductor Engineering, TechCrunch, etc.) — free and unlimited
- Classifies every item by signal type using Claude Haiku (11 types, HIGH/MEDIUM/LOW urgency)
- Stores items in **Upstash Redis** (key-value, 7-day TTL) and **Upstash Vector** (1024-dim embeddings, BAAI/bge-large-en-v1.5)
- Exposes a REST API so Icarus can query, crawl, and build Miro boards on demand

## What Hermes Does NOT Do

- Send Telegram messages (Icarus does that)
- Access personal data (email, calendar, tasks)
- Make decisions or take actions
- Push data anywhere — consumers pull on demand

---

## Supplier Coverage

~590 companies across 17 categories. 3 tiers by crawl priority.

| Category | Examples |
|---|---|
| Semiconductors & Chips | NVIDIA, Intel, AMD, TSMC, ASML, ARM |
| Memory & Storage | Samsung, Micron, SK Hynix, Western Digital |
| Networking | Cisco, Arista, Palo Alto, Nokia |
| Cloud & Infrastructure | AWS, Azure, Google Cloud, Oracle |
| AI Foundation Labs | OpenAI, Anthropic, Google DeepMind, xAI |
| AI Infrastructure | Cerebras, Groq, SambaNova, Tenstorrent |
| Procurement Software | SAP Ariba, Coupa, Ivalua, Jaggaer |
| Logistics & Supply Chain | DHL, FedEx, UPS, Maersk, XPO |
| Robotics & Drones | Boston Dynamics, Figure AI, ABB, DJI |
| Battery & EV | Tesla, CATL, BYD, LG Energy, Northvolt |
| + 7 more categories | ... |

Plus **18 industry RSS feeds**: Supply Chain Dive, Spend Matters, Semiconductor Engineering, EE Times, IEEE Spectrum, Data Center Knowledge, Next Platform, Ars Technica, MIT Technology Review, TechCrunch, The Register, Wired, and more.

---

## Signal Detection

Every item is classified by Claude Haiku into one of 11 signal types:

| Signal | Emoji | Procurement relevance |
|---|---|---|
| SUPPLY_CHAIN | ⚠️ | High — disruptions, shortages |
| PRICING_CHANGE | 💲 | High — contract impact |
| REGULATORY | ⚖️ | High — compliance actions |
| ACQUISITION | 🤝 | Medium — vendor consolidation |
| EARNINGS | 📊 | Medium — financial stability |
| FUNDING | 💰 | Low — future capability signal |
| PRODUCT_RELEASE | 🆕 | Low — new offerings |
| PARTNERSHIP | 🔗 | Low — ecosystem changes |
| LAYOFFS_HIRING | 👥 | Medium — capacity signals |
| RESEARCH_PAPER | 🔬 | Low — future direction |
| OTHER | 📰 | Neutral |

---

## Database Layer

### Upstash Redis — Exact Lookup
```
hermes:seen:{md5}       Dedup flag — TTL 30 days
hermes:item:{md5}       Full item JSON — TTL 7 days
hermes:supplier:{slug}  List of item IDs — max 3000 per supplier
```

### Upstash Vector — Semantic Search (RAG)
- **Model:** BAAI/bge-large-en-v1.5 (hosted by Upstash, no OpenAI key needed)
- **Dimensions:** 1024, Cosine similarity
- **Text:** `"{supplier} ({category}): {title}. {significance_reason}"`
- **Query:** `/search?q=chip+export+controls` → returns items from ASML, NVIDIA, Applied Materials without naming them

Both databases are updated in a single `store_item()` call. Vector failures never drop the Redis write.

---

## HTTP API

Base URL: `https://hermes-agent-production-114e.up.railway.app`  
Auth: `x-api-key: {HERMES_API_KEY}` header on all endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Status + supplier count |
| GET | `/greet` | Live stats for Icarus |
| GET | `/query/{company}` | Company signals (fuzzy match) |
| GET | `/briefing` | Top significant signals |
| GET | `/search?q=` | **RAG** — semantic topic search |
| POST | `/crawl/rss` | Trigger RSS crawl now |
| POST | `/crawl/edgar` | Trigger EDGAR crawl now |
| POST | `/crawl/tavily` | Trigger Tavily crawl now |
| POST | `/miro/landscape` | Build landscape Miro board |
| POST | `/miro/signals` | Build signal Miro board |
| POST | `/flush` | Clear all data (clean start) |

---

## Crawl Schedule

| Crawler | Frequency | Cost |
|---|---|---|
| RSS + 18 industry feeds | Every 6h | Free, unlimited |
| EDGAR | Daily 07:30 | Free |
| Tavily | Weekly Mon 09:00 | Free tier (~700/month) |

---

## Icarus Tools (Telegram)

Say any of these in Telegram and Icarus will call Hermes:

- **"Greet Hermes"** → live stats
- **"What does Hermes have on NVIDIA?"** → company signal lookup
- **"Give me a Hermes briefing"** → top significant signals
- **"What are chip suppliers saying about export controls?"** → RAG semantic search
- **"Tell Hermes to run a crawl"** → triggers RSS cycle
- **"Build me a Miro landscape for Cloud & Infrastructure"** → Miro board

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| API server | FastAPI + uvicorn |
| Scheduler | APScheduler |
| RSS parsing | feedparser + httpx (8s timeout, 512KB cap) |
| News search | Tavily API |
| SEC filings | EDGAR REST API (public) |
| Signal detection | Claude Haiku (Anthropic) |
| Key-value store | Upstash Redis (REST) |
| Vector search | Upstash Vector (BAAI/bge-large-en-v1.5) |
| Deployment | Railway |

---

## Environment Variables

```
ANTHROPIC_API_KEY          Claude Haiku for signal detection
TAVILY_API_KEY             News search
UPSTASH_REDIS_REST_URL     Upstash Redis
UPSTASH_REDIS_REST_TOKEN   Upstash Redis
UPSTASH_VECTOR_REST_URL    Upstash Vector index
UPSTASH_VECTOR_REST_TOKEN  Upstash Vector index
MIRO_API_TOKEN             Miro REST API
HERMES_API_KEY             Shared secret for HTTP API auth
```

---

## Project Structure

```
hermes-agent/
├── main.py                    FastAPI app + APScheduler
├── config/
│   └── suppliers.py           ~590 companies, 17 categories, 18 industry feeds
├── crawlers/
│   ├── rss_crawler.py         RSS + industry feeds — every 6h
│   ├── tavily_crawler.py      Tavily news search — weekly
│   └── edgar_crawler.py       SEC EDGAR — daily
├── processors/
│   └── signal_detector.py     Claude Haiku signal classification
├── storage/
│   └── redis_store.py         Redis + Vector dual-write, semantic_search(), flush()
├── miro/
│   ├── client.py              Miro REST API wrapper
│   └── boards.py              Landscape + signal board builders
├── integrations/
│   └── hermes_client.py       Standalone connector for SpendLens
└── presentation/
    └── index.html             5-slide HTML deck
```
