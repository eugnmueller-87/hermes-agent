# Hermes Agent

Hermes is the AI market intelligence layer of the SpendLens procurement stack. It watches ~56 AI suppliers across 8 categories, classifies every signal with Claude Haiku, stores everything in two purpose-built databases, and answers natural language questions — including semantic RAG search, company knowledge profiles, and macro trend clustering.

---

## Role in the Stack

Hermes occupies the bottom layer of the architecture — always running, never pushing, serving data on demand to Icarus and Hades.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ICARUS (Personal AI OS)                          │
│                    Telegram · Claude Sonnet 4.6 · icarusai.de               │
│                                                                             │
│   "What does Hermes have on TSMC?"      "Give me a market briefing"         │
│            │                                        │                        │
│            ▼                                        ▼                        │
│    hermes_query("TSMC")                  hermes_briefing()                   │
└─────────────────────────────────────────────────────────────────────────────┘
                        │                            │
                        ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HADES (DD Agent)                               │
│                                                                             │
│  hermes_preflight ──→ reads hermes:supplier:<slug>  (pre-investigation)     │
│  hermes_register  ──→ writes hermes:watchlist:<slug> (post-investigation)   │
│  audit_writer     ──→ writes hades:audit:<slug>      (audit persistence)    │
└─────────────────────────────────────────────────────────────────────────────┘
                        │           ▲           │
                  reads signals     │       registers
                        │        writes         │
                        ▼           │           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HERMES  (this agent)                               │
│                                                                             │
│  Crawlers (scheduled):                                                      │
│  ├─ AI RSS feeds              ── every Friday 05:00                         │
│  └─ Weekly digest             ── every Sunday 18:00                         │
│                                                                             │
│  Processing:                                                                │
│  Claude Haiku → signal classification (type, urgency, significance)        │
│  Claude Sonnet → macro theme clustering (6h cache)                         │
│                                                                             │
│  Storage (dual-write):                                                      │
│  ├─ Upstash Redis  — hermes:item:*, hermes:supplier:*, hermes:profile:*    │
│  │                   hades:audit:*, hermes:watchlist:*                      │
│  └─ Upstash Vector — semantic RAG (BAAI/bge-large-en-v1.5, 1024-dim)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### How Hermes interacts with the rest of the stack

| From | To | What | When |
|---|---|---|---|
| Icarus | Hermes | `GET /query/{company}` | User asks about a specific supplier |
| Icarus | Hermes | `GET /briefing` | User asks for market overview |
| Icarus | Hermes | `GET /search?q=` | Semantic topic search |
| Icarus | Hermes | `GET /clusters` | Macro theme clusters |
| Icarus | Hermes | `POST /crawl/rss` | User triggers manual crawl |
| Hades | Hermes Redis | `get hermes:supplier:<slug>` | Hades pre-flight reads market intel before DD |
| Hades | Hermes Redis | `set hermes:watchlist:<slug>` | Hades registers new supplier after DD |
| Hades | Hermes Redis | `lpush hades:audit:<slug>` | Hades writes audit record after every investigation |

**Hermes never initiates contact with Icarus or Hades. All consumers pull on demand.**

---

## What Hermes Does

- Crawls ~56 AI suppliers via RSS every Friday at 05:00 (8 categories: foundation labs, chips, agents, dev tools, coding, search, voice/multimodal, rising stars)
- Generates a weekly AI intelligence digest every Sunday at 18:00
- Classifies every item with Claude Haiku — 11 signal types, HIGH/MEDIUM/LOW urgency, significance flag
- Builds **company knowledge profiles** that accumulate over time (`hermes:profile:{slug}`)
- Detects **macro theme clusters** across all recent significant signals using Claude Sonnet
- Stores items in **Upstash Redis** (exact lookup, 7-day TTL) and **Upstash Vector** (1024-dim RAG embeddings)
- Exposes a REST API so Icarus and Hades can query, search, profile, and cluster on demand

## What Hermes Does NOT Do

- Send Telegram messages (Icarus does that)
- Access personal data (email, calendar, tasks)
- Make decisions or take actions
- Push data anywhere — all consumers pull on demand

---

## Supplier Coverage

~56 AI companies across 8 categories. Crawled weekly via RSS.

| Category | Examples |
|---|---|
| AI Foundation Labs | OpenAI, Anthropic, Google DeepMind, Mistral, xAI |
| AI Infrastructure & Chips | NVIDIA, Groq, Cerebras, Tenstorrent, SambaNova |
| AI Agents & Orchestration | LangChain, LlamaIndex, CrewAI, AutoGen |
| AI Developer Tools | Hugging Face, Weights & Biases, Scale AI, Together AI |
| AI Coding | Cursor, GitHub Copilot, Cognition (Devin), Replit |
| AI Search & Research | Perplexity AI, Exa AI, Brave Search, Tavily |
| AI Voice & Multimodal | ElevenLabs, Deepgram, HeyGen, Whisper |
| AI Rising Stars | Runway ML, Midjourney, Figure AI, Physical Intelligence |

---

## Signal Detection

Every item is classified by Claude Haiku into one of 11 signal types:

| Signal | Emoji | Relevance |
|---|---|---|
| SUPPLY_CHAIN | ⚠️ | High — disruptions, shortages |
| PRICING_CHANGE | 💲 | High — contract impact |
| REGULATORY | ⚖️ | High — compliance actions |
| ACQUISITION | 🤝 | Medium — vendor consolidation |
| EARNINGS | 📊 | Medium — financial stability |
| LAYOFFS_HIRING | 👥 | Medium — capacity signals |
| FUNDING | 💰 | Low — future capability signal |
| PRODUCT_RELEASE | 🆕 | Low — new offerings |
| PARTNERSHIP | 🔗 | Low — ecosystem changes |
| RESEARCH_PAPER | 🔬 | Low — future direction |
| OTHER | 📰 | Neutral |

---

## Intelligence Layer

### Company Knowledge Profiles
Every stored signal updates a permanent profile at `hermes:profile:{slug}`:
- Total signals, significant count, urgency breakdown
- Top signal types by frequency
- Last 10 signals (summary)
- Risk flags — last 5 HIGH urgency significant signals
- Category, tier, first seen, last updated

Query: `GET /profile/{company}` → full profile with fuzzy name matching.

### Macro Theme Clustering
`GET /clusters` scans recent significant signals and sends them to Claude Sonnet, which groups them into macro themes — each with a synthesis paragraph, companies involved, and urgency distribution. Results are cached 6 hours in Redis.

Example output: *"5 chip suppliers flagged export control risk this week — TSMC, ASML, NVIDIA, KLA, Applied Materials."*

### Hades Integration — Shared Redis
Hermes and Hades share the same Upstash Redis instance. This enables two-way intelligence flow:

- **Hades reads from Hermes** — `hermes_preflight` node reads `hermes:supplier:<slug>` before starting DD. If Hermes has 10+ signals on a supplier, Hades skips NewsAPI and uses Hermes data instead (faster + cheaper).
- **Hades writes to Hermes** — after every investigation, `hermes_register` writes `hermes:watchlist:<slug>` so crawlers pick up the new supplier. `audit_writer` writes `hades:audit:<slug>` for persistent audit history.

---

## Database Layer

### Upstash Redis — Exact Lookup
```
hermes:seen:{md5}        Dedup flag — TTL 30 days
hermes:item:{md5}        Full item JSON — TTL 7 days
hermes:supplier:{slug}   List of item IDs — max 3000 per supplier
hermes:profile:{slug}    Company knowledge profile — permanent, no TTL
hermes:clusters:{date}   Daily macro clusters — TTL 6 hours
hermes:watchlist:{slug}  Hades-registered supplier record — permanent
hades:audit:{slug}       Hades investigation history — list, newest first, max 50
```

### Upstash Vector — Semantic Search (RAG)
- **Model:** BAAI/bge-large-en-v1.5 (hosted by Upstash, no separate API key)
- **Dimensions:** 1024, Cosine similarity
- **Text embedded:** `"{supplier} ({category}): {title}. {significance_reason}"`
- **Query:** `/search?q=chip+export+controls` → returns items from ASML, NVIDIA, Applied Materials without naming them

Both databases are written in a single `store_item()` call. Vector and profile failures are caught and logged — they never drop the Redis write.

---

## HTTP API

Base URL: `https://hermes-agent-production-114e.up.railway.app`  
Auth: `x-api-key: {HERMES_API_KEY}` header on all endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Status + supplier count |
| GET | `/greet` | Live stats for Icarus |
| GET | `/query/{company}` | Recent signals (fuzzy match) |
| GET | `/profile/{company}` | Accumulated company knowledge profile |
| GET | `/briefing` | Top significant signals across all suppliers |
| GET | `/search?q=` | **RAG** — semantic topic/theme search |
| GET | `/clusters` | Macro theme clusters (Claude Sonnet synthesis, 6h cache) |
| GET | `/chart/signals` | QuickChart PNG — signals by urgency |
| GET | `/chart/landscape` | QuickChart PNG — item counts by category |
| POST | `/crawl/rss` | Trigger RSS crawl now |
| POST | `/crawl/edgar` | Trigger EDGAR crawl now |
| POST | `/crawl/tavily` | Trigger Tavily crawl now |
| POST | `/crawl/jobs` | Trigger job postings crawl now |
| POST | `/crawl/transcripts` | Trigger earnings transcripts crawl now |
| POST | `/flush` | Clear all data (clean start) |

---

## Crawl Schedule

| Job | When | What |
|---|---|---|
| AI RSS crawl | Every Friday 05:00 | RSS feeds for ~56 AI suppliers across 8 categories |
| Weekly digest | Every Sunday 18:00 | Claude Sonnet synthesis of the week's AI signals |

Manual triggers available via API for all crawlers (`POST /crawl/rss`, `/crawl/tavily`).

---

## Icarus Tools (Telegram)

| Tool | Example prompt | What it calls |
|---|---|---|
| `hermes_greet` | "Greet Hermes" | `GET /greet` |
| `hermes_query` | "What does Hermes have on TSMC?" | `GET /query/{company}` |
| `hermes_profile` | "What do we know about Cerebras?" | `GET /profile/{company}` |
| `hermes_briefing` | "Give me a Hermes briefing" | `GET /briefing` |
| `hermes_search` | "Any signals about chip export controls?" | `GET /search?q=` |
| `hermes_trends` | "What macro themes are emerging this week?" | `GET /clusters` |
| `hermes_crawl` | "Tell Hermes to run a crawl" | `POST /crawl/{type}` |
| `hermes_chart` | "Show me a signals chart" | `GET /chart/signals` |

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.13 |
| API server | FastAPI + uvicorn |
| Scheduler | APScheduler (cron-style) |
| RSS parsing | feedparser + httpx (8s timeout, 512KB cap) |
| News search | Tavily API |
| SEC filings | EDGAR REST API (public) |
| Signal detection | Claude Haiku (Anthropic) |
| Cluster synthesis | Claude Sonnet (Anthropic) |
| Key-value store | Upstash Redis (REST) |
| Vector search | Upstash Vector (BAAI/bge-large-en-v1.5) |
| Chart generation | QuickChart.io (free, no API key) |
| Deployment | Railway (24/7, auto-deploy on push) |

---

## Environment Variables

```
ANTHROPIC_API_KEY          Claude Haiku (signals) + Claude Sonnet (clusters)
TAVILY_API_KEY             Tavily news search + job postings
UPSTASH_REDIS_REST_URL     Upstash Redis instance (shared with Hades)
UPSTASH_REDIS_REST_TOKEN   Upstash Redis instance (shared with Hades)
UPSTASH_VECTOR_REST_URL    Upstash Vector index
UPSTASH_VECTOR_REST_TOKEN  Upstash Vector index
HERMES_API_KEY             Shared secret for HTTP API auth
```

---

## Project Structure

```
hermes-agent/
├── main.py                        FastAPI app + APScheduler
├── config/
│   └── suppliers.py               ~56 AI companies, 8 categories, 3 tiers
├── crawlers/
│   ├── rss_crawler.py             AI RSS feeds — every Friday 05:00
│   ├── edgar_crawler.py           SEC EDGAR filings (manual trigger)
│   ├── tavily_crawler.py          Tavily web search (manual trigger)
│   ├── jobs_crawler.py            Job postings (manual trigger)
│   └── transcripts_crawler.py     Earnings 8-K full text (manual trigger)
├── processors/
│   └── signal_detector.py         Claude Haiku signal classification
├── intelligence/
│   ├── digest.py                  Claude Sonnet weekly AI digest — every Sunday 18:00
│   └── clusters.py                Claude Sonnet macro theme clustering
├── storage/
│   └── redis_store.py             Redis + Vector dual-write, profiles, semantic_search()
├── charts/
│   └── quickchart.py              QuickChart.io PNG generation
└── integrations/
    └── hermes_client.py           Standalone connector for Hades + SpendLens
```

---

## Part of the SpendLens Stack

| Agent | Role |
|---|---|
| **Icarus** | Personal AI OS — user interface, orchestrates all three agents |
| **SpendLens** | Spend analytics platform — vendor records, approval workflows |
| **Hades** | Supplier due diligence — writes to Hermes Redis after every investigation |
| **Hermes** | Market intelligence foundation — crawls signals, serves data on demand |
