# Hermes Agent — Handover Document

**Last updated:** 2026-05-04

## What is Hermes?

Hermes is a market intelligence crawler that serves as a read-only data source for two systems:

- **Icarus AI** — master personal operations agent (Gmail, Calendar, Tasks, Telegram). Icarus queries Hermes on demand when you ask about a company, category, or signal type.
- **SpendLens** — procurement intelligence dashboard. Consumes Hermes signals automatically on every analysis cycle via `HermesClient`.

Hermes never pushes, never alerts, never accesses personal data. He crawls the external world, classifies what he finds, stores it in Redis, and waits to be asked.

---

## Core Architecture

```
Hermes                        Redis (shared)              Icarus
------                        --------------              ------
Crawls external world  →→→   hermes:* namespace   ←←←   Pulls on demand
Stores structured data        (read/write)               Owns personal data
Runs on its own schedule      hermes:item:*              (Gmail, Calendar,
No Telegram                   hermes:seen:*               Tasks, Redis personal
No personal data              hermes:supplier:*           namespace)
                                       ↑
                              SpendLens (read-only)
                              Pulls via HermesClient
                              Injects into Icarus pipeline
```

Icarus is master. Hermes is a data source. SpendLens is a consumer. This separation must be preserved.

---

## Current Status

| Component | Status |
|---|---|
| Railway deployment | **Live** — running 24/7 |
| RSS crawler | **Active** — every 6h |
| EDGAR crawler | **Active** — daily 07:30 |
| Tavily crawler | **Active** — weekly Monday 09:00 |
| SpendLens integration | **Live** — HermesClient wired into icarus.py |
| Miro Agent | **Built** — modules ready, Telegram trigger pending |
| GitHub repo | **Live** — `eugnmueller-87/hermes-agent` |
| Telegram notifier | **Removed** — Hermes is pull-only |

---

## File Structure

```
hermes-agent/
├── main.py                         Entry point + APScheduler
├── railway.toml                    Railway deployment config
├── requirements.txt
├── .env.example
├── HANDOVER.md                     This file
├── ROADMAP.md                      Phased roadmap
├── TODO.md                         Current task list
├── config/
│   └── suppliers.py                ~250 companies, 17 categories, 3 tiers
├── crawlers/
│   ├── rss_crawler.py              RSS feeds — every 6h
│   ├── tavily_crawler.py           Tavily news search — weekly
│   └── edgar_crawler.py            SEC EDGAR filings — daily
├── processors/
│   └── signal_detector.py          Claude Haiku signal classification
├── storage/
│   └── redis_store.py              Upstash Redis interface (dedup + store + query)
├── integrations/
│   └── hermes_client.py            Standalone connector for SpendLens and Icarus
├── miro/
│   ├── client.py                   Miro REST API wrapper
│   └── boards.py                   Signal board + landscape board builders
├── tests/
├── logs/
├── audit_logs/
├── screenshots/
└── hermes_explorer.ipynb           Interactive dev/debug notebook
```

---

## Crawl Schedule

| Crawler | Frequency | Coverage | Cost |
|---|---|---|---|
| RSS | Every 6h | All companies with RSS feeds | Free |
| EDGAR | Daily 07:30 | Tier 1+2 US-listed companies | Free |
| Tavily | Weekly (Mon 09:00) | Tier 1+2 (~177 companies) | Free tier |

**Tavily budget:** ~700 searches/month used, ~300 held in reserve for on-demand Icarus queries.
**Total cost:** ~$6/month (Railway hosting only — all APIs on free tiers).

---

## Redis Key Schema

```
hermes:seen:{md5_hash}       Dedup flag — TTL 30 days
hermes:item:{md5_hash}       Full item JSON — TTL 7 days
hermes:supplier:{slug}       List of item IDs per supplier — max 50
```

### Item JSON Shape

```json
{
  "id": "md5 hash of URL",
  "supplier": "NVIDIA",
  "title": "NVIDIA announces H200 NVL cluster",
  "url": "https://...",
  "summary": "...",
  "published": "2026-05-04T10:00:00Z",
  "source": "rss | tavily | edgar",
  "signal_type": "PRODUCT_RELEASE",
  "is_significant": true,
  "significance_reason": "Major new hardware affecting AI infrastructure supply.",
  "urgency": "HIGH",
  "emoji": "🆕"
}
```

---

## Signal Types

| Signal | Procurement-relevant? | Default impact |
|---|---|---|
| SUPPLY_CHAIN | Yes | negative |
| PRICING_CHANGE | Yes | negative |
| EARNINGS | Yes | neutral |
| REGULATORY | Yes | negative |
| ACQUISITION | Yes | neutral |
| LAYOFFS_HIRING | Yes | neutral |
| FUNDING | No | positive |
| PRODUCT_RELEASE | No | positive |
| PARTNERSHIP | No | positive |
| RESEARCH_PAPER | No | positive |
| OTHER | No | neutral |

---

## SpendLens Integration

SpendLens lives at `C:\Users\eugnm\OneDrive\Desktop\PROCUREMENT\PROCUREMENT\SpendLens_App`.

Two files were added/modified:

**`modules/hermes_client.py`** (new file — copy of `integrations/hermes_client.py` with SpendLens-specific converter):
- `get_signals(vendor, limit, procurement_only)` — fetch items for one supplier
- `get_risk_flags(vendor)` — significant HIGH/MEDIUM items only
- `get_procurement_briefing(limit)` — top procurement signals across all suppliers
- `enrich_vendor_list(vendor_names)` — bulk risk scoring with fuzzy name matching
- `to_icarus_signals(items)` — converts Hermes items to Icarus signal format (category + relevance + impact)

**`icarus.py`** (modified in 3 places):
1. `_get_hermes_signals()` function after `load_dotenv()` — fetches briefing, converts, returns list
2. In `run()`: `signals = hermes_signals + signals` — prepends Hermes signals before dedup
3. In `query_with_claude()`: Hermes context block added to Claude prompt

**SpendLens `.env`** — `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` added (same values as Hermes).

Integration is fail-safe: if Redis is unreachable or Hermes is down, `_get_hermes_signals()` returns `[]` and SpendLens continues normally.

---

## Miro Agent

Modules are in `miro/`. Requires `MIRO_ACCESS_TOKEN` in `.env`.

- `client.py` — REST wrapper for boards, frames, sticky notes, cards
- `boards.py`:
  - `build_signal_board(store)` — items grouped by signal type into frames, urgency-coloured stickies
  - `build_landscape_board(store, category_filter)` — suppliers as cards grouped by category, tier-coloured

Both return a shareable Miro URL. Phase 4 wires this to Icarus Telegram commands.

---

## Environment Variables

```
ANTHROPIC_API_KEY         Claude Haiku for signal detection
TAVILY_API_KEY            News search
UPSTASH_REDIS_REST_URL    Shared Redis instance (Icarus + Hermes + SpendLens)
UPSTASH_REDIS_REST_TOKEN  Shared Redis instance
MIRO_ACCESS_TOKEN         Miro REST API (optional — Miro Agent only)
```

No Telegram variables. Hermes does not send messages.

---

## Key Decisions

1. **Icarus is master** — Hermes never pushes data, never accesses personal namespaces
2. **Shared Redis, strict namespace** — `hermes:*` only; Icarus and SpendLens read-only consumers
3. **SpendLens integration is fail-safe** — optional import, try/except, returns empty list on failure
4. **Weekly Tavily only** — keeps usage under 1,000/month free tier; daily was ~$19/month
5. **Claude Haiku for classification** — fast, cheap, good enough for high-volume signal tagging
6. **Fuzzy vendor matching** — `difflib.get_close_matches(cutoff=0.6)` bridges SpendLens vendor names to Hermes slugs
7. **Miro over Excalidraw** — Miro has a full server-side REST API; Excalidraw is client-only

---

## What Is Next

| Phase | Description | Status |
|---|---|---|
| Phase 2 | Add Hermes query commands to Icarus Telegram | Pending |
| Phase 3 | Knowledge layer — structured company profiles at `hermes:profile:{slug}` | Pending |
| Phase 4 | Wire Miro boards to Icarus Telegram (trigger from chat, return URL) | Pending |
| Phase 5 | Morning briefing enrichment, weekly digest, supplier watchlist | Pending |

**Immediate next step:** Wait for Hermes to accumulate Redis data over the first week, then run a SpendLens analysis and verify Hermes signals appear in the output.
