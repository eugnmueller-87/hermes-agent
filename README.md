# Hermes Agent

Hermes is a market intelligence crawler and a supporting sub-agent of **Icarus AI**, a personal operations system. While Icarus manages your personal world — calendar, email, tasks, Telegram — Hermes watches the external world: tech suppliers, AI companies, semiconductor markets, SEC filings, and research. He stores everything he finds in a shared Redis instance. Icarus pulls from it on demand.

---

## Role in the Icarus System

```
┌─────────────────────────────────────────────────────────────┐
│                        ICARUS AI                            │
│                    (Master Agent)                           │
│                                                             │
│   Gmail · Calendar · Tasks · Telegram · Personal Data      │
│                          │                                  │
│              asks "what do you have on X?"                  │
│                          │                                  │
│              ┌───────────▼───────────┐                      │
│              │     Shared Redis      │                      │
│              │    hermes:* keys      │                      │
│              └───────────▲───────────┘                      │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │ writes
               ┌───────────┴───────────┐
               │      HERMES AGENT     │
               │    (Sub-Agent)        │
               │                       │
               │  RSS · Tavily · EDGAR │
               │  Claude Haiku         │
               │  ~250 companies       │
               └───────────────────────┘
```

**Icarus is master. Hermes never pushes, never alerts, never accesses personal data.**

Hermes writes to the `hermes:*` Redis namespace. Everything else belongs to Icarus. This separation is intentional and permanent.

---

## Responsibilities

### What Hermes Does
- Crawls RSS feeds, Tavily news search, and SEC EDGAR filings for ~250 tracked companies
- Classifies every news item by signal type using Claude Haiku
- Stores structured intelligence in Upstash Redis under the `hermes:*` namespace
- Deduplicates items so nothing is processed twice
- Runs continuously on Railway on an automated schedule

### What Hermes Does NOT Do
- Send Telegram messages (Icarus does that)
- Access personal data (email, calendar, tasks)
- Make decisions or take actions
- Push data anywhere — Icarus pulls on demand

---

## Supplier Coverage

~250 companies across 17 categories, organised into 3 tiers by priority.

| Category | Examples |
|---|---|
| Semiconductors & Chips | NVIDIA, Intel, AMD, TSMC, Qualcomm |
| Memory & Storage | Samsung, Micron, SK Hynix, Western Digital |
| Networking & Connectivity | Cisco, Arista, Juniper, Palo Alto |
| Cloud & Infrastructure | AWS, Azure, Google Cloud, Oracle |
| Servers & IT Hardware | Dell, HPE, Supermicro, Lenovo |
| Contract Manufacturing | Foxconn, Flex, Jabil, Celestica |
| AI Foundation Labs | OpenAI, Anthropic, Google DeepMind, Meta AI |
| AI Infrastructure & Chips | Cerebras, Groq, SambaNova, Tenstorrent |
| AI Agents & Orchestration | LangChain, Cohere, Mistral |
| AI Coding | GitHub Copilot, Cursor, Tabnine |
| Power & Energy | Eaton, Vertiv, Schneider Electric |
| Cybersecurity | CrowdStrike, SentinelOne, Palo Alto |
| + 6 more categories | ... |

**Tier 1** — highest priority, crawled most frequently  
**Tier 2** — important, included in weekly Tavily sweep  
**Tier 3** — broader coverage, included in full sweeps  

---

## Signal Detection

Every item is classified by Claude Haiku into one of 11 signal types:

| Signal | Emoji | Triggers On |
|---|---|---|
| FUNDING | 💰 | Investment rounds, capital raises |
| ACQUISITION | 🤝 | M&A activity, buyouts |
| PRODUCT_RELEASE | 🆕 | New models, hardware, software |
| PRICING_CHANGE | 💲 | API pricing, contract changes |
| SUPPLY_CHAIN | ⚠️ | Disruptions, shortages, delays |
| EARNINGS | 📊 | Financial results, guidance |
| PARTNERSHIP | 🔗 | New partnerships, integrations |
| REGULATORY | ⚖️ | Compliance actions, legal |
| LAYOFFS_HIRING | 👥 | Major headcount changes |
| RESEARCH_PAPER | 🔬 | arXiv, breakthrough research |
| OTHER | 📰 | Everything else |

Each item is also rated **HIGH / MEDIUM / LOW** urgency and flagged `is_significant` if it warrants attention.

---

## Crawl Schedule

| Crawler | Frequency | Coverage | Cost |
|---|---|---|---|
| RSS | Every 6 hours | All companies with RSS feeds | Free |
| EDGAR | Daily 07:30 | US-listed Tier 1+2 companies | Free |
| Tavily | Weekly (Monday 09:00) | Tier 1+2 (~177 companies) | Free tier |

Tavily is intentionally capped at weekly to stay within the free tier (~700 searches/month). ~300 searches/month are held in reserve for on-demand Icarus queries.

---

## Redis Key Schema

```
hermes:seen:{md5_hash}       Dedup flag — TTL 30 days
hermes:item:{md5_hash}       Full item JSON — TTL 7 days
hermes:supplier:{slug}       List of item IDs per supplier — max 50
```

### Item Schema
```json
{
  "id": "md5 hash of URL",
  "supplier": "NVIDIA",
  "title": "NVIDIA announces new H200 cluster",
  "url": "https://...",
  "summary": "...",
  "published": "2026-05-04T10:00:00Z",
  "source": "rss | tavily | edgar",
  "signal_type": "PRODUCT_RELEASE",
  "is_significant": true,
  "significance_reason": "Major new hardware launch affecting AI infrastructure supply.",
  "urgency": "HIGH",
  "emoji": "🆕"
}
```

---

## How Icarus and Hermes Work Together

### Phase 2 — On-Demand Queries (planned)
Icarus will expose Telegram commands that pull directly from Hermes Redis:

```
You → Telegram:  "What does Hermes have on TSMC?"
Icarus           reads hermes:supplier:tsmc → formats items
Icarus → You:    "Last 5 items on TSMC: ..."

You → Telegram:  "Any AI signals today?"
Icarus           scans hermes:item:* filtered by date + category
Icarus → You:    "3 significant AI signals today: ..."

You → Telegram:  "Give me a Hermes briefing"
Icarus           pulls top 5 significant items across all suppliers
Icarus → You:    "Today's top signals: 💰 Cerebras raises $250M..."
```

### Phase 3 — Knowledge Layer (planned)
Hermes will build living company profiles at `hermes:profile:{slug}` — not just news items but structured intelligence: funding history, key products, pricing notes, risk flags.

### Phase 5 — Morning Briefing Enrichment (planned)
Icarus morning briefing will optionally include top Hermes signals from the past 24 hours — pulled by Icarus at 06:00, never pushed by Hermes.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.14 |
| Scheduler | APScheduler |
| News search | Tavily API |
| RSS parsing | feedparser |
| SEC filings | EDGAR REST API (public) |
| Signal detection | Claude Haiku (Anthropic) |
| Storage | Upstash Redis (REST) |
| Deployment | Railway |

---

## Environment Variables

```
ANTHROPIC_API_KEY        Claude Haiku for signal detection
TAVILY_API_KEY           News search
UPSTASH_REDIS_REST_URL   Shared Redis instance (same as Icarus)
UPSTASH_REDIS_REST_TOKEN Shared Redis instance (same as Icarus)
```

No Telegram variables. Hermes does not send messages.

---

## Project Structure

```
hermes-agent/
├── main.py                    Entry point + APScheduler
├── railway.toml               Railway deployment config
├── requirements.txt
├── .env.example
├── config/
│   └── suppliers.py           ~250 companies across 17 categories
├── crawlers/
│   ├── rss_crawler.py         RSS feeds — every 6h
│   ├── tavily_crawler.py      Tavily news search — weekly
│   └── edgar_crawler.py       SEC EDGAR filings — daily
├── processors/
│   └── signal_detector.py     Claude Haiku signal classification
└── storage/
    └── redis_store.py         Upstash Redis interface
```

---

## Part of the Icarus System

| Agent | Role |
|---|---|
| **Icarus** | Master agent — personal operations, Telegram, decisions |
| **Hermes** | Sub-agent — external market intelligence, read-only data source |
| **Miro Agent** | Planned — visual boards and presentations from Hermes data |
