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

## Phase 1c — Miro Agent ✅ COMPLETE

- [x] `miro/client.py` — Miro REST API wrapper
- [x] `miro/boards.py` — signal board + landscape board builders
- [x] `POST /miro/landscape` and `POST /miro/signals` HTTP endpoints
- [x] Triggered from Telegram via Icarus `build_miro_board` tool

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

## Phase 3 — Knowledge Layer

Hermes builds structured, growing knowledge about each company — not just news items but a living profile.

- [ ] Company profile schema (funding history, key products, pricing notes, risk flags, recent signals)
- [ ] Populate profiles incrementally as crawlers find new data
- [ ] Store profiles at `hermes:profile:{slug}` in Redis
- [ ] Icarus can ask "what do we know about Cerebras?" and get a full profile, not just recent news
- [ ] Separate procurement intelligence from AI intelligence per company

---

## Phase 4 — Autonomous Intelligence

- [ ] Icarus morning briefing enriched with top Hermes signals (opt-in, pulled at 06:00)
- [ ] Weekly Hermes digest — auto-generated summary of the week's most significant signals per category
- [ ] Auto-generate Miro board on major events (large funding round, acquisition)
- [ ] Supplier watchlist — track specific companies with higher crawl frequency on demand
- [ ] SpendLens deeper integration — Hermes supplier profiles feed vendor detail views

---

## Architecture Principles

1. **Icarus is master** — Hermes never pushes, never accesses personal data, never sends messages
2. **Two databases, one store_item() call** — Redis (exact lookup) + Vector (semantic search) updated simultaneously
3. **Pull on demand** — Icarus fetches when asked, not on a push schedule
4. **Least privilege** — each agent knows only what it needs
5. **Railway as single platform** — Icarus and Hermes as separate services in one project
6. **Free tier discipline** — Tavily capped weekly (~700/month), Vector index 10K vectors, Redis 10K commands/day
