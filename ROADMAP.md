# Hermes Agent — Roadmap

## Vision

Hermes is Icarus's external intelligence layer. While Icarus manages your personal world (calendar, email, tasks), Hermes watches the external world — tech suppliers, AI companies, semiconductor markets, SEC filings, industry news — and makes that intelligence available on demand via natural language. Together they form a complete personal operations system: one facing inward, one facing outward.

---

## Phase 1 — Deploy & Stabilize ✅ COMPLETE

- [x] RSS, Tavily, and EDGAR crawlers running on schedule
- [x] Claude Haiku signal detection (11 signal types, HIGH/MEDIUM/LOW urgency)
- [x] Upstash Redis storage (`hermes:*` namespace, dedup, 7-day TTL)
- [x] Railway deployment, APScheduler, environment variables

**Status:** Live. RSS every 6h, EDGAR daily 07:30, Tavily weekly Monday 09:00.

---

## Phase 1b — SpendLens Integration ✅ COMPLETE

- [x] `HermesClient` standalone connector with fuzzy vendor name matching
- [x] `get_procurement_briefing()`, `enrich_vendor_list()`, `to_icarus_signals()`
- [x] SpendLens pulls Hermes signals automatically on every analysis cycle

---

## Phase 1c — QuickChart Integration ✅ COMPLETE

- [x] `charts/quickchart.py` — QuickChart REST API wrapper (no API key required)
- [x] `GET /chart/signals` — bar chart of significant signals by urgency (HIGH/MEDIUM/LOW)
- [x] `GET /chart/landscape` — horizontal bar chart of item counts by category (top 10)
- [x] Returns a PNG image URL Icarus can send directly as a Telegram photo (inline, no link click)
- [x] Full error logging — entry, item counts, data breakdown, success URL, specific error types

---

## Phase 2 — Icarus Integration ✅ COMPLETE

- [x] `hermes_greet` — live stats from Hermes
- [x] `hermes_query` — company-specific signal lookup with fuzzy matching
- [x] `hermes_briefing` — top significant signals across all suppliers
- [x] `hermes_crawl` — trigger RSS/EDGAR/Tavily crawl on demand from Telegram
- [x] `GET /query/{company}`, `GET /briefing`, `GET /greet`, `POST /crawl/*` endpoints
- [x] `GET /health`, `POST /flush` operational endpoints
- [x] Icarus system prompt updated with Hermes tool usage rules and fallback behaviour

---

## Phase 2b — RAG Semantic Search ✅ COMPLETE

- [x] Upstash Vector index (`hermes_crawler_agent`, BAAI/bge-large-en-v1.5, 1024-dim, cosine)
- [x] Every stored item is simultaneously embedded into the vector index (supplier + title + significance_reason)
- [x] `GET /search?q=` endpoint — natural language topic queries across all suppliers
- [x] `hermes_search` tool in Icarus — routes topic/theme questions to semantic search
- [x] System prompt rule: `hermes_query` for named companies, `hermes_search` for topics/themes
- [x] 18 industry RSS feeds added (Supply Chain Dive, Semiconductor Engineering, EE Times, Ars Technica, TechCrunch, MIT Tech Review, etc.) — free, unlimited

**What this unlocks:** "What are chip suppliers signaling about export controls?" returns relevant items from ASML, NVIDIA, Applied Materials, KLA — without the user naming any of them.

---

## Phase 2c — Conversational Context ✅ COMPLETE

- [x] Icarus system prompt updated: Claude explicitly instructed to resolve pronouns and carry company/topic context into Hermes tool inputs
- [x] "what about their competitors?" after asking about NVIDIA → Claude resolves before calling tool
- [x] `hermes_profile` and `hermes_trends` added to system prompt routing rules

---

## Phase 3 — Knowledge Layer ✅ COMPLETE

- [x] Company profile schema: name, category, tier, signal counts, urgency breakdown, risk flags, recent history (last 10), first/last seen
- [x] `_update_profile()` called inside `store_item()` — every new signal enriches the profile atomically
- [x] Stored at `hermes:profile:{slug}` in Redis — permanent, no TTL
- [x] `GET /profile/{company}` endpoint — fuzzy match, returns full profile JSON
- [x] `hermes_profile` tool in Icarus — "what do we know about Cerebras?" → full profile, not just recent news
- [x] Profile update failure is caught and logged — never blocks signal storage

**What this unlocks:** Hermes builds a living dossier on every tracked company. Ask once, get everything accumulated — not just what arrived in the last 7 days.

---

## Phase 3b — Cross-Signal Intelligence ✅ COMPLETE

- [x] `intelligence/clusters.py` — scans recent significant signals, sends to Claude Sonnet, returns macro theme clusters
- [x] Each cluster: theme label + 1-paragraph synthesis + companies involved + urgency distribution
- [x] Cached at `hermes:clusters:{date}` — 6h TTL, `?refresh=true` to force rebuild
- [x] `GET /clusters` endpoint
- [x] `hermes_trends` tool in Icarus — "what macro themes are emerging this week?"

**What this unlocks:** "5 chip suppliers flagged export control risk this week — TSMC, ASML, NVIDIA, KLA, Applied Materials." Cross-company patterns invisible to any single query.

---

## Phase 4 — Autonomous Intelligence ✅ PARTIAL

- [x] **Morning briefing enrichment** — top 3 Hermes signals appended to 06:00 Icarus brief; failure silently skipped, never breaks the briefing
- [ ] Weekly Hermes digest — auto-generated summary of the week's most significant signals per category
- [ ] Supplier watchlist — track specific companies with higher crawl frequency on demand
- [ ] SpendLens deeper integration — Hermes supplier profiles feed vendor detail views

---

## Phase 5 — Richer Data Sources ✅ COMPLETE

- [x] **Job postings crawler** (`crawlers/jobs_crawler.py`) — Tavily searches Lever/Greenhouse/Workday for Tier 1+2; runs Wednesday 09:00; hiring spikes are 6-month leading indicators
- [x] **Earnings call transcripts** (`crawlers/transcripts_crawler.py`) — SEC 8-K full-text for earnings filings; runs Thursday 08:00; dense forward-looking language for Haiku to classify
- [x] `POST /crawl/jobs` and `POST /crawl/transcripts` trigger endpoints
- [x] Both feed the same `store_item()` pipeline — no new storage layer

**Crawl schedule now:** RSS @0/6/12/18h · EDGAR daily @07:30 · Tavily Mon @09:00 · Jobs Wed @09:00 · Transcripts Thu @08:00

---

## Phase 6 — Deep Autonomous Intelligence ⬜ NEXT

Build on the intelligence layer to make Hermes proactive and self-improving.

- [ ] Weekly Hermes digest — Claude Sonnet auto-generates a weekly summary per category, sent to Icarus every Sunday evening
- [ ] Supplier watchlist — user can pin companies for higher crawl frequency (RSS every 2h, Tavily twice weekly)
- [ ] Trend memory — compare this week's clusters to last week's; surface what's new vs. continuing
- [ ] Profile enrichment from profiles — Haiku extracts key products, pricing notes, risk flags from accumulated signals and writes them back to the profile
- [ ] SpendLens deeper integration — Hermes supplier profiles feed vendor detail views in SpendLens

---

## Visualisation Backlog (parked — revisit when core NL intelligence is mature)

Current focus is natural language market intelligence — Hermes answers questions, Icarus relays them. Charts are a nice-to-have, not the core value.

- [ ] **Matplotlib graphic engine** — replace QuickChart with native PNG generation on Hermes; full control over styling; returns image bytes directly; no external dependency. Requires: `matplotlib` on Railway, byte handling in Icarus, base64 rendering in PWA frontend.
- [ ] **CI/CD for Hostinger VPS** — GitHub Action (SSH + git pull + systemctl restart) so PWA deploys automatically on push. Prerequisite for any PWA-side visual work.
- [ ] **Miro integration (optional)** — whiteboard-style landscape and signal boards via `POST /miro/*`; requires `MIRO_API_TOKEN`; useful if a shareable visual board is needed beyond inline charts.
- [ ] **Bricks / BI dashboard (optional)** — manual export of Hermes data to CSV → Bricks dashboard; useful for demos or stakeholder reporting outside Telegram.

---

## Architecture Principles

1. **Icarus is master** — Hermes never pushes, never accesses personal data, never sends messages
2. **Two databases, one store_item() call** — Redis (exact lookup) + Vector (semantic search) updated simultaneously; profile update is a third write in the same call
3. **Pull on demand** — Icarus fetches when asked, not on a push schedule
4. **Least privilege** — each agent knows only what it needs
5. **Railway as single platform** — Icarus and Hermes as separate services in one project
6. **Free tier discipline** — Tavily capped weekly (~700/month), Vector index 10K vectors, Redis 10K commands/day
7. **Isolation on every new feature** — failures are caught and logged, never cascade into existing functionality
