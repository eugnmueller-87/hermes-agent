# Hermes Agent — Roadmap

## Vision

Hermes is Icarus's external intelligence layer. While Icarus manages your personal world (calendar, email, tasks), Hermes watches the external world — tech suppliers, AI companies, markets, research — and makes that intelligence available on demand. Together they form a complete personal operations system: one facing inward, one facing outward.

---

## Phase 1 — Deploy & Stabilize (Current)

Get Hermes running reliably in production.

- [ ] Remove Telegram notifier (Hermes is pull-only, Icarus is master)
- [ ] Create `hermes-agent` GitHub repository
- [ ] Deploy to Railway as a new service alongside Icarus
- [ ] Set environment variables on Railway
- [ ] Verify RSS, Tavily, and EDGAR crawlers run on schedule
- [ ] Confirm Redis keys are written correctly in `hermes:*` namespace

**Progress:** Environment ready — `.env` filled, venv set up, all dependencies installed, Redis connection verified. Next: apply Telegram notifier removal, then push to GitHub and deploy to Railway.

**Success criteria:** Hermes runs 24/7, collects intel, stores in Redis. No crashes, no overlap with Icarus personal data.

---

## Phase 2 — Icarus Integration (On-Demand Queries)

Icarus learns to pull from Hermes when you ask.

- [ ] Add Telegram command handler in Icarus for Hermes queries
- [ ] `"What does Hermes have on [company]?"` → pulls `hermes:supplier:{slug}`
- [ ] `"Any AI signals today?"` → filters items by category + date
- [ ] `"What's moving in semiconductors?"` → category-level digest
- [ ] `"Give me a Hermes briefing"` → top 5 significant signals of the day
- [ ] Icarus formats Hermes data cleanly before showing it (no raw JSON)

**Success criteria:** You can ask Icarus about any tracked company or category from Telegram and get a clean, formatted answer sourced from Hermes data.

---

## Phase 3 — Knowledge Layer (Procurement + AI Skillset)

Hermes builds structured, growing knowledge about each company — not just news items but a living profile.

- [ ] Design company profile schema (funding history, key products, pricing, risk flags, recent signals)
- [ ] Populate profiles incrementally as crawlers find new data
- [ ] Separate procurement intelligence (pricing, supply chain, distributors) from AI intelligence (models, benchmarks, funding)
- [ ] Store profiles at `hermes:profile:{slug}` in Redis
- [ ] Icarus can ask "what do we know about Cerebras?" and get a full profile, not just recent news

**Success criteria:** Each tracked company has a growing knowledge profile. Icarus can give you a supplier brief without needing to search the web.

---

## Phase 4 — Miro Agent

A separate agent that turns data into visual boards and presentations.

- [ ] Set up Miro API access (account + REST API token)
- [ ] Build `miro-agent` service (Python, Railway)
- [ ] Board types:
  - Competitive landscape maps (category view of suppliers)
  - Supplier risk boards (flagged items visualized)
  - AI startup radar (funding + momentum map)
  - Project planning boards (SpendLens, Icarus roadmap)
  - Client presentations (Miro presentation mode)
- [ ] Icarus Telegram commands:
  - `"Build a board for chip suppliers"` → Miro competitive landscape
  - `"Create a presentation on AI infrastructure"` → Miro presentation
  - `"Map today's Hermes signals"` → visual signal board
- [ ] Miro Agent pulls from Hermes data, does not access personal Icarus data

**Success criteria:** You can trigger a Miro board from Telegram in under 60 seconds, populated with real data from Hermes.

---

## Phase 5 — Autonomous Intelligence

Hermes and the Miro Agent operate with minimal input, surfacing what matters without being asked.

- [ ] Icarus morning briefing enriched with top Hermes signals (opt-in, not automatic push from Hermes)
- [ ] Weekly Hermes digest — auto-generated summary of the week's most significant signals per category
- [ ] Auto-generate Miro board on major events (large funding round, major acquisition) — triggered by Icarus
- [ ] SpendLens integration — Hermes feeds procurement signals directly into SpendLens analysis
- [ ] Supplier watchlist — track specific companies with higher frequency on demand

**Success criteria:** The system surfaces the right intelligence at the right time with minimal prompting. Icarus remains the decision layer throughout.

---

## Architecture Principles (Preserved Across All Phases)

1. **Icarus is master** — Hermes never pushes, never accesses personal data, never sends Telegram messages
2. **Shared Redis, separate namespaces** — `hermes:*` is Hermes territory, everything else is Icarus
3. **Pull on demand** — Icarus fetches Hermes data when you ask, not on a push schedule
4. **Least privilege** — each agent knows only what it needs to do its job
5. **Railway as single platform** — Icarus, Hermes, Miro Agent all run as separate Railway services in one project
