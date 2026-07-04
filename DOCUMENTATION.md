# Hermes — Full Documentation (2026-05-09)

## What Hermes is

Market intelligence sub-agent of Icarus AI. Crawls ~590 companies across 17 categories, classifies signals with Claude Haiku, stores everything in Upstash Redis + Upstash Vector, and exposes a REST API for Icarus and SpendLens to query on demand.

**Key principle:** Hermes never pushes, never alerts, never accesses personal data. All consumers pull on demand.

**Live URL:** `https://hermes-agent-production-114e.up.railway.app`
**Auth:** `X-API-Key: {HERMES_API_KEY}` header on all endpoints

---

## Architecture

```
You (Telegram)
     ↓
ICARUS AI ──HTTP──→ HERMES AGENT
(master)   (auth)   (sub-agent)
                         ↓
          Crawlers: RSS · EDGAR · Tavily · Jobs · Transcripts
                         ↓
                   Claude Haiku (signal classification)
                         ↓
              ┌──────────────────────┐
              ↓                      ↓
          Upstash Redis         Upstash Vector
        (exact lookup)         (semantic RAG)
```

---

## Full HTTP API

### Health & Status

| Method | Endpoint | Auth | Response |
|--------|----------|------|----------|
| GET | `/health` | No | `{"status": "ok", "suppliers": 590}` |
| GET | `/greet` | Yes | Stats + latest signal summary |

### Intelligence

| Method | Endpoint | Params | Response |
|--------|----------|--------|----------|
| GET | `/query/{company}` | `limit=5` | Signals for a specific company (Redis lookup) |
| GET | `/briefing` | `limit=10` | Top signals across all categories |
| GET | `/search` | `q=string`, `limit=10` | Semantic search across all signals (Vector RAG) |
| GET | `/clusters` | `refresh=false` | Macro theme clusters (6h cache) |
| GET | `/profile/{company}` | — | Full company knowledge profile |
| GET | `/digest` | `refresh=false` | Weekly digest |
| GET | `/trends/delta` | — | This week vs last week cluster comparison |

### Watchlist

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/watchlist` | `{"watchlist": [...], "count": int}` |
| POST | `/watchlist/{company}` | `{"status": "added", "slug": "..."}` |
| DELETE | `/watchlist/{company}` | `{"status": "removed", "slug": "..."}` |

Watchlist companies get RSS crawled every 2 hours (vs 6 hours for the full set).

### Crawlers (manual trigger)

| Method | Endpoint | What it runs |
|--------|----------|-------------|
| POST | `/crawl/rss` | RSS crawler across all suppliers |
| POST | `/crawl/edgar` | SEC EDGAR filing crawler |
| POST | `/crawl/tavily` | Tavily AI news search |
| POST | `/crawl/jobs` | Job board postings crawler |
| POST | `/crawl/transcripts` | Earnings call transcript crawler |

### Visualization & Admin

| Method | Endpoint | Response |
|--------|----------|----------|
| GET | `/chart/signals` | `{"url": "..."}` — QuickChart PNG of signal urgency distribution |
| GET | `/chart/landscape` | `{"url": "..."}` — QuickChart PNG of category landscape |
| POST | `/flush` | Clears all Redis data (destructive — dev only) |

---

## Data models

### Signal Item

```json
{
  "id": "md5(url)",
  "supplier": "NVIDIA",
  "category": "semiconductors",
  "title": "NVIDIA Announces H200 GPU",
  "url": "https://...",
  "summary": "First 500 chars...",
  "published": "2026-05-05T10:00:00Z",
  "source": "rss|tavily|edgar|jobs|transcripts",
  "signal_type": "PRODUCT_RELEASE|FUNDING|ACQUISITION|PRICING_CHANGE|SUPPLY_CHAIN|EARNINGS|PARTNERSHIP|REGULATORY|LAYOFFS_HIRING|RESEARCH_PAPER|OTHER",
  "is_significant": true,
  "significance_reason": "One sentence why this matters",
  "urgency": "HIGH|MEDIUM|LOW",
  "emoji": "🆕"
}
```

### Signal Types

| Type | Emoji | Urgency | Meaning |
|------|-------|---------|---------|
| SUPPLY_CHAIN | ⚠️ | HIGH | Disruptions, shortages, logistics |
| PRICING_CHANGE | 💲 | HIGH | Rate changes, contract negotiations |
| REGULATORY | ⚖️ | HIGH | Compliance, sanctions, export controls |
| ACQUISITION | 🤝 | MEDIUM | M&A, vendor consolidation |
| EARNINGS | 📊 | MEDIUM | Financial results |
| LAYOFFS_HIRING | 👥 | MEDIUM | Workforce / capacity signals |
| FUNDING | 💰 | LOW | Investment rounds |
| PRODUCT_RELEASE | 🆕 | LOW | New products, feature launches |
| PARTNERSHIP | 🔗 | LOW | Strategic alliances |
| RESEARCH_PAPER | 🔬 | LOW | Academic publications |
| OTHER | 📰 | NEUTRAL | General news |

### Company Profile

```json
{
  "slug": "nvidia",
  "name": "NVIDIA",
  "category": "semiconductors",
  "tier": 1,
  "total_signals": 47,
  "significant_signals": 12,
  "recent_signals": [...],
  "signal_type_counts": {"PRODUCT_RELEASE": 8, "EARNINGS": 5},
  "urgency_counts": {"HIGH": 3, "MEDIUM": 5, "LOW": 4},
  "risk_flags": [{"title": "...", "published": "...", "reason": "..."}]
}
```

---

## Storage — Upstash Redis + Vector

### Redis key structure

| Key | Content | TTL |
|-----|---------|-----|
| `hermes:seen:{md5}` | Dedup flag | 30 days |
| `hermes:item:{md5}` | Full signal JSON | 7 days |
| `hermes:supplier:{slug}` | List of item IDs | 7 days |
| `hermes:profile:{slug}` | Company profile JSON | Permanent |
| `hermes:meta:item_count` | Total count | Permanent |
| `hermes:index:significant` | Sorted set of significant IDs | Permanent |
| `hermes:clusters:{date}` | Macro clusters JSON | 6 hours |
| `hermes:digest:weekly:{iso_week}` | Weekly digest JSON | 30 days |
| `hermes:watchlist` | Set of watched slugs | Permanent |

### Upstash Vector

- **Model:** BAAI/bge-large-en-v1.5 (1024 dimensions, cosine similarity)
- **What's embedded:** `"{supplier} ({category}): {title}. {significance_reason}"`
- **Metadata stored:** supplier, category, published, is_significant, urgency
- **Used by:** `/search?q=...` — semantic search without knowing company name
- **Free tier:** 10,000 vectors total

### Write pattern (atomic)

Every signal is written as:
1. Redis `HSET`, `LPUSH`, `INCR`, `ZADD` (always happens)
2. Vector upsert (non-blocking — failure logged, never drops Redis write)
3. Profile update (non-blocking)

---

## Crawlers & schedule

| Crawler | Schedule | Coverage | Cost |
|---------|----------|----------|------|
| RSS | Every 6h (0,6,12,18) | ~590 companies + 18 industry feeds | Free |
| Watchlist RSS | Every 2h (odd hours) | User watchlist only | Free |
| EDGAR | Daily 07:30 Berlin | Tier 1+2 US-listed (~177 companies) | Free |
| Tavily | Weekly Monday 09:00 | Tier 1+2 (~177 companies) | ~700 req/month |
| Jobs | Weekly Wednesday 09:00 | Tier 1+2 | ~350 req/month |
| Transcripts | Weekly Thursday 08:00 | Tier 1+2 earnings calls via EDGAR | Free |
| Weekly digest | Sunday 18:00 Berlin | All significant signals | Claude Sonnet API cost |

### Processing pipeline

```
Raw articles (RSS/EDGAR/Tavily/Jobs/Transcripts)
    ↓
signal_detector.py — Claude Haiku classification
    ↓
store.store_items() — Redis + Vector write
    ↓
profile update — per-company knowledge base
```

---

## Intelligence layer

### Signal detection (Claude Haiku)
- File: `processors/signal_detector.py`
- Classifies each item into signal_type + urgency + is_significant
- Cost: ~$0.005 per 100 signals

### Macro clustering (Claude Sonnet)
- File: `intelligence/clusters.py`
- Triggered by `GET /clusters`
- Input: top 80 recent significant signals
- Output: themed clusters with synthesis
- Cache: 6 hours

### Weekly digest (Claude Sonnet)
- File: `intelligence/digest.py`
- Triggered: Sunday 18:00 or `GET /digest?refresh=true`
- Input: top 150 signals grouped by category
- Output: overall summary + per-category synthesis

### Trend delta
- File: `intelligence/trends.py`
- Compares this week's clusters to last week's
- Output: new themes, continuing, resolved

---

## Supplier coverage

**~590 companies across 17 categories**

**Tier system:**
- **Tier 1** — Industry leaders (NVIDIA, TSMC, ASML, Intel...) — daily EDGAR + weekly Tavily
- **Tier 2** — Important players (~150) — daily EDGAR + weekly Tavily
- **Tier 3** — Extended ecosystem (~250) — RSS only

**Plus 18 industry RSS feeds:** Supply Chain Dive, Semiconductor Engineering, IEEE Spectrum, TechCrunch, MIT Tech Review, The Register, Wired, Ars Technica, etc.

---

## How Icarus (Telegram) uses Hermes

File: `bot/skills/hermes.py`

Tools exposed to Telegram:
- `hermes_query` — "What's happening with SAP?" → `/query/SAP`
- `hermes_search` — "Any chip shortage news?" → `/search?q=chip+shortage`
- `hermes_briefing` — Top signals summary → `/briefing`
- `hermes_crawl` — Trigger a fresh crawl → `/crawl/rss`
- `hermes_digest` — Weekly digest → `/digest`
- `hermes_watch` — Add company to watchlist → `/watchlist/{company}`
- `hermes_delta` — Trend comparison → `/trends/delta`
- `hermes_enrich` — Enrich company profile → `/enrich/{company}`
- `hermes_trends` — Macro clusters → `/clusters`
- `hermes_profile` — Company profile → `/profile/{company}`
- `hermes_greet` — System status → `/greet`

Auth pattern:
```python
headers = {"x-api-key": os.environ["HERMES_API_KEY"]}
r = requests.get(f"{HERMES_URL}/briefing", headers=headers, timeout=30)
```

---

## How SpendLens uses Hermes (current + planned)

### Currently working
- `modules/hermes_client.py` reads signals from shared Upstash Redis directly
- `get_procurement_briefing(limit)` — top signals mapped to SpendLens categories
- `to_icarus_signals()` — converts Hermes format to SpendLens internal format

### Planned (not built yet)
- Upload → extract top vendors → `POST /watchlist/{vendor}` — Hermes starts watching your suppliers
- Vendor detail view → `GET /query/{vendor}` — show market signals next to spend data
- Replace SpendLens internal RSS crawler (`icarus.py`) with `GET /briefing` from real Hermes

---

## Environment variables

### On Railway (hermes crawler agent)
```
ANTHROPIC_API_KEY               Claude Haiku + Sonnet
TAVILY_API_KEY                  Tavily search API
UPSTASH_REDIS_REST_URL          Redis instance URL
UPSTASH_REDIS_REST_TOKEN        Redis API token
UPSTASH_VECTOR_REST_URL         Vector index URL
UPSTASH_VECTOR_REST_TOKEN       Vector API token
HERMES_API_KEY                  Shared secret (must match consumers)
```

### On consumers (Icarus bot, SpendLens)
```
HERMES_URL=https://hermes-agent-production-114e.up.railway.app
HERMES_API_KEY=<same value as above>
```

---

## Tech stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.13 |
| API server | FastAPI + Uvicorn |
| Scheduler | APScheduler |
| RSS parsing | feedparser |
| HTTP client | httpx |
| News search | Tavily Python SDK |
| LLM | Anthropic SDK (Haiku for signals, Sonnet for clusters/digest) |
| Redis | upstash-redis |
| Vector DB | upstash-vector |
| Charts | QuickChart.io (no API key needed) |
| Deployment | Railway (auto-deploy on git push) |

---

## Project structure

```
hermes-agent/
├── main.py                     # FastAPI app + APScheduler
├── config/
│   └── suppliers.py            # ~590 companies + 18 industry feeds
├── crawlers/
│   ├── rss_crawler.py
│   ├── edgar_crawler.py
│   ├── tavily_crawler.py
│   ├── jobs_crawler.py
│   └── transcripts_crawler.py
├── processors/
│   └── signal_detector.py      # Claude Haiku classification
├── intelligence/
│   ├── clusters.py             # Claude Sonnet macro clustering
│   ├── digest.py               # Weekly digest generation
│   ├── enrichment.py           # Company profile enrichment
│   └── trends.py               # Trend delta analysis
├── storage/
│   └── redis_store.py          # Redis + Vector store
└── charts/
    └── quickchart.py           # QuickChart PNG generation
```

---

## Key architectural decisions

1. **Icarus is master** — Hermes never pushes or initiates
2. **Two databases, one write** — Redis + Vector updated atomically per signal
3. **Vector upsert is non-blocking** — failure never drops Redis write
4. **No startup crawls** — prevents Railway redeploy race conditions
5. **8s HTTP timeout + 512KB cap per feed** — prevents slow feeds blocking the cycle
6. **`/query` vs `/search`** — exact company name → Redis; topic/theme → Vector RAG
7. **Weekly Tavily only** — keeps usage under 1,000/month free tier
8. **Profiles are permanent** — no TTL, grow over time
9. **Clusters cached 6h** — reduces Claude API cost
10. **Watchlist high-frequency** — every 2 hours for critical companies
