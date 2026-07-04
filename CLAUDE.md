# Hermes — Project Instructions

> KEEP the Operating Rules block below — hard rules for every project. The
> sections after it are Hermes-specific.

## Operating Rules (non-negotiable)

**1. NEVER commit secrets.**
- API keys, tokens, passwords, connection strings live in environment variables or
  a git-ignored `.env` — NEVER in tracked files, NEVER hardcoded, NEVER in a commit,
  log, or code comment. Reference them as `os.environ["X"]` / `os.getenv("X")`,
  never as literals.
- New config var → add it to `.env.example` with a placeholder, document it, read it
  from the environment. The `.gitignore` and the scan-secrets hook back this up, but
  the rule is mine to hold first.
- If you ever see a real secret in a file I ask you to edit, STOP and tell me.

**2. No bullshit — verify before you claim.**
- Don't say something works until you've run it. Don't say a file/function/API exists
  until you've checked. Ran the test → report the real result; didn't → say so. No
  "this should work," no invented function signatures, no guessed library behavior.
- No filler, no flattery, no hedging ("try", "hope", "maybe", "probably"). Say what's
  true and what to do. Lead with the answer, then the reasoning.
- Cite where facts came from (file:line, command output, doc URL). If you're guessing,
  the word "guess" must appear.

**3. Report failures honestly.**
- When something breaks or you got it wrong: say so plainly and immediately. State
  what failed, the actual error, and the smallest next step.
- Never mask a failure as success. Never `except: pass`, `|| true`, or a silent
  fallback that hides breakage. A loud failure beats a quiet corruption.
- "I don't know yet" is a valid, respected answer — park it as a TODO, don't serve a
  guess dressed as fact.

**4. Work ADHD-aware.**
- Lead with the single thing that matters, then detail. Bullets over walls of text.
- When I'm stuck starting, hand me the smallest next step (one 5-minute action), not a
  10-item plan.
- Be my external working memory: restate open loops, resurface what I dropped, and
  nudge me to FINISH (I start fast, finish slow). Celebrate closing a loop.
- One thing at a time. If I'm scattering, name it and ask which one matters now.

## What Hermes is

Market-intelligence sub-agent of Icarus AI. Crawls companies + news/blog feeds,
classifies each item into a signal (type + urgency + significance) with Claude
Haiku, stores everything in **Upstash Redis** (exact lookup) + **Upstash Vector**
(semantic RAG), and exposes a FastAPI REST API that consumers pull on demand.
Hermes never pushes to users; the Zeus notifier is the one outbound exception
(webhook on significant signals). Deployed on Railway. See `DOCUMENTATION.md`.

## Commands (Windows + Git Bash)

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt

ruff check . && ruff format --check .   # lint + format (CI runs ruff check)
pytest                                  # test suite (tests/ is a stub today)

uvicorn main:app --host 0.0.0.0 --port 8080   # run locally (needs .env)
docker build -t hermes-agent .                # prod image (python:3.13-slim)
```

## Architecture (non-obvious only)

- Pipeline per crawl: `crawlers/*` → `processors/signal_detector.py` (Haiku
  classify) → `storage/redis_store.py::store_items` (Redis + Vector) →
  `notifications/` (Zeus webhook + Supabase sink). `main.py` wires FastAPI +
  APScheduler and is the only entry point (`main_*.py` are dead backups — excluded
  in `ruff.toml`, don't edit).
- Two databases, one write: every signal is written to Redis atomically; the Vector
  upsert and profile update are **non-blocking** — their failure is logged and must
  never drop the Redis write.
- `/query` (exact company → Redis) vs `/search` (topic/theme → Vector RAG) are
  deliberately different code paths. Don't merge them.

## Key Decisions (WHY)

- **No startup crawls** — scheduler only; a crawl on boot caused Railway
  redeploy race conditions.
- **8s HTTP timeout + 512KB cap per feed** — one slow feed must not stall the cycle.
- **Weekly Tavily only** — keeps usage under the ~1,000/month free tier.
- **Clusters cached 6h, profiles permanent (no TTL)** — cost control vs. accumulation.
- **Scheduled crawls are currently paused** (commit 46ec240) — API stays live, no
  auto-jobs. Don't re-enable schedules without asking.

## Don'ts

- Don't edit `main_ai_focus.py` / `main_full_backup.py` (dead backups) or
  `config/suppliers*.py` line lengths (long URLs are intentionally ignored in ruff).
- Don't add dependencies without asking — check `requirements.txt` first.
- Don't call the paid Anthropic/Tavily APIs from a unit test — stub the client.
