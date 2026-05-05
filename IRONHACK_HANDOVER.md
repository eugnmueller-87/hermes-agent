# Ironhack Week 3 — Session Handover

**Date:** 2026-05-04  
**Next session:** Tomorrow — live content pipeline test

---

## What was built this session

The intelligence layer (crawlers → Redis) already existed from previous weeks. This session added the **content layer** on top.

### New files created

| File | Purpose |
|---|---|
| `knowledge_base/primary/brand_voice.md` | Tone rules, post formula, forbidden phrases |
| `knowledge_base/primary/background.md` | 10yr procurement career, angle for content |
| `knowledge_base/primary/linkedin_examples.md` | 2 annotated example posts for style reference |
| `knowledge_base/primary/methodology.md` | Content pillars, post types, signal-to-post workflow |
| `knowledge_base/secondary/hermes_signals_sample.md` | Sample signals with procurement + content angles |
| `knowledge_base/secondary/supplier_landscape.md` | 250 companies, tier rankings, angles per category |
| `src/document_processor.py` | Loads `.md` files, builds 8,000-char context blocks |
| `src/knowledge_base.py` | `KnowledgeBase` class with `brand_voice_context()` / `signals_context()` |
| `src/llm_integration.py` | `LLMClient` wrapping Anthropic API — Haiku for briefs, Sonnet for drafts |
| `src/prompt_templates.py` | 5 templates with `{kb_context}` + `{signal}` placeholders |
| `src/content_pipeline.py` | Full 6-step pipeline: Document → Monitor → Brief → Draft → Publish → Iterate |
| `src/main.py` | CLI entry point with argparse |
| `config/vscode_agent.json` | VSCode agent config with tools, system_prompt, content_rules |
| `UNIQUENESS.md` | 6-dimension comparison: Generic ChatGPT vs Hermes |

### Updated files

| File | What changed |
|---|---|
| `TLDR.md` | Rewritten from crawler-only to full two-layer system |
| `presentation/index.html` | Expanded to 5 slides, required Ironhack project headlines used as titles |

### Bug fixed

`content_pipeline.py` was calling `client.get_significant_items()` — method does not exist on `HermesClient`.  
Fixed to: `client.get_procurement_briefing(limit=20)` (line 162 of `integrations/hermes_client.py`).

---

## Architecture

```
Intelligence layer (live since Week 2):
  RSS every 6h   ─┐
  EDGAR daily    ─┼─→ Claude Haiku classify → Redis (hermes:*)
  Tavily weekly  ─┘

Content layer (built this session):
  Redis signals → fetch_signals()
       ↓
  Knowledge base (primary 4 docs + secondary 2 docs) → brand_voice_context()
       ↓
  Claude Sonnet → LinkedIn post draft (150–300 words)
       ↓
  Telegram staging → Icarus one-tap approval → publish
```

Never auto-publishes. Always approval-gated through Icarus.

---

## Tomorrow's test — two options

### Option A: Manual signal (recommended — full demo control)
Only needs `ANTHROPIC_API_KEY`. No Redis required.

```bash
cd C:\Users\eugnm\OneDrive\Desktop\hermes-agent
python -m src.main --signal NVIDIA --summary "NVIDIA announces GB200 NVL72 availability for hyperscalers, lead times 6-9 months"
```

### Option B: Live Redis signals
Needs all 4 env vars in `.env`.

```bash
python -m src.main --urgency HIGH
```

### Sanity checks before the test

```bash
# 1. Confirm KB loads correctly (no env vars needed)
python -m src.main --kb

# 2. Confirm market brief works (needs Redis for Option B)
python -m src.main --brief
```

---

## What a good output looks like

A passing test post will:
- Start with a specific fact (not "I'm excited to share...")
- Name the actual company and product
- Have a procurement angle — lead times, pricing risk, sourcing implications
- Be 150–300 words, plain text, no markdown, no em-dashes, no bold
- End with 3–5 relevant hashtags

If output is generic or hallucinates: tune `knowledge_base/primary/brand_voice.md` or `src/prompt_templates.py` → `LINKEDIN_POST`.

---

## Ironhack requirements status

| Requirement | Status |
|---|---|
| GitHub Kanban board | Live — GitHub Projects (accepted as Trello substitute) |
| Primary knowledge base | 4 docs built |
| Secondary knowledge base (research layer) | 2 docs built |
| LLM API integration | `LLMClient` — Haiku + Sonnet |
| Prompt templates (5) | LINKEDIN_POST, MARKET_BRIEF, SIGNAL_ANALYSIS, CONTENT_CALENDAR, UNIQUENESS_COMPARISON |
| Content generation pipeline | 6-step, CLI via `src/main.py` |
| VSCode agent config | `config/vscode_agent.json` |
| Uniqueness comparison | `UNIQUENESS.md` |
| Presentation (5 slides, required headlines) | `presentation/index.html` |
| Pushed to IRONHACK repo | `https://github.com/eugnmueller-87/IRONHACK.git` |

### Still needed (manual actions)

- **Day 1 Kanban screenshot** — screenshot GitHub Projects board → add image to IRONHACK repo
- **Day 2 Kanban screenshot** — take after tomorrow's test session

---

## Key file locations

| What you need | Where |
|---|---|
| Run the pipeline | [src/main.py](src/main.py) |
| Manual signal test | `src/main.py:49` — `cmd_signal()` |
| Signal fetch from Redis | `src/content_pipeline.py:46` — `fetch_signals()` |
| Post generation | `src/content_pipeline.py:84` — `draft_post()` |
| Brand voice rules | `knowledge_base/primary/brand_voice.md` |
| Post prompt template | `src/prompt_templates.py` — `LINKEDIN_POST` |
| HermesClient briefing method | `integrations/hermes_client.py:162` — `get_procurement_briefing()` |
| Presentation slides | `presentation/index.html` |

---

## Env vars reference

```
ANTHROPIC_API_KEY         Always needed (LLM calls)
UPSTASH_REDIS_REST_URL    Needed for live Redis signals (Option B)
UPSTASH_REDIS_REST_TOKEN  Needed for live Redis signals (Option B)
TAVILY_API_KEY            Crawler only, not needed for content test
```
