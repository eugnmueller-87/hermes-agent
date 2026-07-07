# Hermes Agent — TL;DR

> **⚠️ Current state (2026-07-07):** this doc describes an earlier, larger vision. What's actually
> live: **~56 suppliers / 8 categories** (not 250/590), **procurement** supplier-intelligence (not
> trading), **manual-trigger** crawls via the `/crawl/*` endpoints (there is **no 24/7 scheduler** —
> `lifespan` logs "no scheduled crawls"). Auth is fail-closed. LinkedIn-draft generation is not part
> of the live service. See README's current-state note + `config/suppliers.py` for the code truth.

**What it was designed as:** A market-intelligence and content system. It watches AI/tech suppliers, classifies every signal with Claude Haiku, and surfaces the most relevant ones — grounded in live market data. *(Coverage/scheduler/LinkedIn claims below are aspirational — see the banner.)*

**Why it exists:** Tracking supplier news, SEC filings, and AI company moves used to take hours per week. Writing content about those moves took more time on top. Hermes automates both: the monitoring and the first draft.

**How it works:** Two layers working together.

- **Intelligence layer** — Three crawlers pull data continuously. Claude Haiku classifies every item into one of 11 signal types with urgency scoring (HIGH / MEDIUM / LOW) and a significance flag. Everything lands in Upstash Redis under `hermes:*`.
- **Content layer** — A six-step pipeline (document → monitor → brief → draft → publish → iterate) pulls significant signals from Redis, combines them with a structured knowledge base, and generates LinkedIn drafts via Claude Sonnet. Drafts are staged in Telegram for one-tap approval via Icarus.

---

| | |
|---|---|
| **Coverage** | ~250 companies · 17 categories · 3 tiers |
| **Crawlers** | RSS every 6h · EDGAR daily · Tavily weekly |
| **Signal types** | 11 (FUNDING, SUPPLY_CHAIN, PRICING_CHANGE, EARNINGS, ...) |
| **Knowledge base** | Primary KB (brand voice, background, examples) + Secondary KB (Hermes signals, supplier landscape) |
| **Prompt templates** | 5 (linkedin_post, market_brief, signal_analysis, content_calendar, uniqueness_comparison) |
| **Storage** | Upstash Redis · 7-day TTL · dedup · `hermes:*` namespace |
| **Deployment** | Railway · 24/7 · auto-deploys on push |
| **Cost** | ~$7–8/month total |

---

**Who reads it:**

- **Content pipeline** — `src/main.py` pulls signals, loads KB, drafts posts via Claude Sonnet
- **Icarus AI** — on demand via Telegram:
  - *"give me a Hermes briefing"* → top signals today
  - *"what does Hermes have on TSMC?"* → company signals
- **SpendLens** — via `HermesClient`, enriches vendor risk scores with live procurement signals

---

**Status:** Live. All crawlers running. Knowledge base built. Content pipeline complete. Icarus LinkedIn skill wired for approval-gated publishing.
