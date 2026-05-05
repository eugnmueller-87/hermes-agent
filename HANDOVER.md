# Hermes Agent — Handover Document

**Last updated:** 2026-05-05 (QuickChart integration)

## What is Hermes?

Hermes is a market intelligence crawler and sub-agent of **Icarus AI** (personal Telegram bot). He crawls the external world, classifies what he finds with Claude Haiku, stores everything in two databases, and answers natural language questions — including semantic topic search powered by RAG.

Hermes never pushes, never alerts, never accesses personal data. He waits to be asked.

---

## Core Architecture

```
You (Telegram)
     │
     ▼
 ICARUS AI  ──── HTTP API ──→  HERMES AGENT
 (master bot)                  (sub-agent)
     │                              │
     │                         Crawlers:
     │                         RSS · EDGAR · Tavily
     │                         + 18 industry feeds
     │                              │
     │                         Claude Haiku
     │                         (signal classification)
     │                              │
     │                    ┌─────────┴──────────┐
     │                    ▼                    ▼
     │              Upstash Redis       Upstash Vector
     │              (exact lookup)      (semantic RAG)
     │                    │                    │
     └──── pulls ─────────┴────────────────────┘
```

---

## Current Status

| Component | Status |
|---|---|
| Railway deployment | **Live** — 24/7 |
| RSS crawler + 18 industry feeds | **Active** — every 6h |
| EDGAR crawler | **Active** — daily 07:30 |
| Tavily crawler | **Active** — weekly Monday 09:00 |
| Upstash Redis | **Live** — items, supplier lists, dedup |
| Upstash Vector | **Live** — BAAI/bge-large-en-v1.5, 1024-dim, semantic search |
| FastAPI HTTP server | **Live** — 7 endpoints |
| QuickChart Agent | **Live** — inline chart images for Telegram |
| Icarus integration | **Live** — 5 Hermes tools in Telegram bot |
| RAG semantic search | **Live** — `/search?q=` + `hermes_search` tool |
| GitHub repo | `eugnmueller-87/hermes-agent` |

---

## HTTP API

All POST endpoints require `x-api-key: {HERMES_API_KEY}` header. GET query endpoints also require it.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Supplier count + status |
| GET | `/greet` | Live stats message for Icarus |
| GET | `/query/{company}` | Company-specific signal lookup (fuzzy match) |
| GET | `/briefing` | Top significant signals across all suppliers |
| GET | `/search?q=` | **RAG** — semantic topic/theme search via vector index |
| POST | `/crawl/rss` | Trigger immediate RSS crawl cycle |
| POST | `/crawl/edgar` | Trigger immediate EDGAR crawl cycle |
| POST | `/crawl/tavily` | Trigger immediate Tavily crawl cycle |
| GET | `/chart/signals` | QuickChart PNG URL — significant signals by urgency |
| GET | `/chart/landscape` | QuickChart PNG URL — item counts by category (top 10) |
| POST | `/flush` | Clear all Redis + vector data (clean start) |

**Base URL:** `https://hermes-agent-production-114e.up.railway.app`

---

## Database Layer

### Upstash Redis — Exact Lookup

```
hermes:seen:{md5}       Dedup flag — TTL 30 days
hermes:item:{md5}       Full item JSON — TTL 7 days
hermes:supplier:{slug}  List of item IDs per supplier — max 3000
```

**Item JSON:**
```json
{
  "id": "md5 hash of URL",
  "supplier": "NVIDIA",
  "title": "...",
  "url": "...",
  "summary": "...",
  "published": "2026-05-05T10:00:00Z",
  "source": "rss | tavily | edgar",
  "signal_type": "PRODUCT_RELEASE",
  "is_significant": true,
  "significance_reason": "...",
  "urgency": "HIGH",
  "emoji": "🆕"
}
```

### Upstash Vector — Semantic Search (RAG)

- **Index:** `hermes_crawler_agent`, Ireland (eu-west-1)
- **Model:** BAAI/bge-large-en-v1.5 (hosted by Upstash — no separate API key)
- **Dimensions:** 1024, Cosine similarity
- **Text embedded:** `"{supplier} ({category}): {title}. {significance_reason}"`
- **Metadata stored:** supplier, category, published, is_significant, urgency
- **Free tier:** 10,000 vectors total

Both databases are written in the same `store_item()` call. Vector upsert failure never drops the Redis write.

---

## Supplier Coverage

~590 companies across 17 categories after deduplication. 3 tiers by priority.

Plus 18 industry RSS feeds (unlimited, free):
- Supply Chain: Supply Chain Dive, Spend Matters, Logistics Management
- Semiconductors: Semiconductor Engineering, EE Times, IEEE Spectrum
- Cloud/DC: Data Center Knowledge, Next Platform, SiliconANGLE
- Broad tech: Ars Technica, TechCrunch, MIT Tech Review, The Verge, Wired, The Register

---

## Icarus Tools

| Tool | When Claude calls it | What it does |
|---|---|---|
| `hermes_greet` | User asks about Hermes or system status | GET /greet → live stats |
| `hermes_query` | Named company: "what does Hermes have on TSMC?" | GET /query/{company} |
| `hermes_briefing` | "briefing", "what's moving today" | GET /briefing |
| `hermes_search` | Topic/theme: "chip export controls", "cloud pricing" | GET /search?q= (RAG) |
| `hermes_crawl` | "run a crawl", "fetch fresh data" | POST /crawl/{rss|edgar|tavily} |
| `hermes_chart` | Chart request, "show me a chart", "visualise signals" | GET /chart/signals or /chart/landscape → send as Telegram photo |

---

## Crawl Schedule

| Crawler | Frequency | Coverage | Free limit |
|---|---|---|---|
| RSS + industry feeds | Every 6h | ~590 companies with feeds + 18 industry sources | Unlimited |
| EDGAR | Daily 07:30 | US-listed Tier 1+2 companies | Unlimited |
| Tavily | Weekly (Mon 09:00) | Tier 1+2 (~177 companies) | 1,000 searches/month |

---

## Environment Variables

**Hermes (Railway):**
```
ANTHROPIC_API_KEY          Claude Haiku for signal detection
TAVILY_API_KEY             News search
UPSTASH_REDIS_REST_URL     Redis instance
UPSTASH_REDIS_REST_TOKEN   Redis instance
UPSTASH_VECTOR_REST_URL    Vector index (https://clever-parrot-92759-eu1-vector.upstash.io)
UPSTASH_VECTOR_REST_TOKEN  Vector index
HERMES_API_KEY             Shared secret for HTTP API auth
```

**Icarus (Railway):**
```
HERMES_URL       https://hermes-agent-production-114e.up.railway.app
HERMES_API_KEY   Same value as Hermes HERMES_API_KEY
```

---

## Visualisation Layer

### QuickChart — Inline Telegram Charts

- **Module:** `charts/quickchart.py`
- **Service:** [quickchart.io](https://quickchart.io) — free, no API key required
- **How it works:** Hermes POSTs a Chart.js 2.x config to `https://quickchart.io/chart/create` and gets back a short PNG URL. Icarus passes that URL to `bot.send_photo()` — chart appears inline in Telegram.
- **Charts available:**
  - `/chart/signals` — bar chart, significant items by urgency (HIGH/MEDIUM/LOW)
  - `/chart/landscape` — horizontal bar chart, item counts by category (top 10)
- **Isolation:** lazy-imported inside each endpoint; QuickChart errors never affect crawlers, storage, or Miro
- **Logging:** entry, item counts, data breakdown, success URL, and specific error types all logged under `hermes.charts`

---

## Key Architectural Decisions

1. **Icarus is master** — Hermes never pushes, never accesses personal namespaces
2. **Two databases, one write call** — Redis + Vector updated atomically in `store_item()`
3. **Vector upsert is non-blocking** — failure logs a warning but never drops the Redis write
4. **No startup crawls** — removed to prevent race conditions on redeploy; scheduler + manual triggers only
5. **8s HTTP timeout + 512KB cap per feed** — prevents one slow/large feed from blocking the entire crawl cycle
6. **hermes_query vs hermes_search** — exact company name → Redis slug lookup; topic/theme → Vector RAG
7. **Weekly Tavily only** — keeps usage under 1,000/month free tier
8. **Miro token stays in Hermes** — Icarus calls the endpoint, never handles Miro credentials directly
