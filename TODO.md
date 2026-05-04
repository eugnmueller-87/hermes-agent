# Hermes Agent — TODO

Work through these in order. One step at a time.

---

## Phase 1 — Deploy & Stabilize

- [ ] **1. Remove Telegram notifier from Hermes**
  - Delete `notifier/telegram_notifier.py`
  - Remove notifier import + calls from `main.py` (Fix A in `hermes_explorer.ipynb` Section 9)
  - Remove `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from `.env.example` (Fix B in notebook)
  - Hermes is pull-only — Icarus is master

- [ ] **2. Create `hermes-agent` GitHub repository**
  - `.gitignore` is ready ✅
  - Create new repo at github.com/eugnmueller-87/hermes-agent
  - Push current codebase

- [ ] **3. Deploy Hermes to Railway**
  - Add new service in existing Railway project (same as Icarus)
  - Connect to `hermes-agent` GitHub repo
  - Railway auto-detects `railway.toml` and runs `python main.py`

- [ ] **4. Set environment variables on Railway**
  ```
  ANTHROPIC_API_KEY
  TAVILY_API_KEY
  UPSTASH_REDIS_REST_URL
  UPSTASH_REDIS_REST_TOKEN
  ```

- [ ] **5. Test all crawlers**
  - Check Railway logs — confirm RSS, Tavily, EDGAR run without errors
  - Check Upstash Redis console — confirm `hermes:*` keys are being written
  - Spot-check 3–5 companies manually

---

## Phase 2 — Icarus Integration

- [ ] **6. Add Hermes query handler to Icarus**
  - Add Redis read functions for `hermes:supplier:{slug}` and `hermes:item:*`
  - Add intent detection in Icarus for Hermes-related questions
  - Format Hermes data cleanly before sending to Telegram

- [ ] **7. Implement Icarus Telegram commands**
  - `"What does Hermes have on [company]?"` → supplier items
  - `"Any AI signals today?"` → filtered by category + date
  - `"What's moving in [category]?"` → category digest
  - `"Give me a Hermes briefing"` → top 5 significant signals

- [ ] **8. Test end-to-end from Telegram**
  - Ask Icarus about a Tier 1 company (NVIDIA, OpenAI, etc.)
  - Verify response is clean and sourced from Hermes data
  - Verify no personal data leaks into Hermes queries

---

## Phase 3 — Knowledge Layer

- [ ] **9. Design company profile schema**
  - Fields: name, category, last_funding, key_products, pricing_notes, risk_flags, recent_signals[]
  - Store at `hermes:profile:{slug}`

- [ ] **10. Build profile updater**
  - After each crawl cycle, update relevant company profiles
  - Procurement focus: pricing, supply chain, distributors
  - AI focus: model releases, benchmarks, funding

- [ ] **11. Add profile query to Icarus**
  - `"What do we know about Cerebras?"` → full company profile
  - `"Supplier brief on Arrow Electronics"` → procurement-focused profile

---

## Phase 4 — Miro Agent

- [ ] **12. Set up Miro API access**
  - Create/confirm Miro account
  - Generate REST API token at miro.com/app/settings/user-profile/apps
  - Test API connection

- [ ] **13. Build `miro-agent` service**
  - New Python project, new Railway service
  - Board creation: competitive landscapes, risk boards, presentations
  - Pulls data from Hermes Redis namespace only

- [ ] **14. Connect Miro Agent to Icarus**
  - Icarus Telegram commands trigger Miro board creation
  - Board URL returned to Icarus → sent to you via Telegram
  - `"Build a board for chip suppliers"` → link in 60 seconds

- [ ] **15. Wire Hermes → Miro**
  - Miro Agent reads `hermes:*` keys to populate boards with live data
  - Auto-layout: group by category, color by signal urgency

---

## Phase 5 — Autonomous Intelligence

- [ ] **16. Enrich Icarus morning briefing with Hermes**
  - Icarus (not Hermes) pulls top signals at 06:00 and includes in briefing
  - User-configurable: categories to include, max items

- [ ] **17. Weekly Hermes digest**
  - Icarus generates a weekly summary from Hermes data every Monday
  - Top signals per category, biggest movers

- [ ] **18. SpendLens integration**
  - Hermes feeds procurement signals into SpendLens analysis
  - Supplier risk flags surface in SpendLens dashboard

- [ ] **19. Supplier watchlist**
  - User can add companies to a high-frequency watchlist via Telegram
  - Icarus stores watchlist, Hermes checks those companies every hour

---

## IronHack

- [ ] **20. Define Week 3 Project scope**
- [ ] **21. Build and submit Week 3 Project**

---

## Done ✅

- [x] Codebase built: RSS, Tavily, EDGAR crawlers + signal detector + Redis store
- [x] ~250 suppliers across 17+ categories configured
- [x] `.gitignore` created
- [x] `.env` created and filled with all 4 keys
- [x] `python-dotenv` added to `requirements.txt`
- [x] Virtual environment set up, all dependencies installed
- [x] Redis connection verified (Upstash responding, keys namespace clean)
- [x] `hermes_explorer.ipynb` created — interactive notebook for all crawlers, Redis inspection, and Phase 1 fixes
