# Hermes Agent — Handover Document

## What is Hermes?

Hermes is a market intelligence crawler that serves as a read-only data source for Icarus. He crawls the external tech and AI world — supplier news, filings, funding rounds, model releases — and stores everything in a shared Upstash Redis instance. Icarus pulls from Hermes on demand. Hermes never pushes, never alerts, never has access to personal data.

## Core Architecture Principle

```
Hermes                        Redis (shared)              Icarus
------                        --------------              ------
Crawls external world  →→→   hermes:* namespace   ←←←   Pulls on demand
Stores structured data        (read/write)               Owns personal data
Runs on its own schedule      hermes:item:*              (Gmail, Calendar,
Never touches Telegram        hermes:seen:*               Tasks, Redis personal
Never sees personal data      hermes:supplier:*           namespace)
```

Icarus is the master. Hermes is a data source. This separation is intentional and must be preserved.

## What Is Built

### File Structure
```
hermes-agent/
├── main.py                    Entry point + APScheduler
├── railway.toml               Railway deployment config
├── requirements.txt
├── .env.example               All required environment variables
├── config/
│   └── suppliers.py           ~250 companies across 17 categories
├── crawlers/
│   ├── rss_crawler.py         RSS feeds — runs every 6h
│   ├── tavily_crawler.py      Tavily news search — runs daily
│   └── edgar_crawler.py       SEC EDGAR filings — US public companies
├── processors/
│   └── signal_detector.py     Claude Haiku classifies each item by signal type
├── storage/
│   └── redis_store.py         Upstash Redis — dedup, store, query interface
└── notifier/
    └── telegram_notifier.py   ⚠️ TO BE REMOVED — Icarus is master, Hermes does not push
```

### Supplier Coverage (17 categories, ~250 companies)

| Category | Count |
|---|---|
| Semiconductors & Chips | 30 |
| Memory & Storage | 12 |
| Networking & Connectivity | 20 |
| Cloud & Infrastructure | 14 |
| Servers & IT Hardware | 13 |
| Contract Manufacturing | 12 |
| Cables, Connectors & Passives | 10 |
| Power & Energy | 8 |
| Test & Measurement | 7 |
| Cybersecurity | 12 |
| Optical & Fiber | 6 |
| Cooling & Thermal | 5 |
| Distributors & Resellers | 12 |
| Enterprise Software | 11 |
| Industrial & Automation | 9 |
| AI Foundation Labs | 10 |
| AI Infrastructure & Chips | 10 |
| AI Agents & Orchestration | 8 |
| AI Developer Tools | 8 |
| AI Coding | 8 |
| AI Search & Research | 5 |
| AI Voice & Multimodal | 6 |
| AI Rising Stars | 16 |

### Signal Types Detected (via Claude Haiku)

| Signal | Emoji | Examples |
|---|---|---|
| FUNDING | 💰 | New investment rounds |
| ACQUISITION | 🤝 | M&A activity |
| PRODUCT_RELEASE | 🆕 | New models, products |
| PRICING_CHANGE | 💲 | API price changes |
| SUPPLY_CHAIN | ⚠️ | Disruptions, shortages |
| EARNINGS | 📊 | Financial results |
| PARTNERSHIP | 🔗 | New partnerships |
| REGULATORY | ⚖️ | Compliance, legal actions |
| LAYOFFS_HIRING | 👥 | Major headcount changes |
| RESEARCH_PAPER | 🔬 | arXiv, breakthrough research |
| OTHER | 📰 | Everything else |

### Crawl Schedule

| Crawler | Frequency | Coverage |
|---|---|---|
| RSS | Every 6h | All companies with RSS feeds |
| EDGAR | Daily at 07:30 | Tier 1+2 US-listed companies |
| Tavily | Daily at 08:00 | Tier 1+2 companies |
| Full Tavily sweep | Weekly (Monday) | All tiers |

### Redis Key Schema

```
hermes:seen:{md5_hash}          Dedup flag — TTL 30 days
hermes:item:{md5_hash}          Full item JSON — TTL 7 days
hermes:supplier:{slug}          List of item IDs per supplier — max 50
```

## What Is NOT Built Yet

- [ ] Telegram notifier removal (Hermes should not push — Icarus pulls)
- [ ] Icarus query commands ("what does Hermes have on X?")
- [ ] Knowledge layer — structured company profiles that grow over time
- [ ] Miro Agent — visualization and presentations
- [ ] GitHub repo created for hermes-agent
- [ ] Railway deployment

## Environment Variables Required

```
ANTHROPIC_API_KEY       Claude Haiku for signal detection
TAVILY_API_KEY          News search (already in Icarus)
UPSTASH_REDIS_REST_URL  Same instance as Icarus (already exists)
UPSTASH_REDIS_REST_TOKEN Same instance as Icarus (already exists)
```

Note: No Telegram vars. Hermes does not send messages.

## Key Decisions Made

1. **Icarus is master** — Hermes never pushes data, never accesses personal namespaces
2. **Shared Redis** — Zero extra infra, Icarus reads `hermes:*` keys on demand
3. **Railway deployment** — Same platform as Icarus, same billing, easy monitoring
4. **Claude Haiku for classification** — Fast and cheap for high-volume signal detection
5. **Tiered crawling** — Tier 1 companies get more frequent checks than Tier 3
6. **New GitHub repo** — `hermes-agent` kept separate from Personal-Assistent for clean modularity

## Deployment Target

- Platform: Railway (new service, same project as Icarus)
- Process: `python main.py` (blocking scheduler)
- Restart policy: always, max 5 retries
