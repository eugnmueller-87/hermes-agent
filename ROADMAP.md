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

## Phase 2c — Conversational Context ⬜ NEXT

Make Hermes tools conversation-aware so follow-up questions work naturally.

- [ ] Update Icarus system prompt: explicitly instruct Claude to carry company/topic context into tool inputs
- [ ] Test: "what's NVIDIA doing?" → "what about their competitors?" → Claude resolves to correct query
- [ ] Test: "any signals about chip shortages?" → "what happened last week?" → Claude scopes correctly

**Isolation:** system prompt change only — no new endpoints, no new tools, zero risk to crawlers or storage.

---

## Phase 3 — Knowledge Layer ⬜ PLANNED

Hermes builds structured, growing knowledge about each company — not just recent news but a living profile.

- [ ] Company profile schema: name, category, tier, key products, risk flags, signal history (last 10), first/last seen
- [ ] `update_profile()` called inside `store_item()` — every new signal enriches the profile atomically
- [ ] Store at `hermes:profile:{slug}` in Redis (no TTL — profiles are permanent)
- [ ] `GET /profile/{company}` endpoint — fuzzy match, returns full profile JSON
- [ ] `hermes_profile` tool in Icarus — "what do we know about Cerebras?" → full profile, not just recent news
- [ ] Profile never blocks signal storage — update_profile() failure logs warning only

**Isolation:** `update_profile()` is additive inside `store_item()`. New endpoint is independent. New Icarus tool is additive. Nothing existing changes.

---

## Phase 3b — Cross-Signal Intelligence ⬜ PLANNED

Surface macro themes by connecting signals across companies — what no single query reveals.

- [ ] `GET /clusters` endpoint — scans recent significant signals, sends to Claude Sonnet, returns theme clusters
- [ ] Each cluster: theme label + 1-paragraph synthesis + list of companies involved + urgency distribution
- [ ] Store at `hermes:clusters:{date}` — regenerated daily or on demand
- [ ] `hermes_trends` tool in Icarus — "what macro themes are emerging this week?"
- [ ] Example output: "5 chip suppliers flagged export control risk this week — TSMC, ASML, NVIDIA, KLA, Applied Materials"

**Isolation:** Entirely new endpoint and tool. No changes to crawlers, storage, or existing endpoints.

---

## Phase 4 — Autonomous Intelligence ⬜ PLANNED

- [ ] **Morning briefing enrichment** — top 3 HIGH-urgency Hermes signals appended to 06:00 Icarus brief
- [ ] Weekly Hermes digest — auto-generated summary of the week's most significant signals per category
- [ ] Supplier watchlist — track specific companies with higher crawl frequency on demand
- [ ] SpendLens deeper integration — Hermes supplier profiles feed vendor detail views

**Morning briefing isolation:** additive call in `morning_briefing()` — failure is caught and silently skipped, never breaks the briefing.

---

## Phase 5 — Richer Data Sources ⬜ PLANNED

Expand signal coverage beyond news and SEC filings.

- [ ] **Job postings crawler** — Tavily searches `"{company} site:lever.co OR site:greenhouse.io"` for Tier 1+2 companies; hiring spikes are 6-month leading indicators
- [ ] **Earnings call transcripts** — target company IR pages + SEC 8-K full-text filings; dense with forward-looking language Haiku can classify
- [ ] Both sources feed the same `store_item()` pipeline — no new storage layer needed
- [ ] Tavily budget: job postings weekly, transcripts triggered by EDGAR earnings detection

**Isolation:** New crawler modules only. Existing RSS/EDGAR/Tavily crawlers untouched. Same signal detection + storage pipeline.

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
2. **Two databases, one store_item() call** — Redis (exact lookup) + Vector (semantic search) updated simultaneously
3. **Pull on demand** — Icarus fetches when asked, not on a push schedule
4. **Least privilege** — each agent knows only what it needs
5. **Railway as single platform** — Icarus and Hermes as separate services in one project
6. **Free tier discipline** — Tavily capped weekly (~700/month), Vector index 10K vectors, Redis 10K commands/day
