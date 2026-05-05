# Hermes — System Diagram

```
╔══════════════════════════════════════════════════════════════════╗
║                      🌍  THE OUTSIDE WORLD                       ║
║                                                                  ║
║   📰 Tech News    📑 SEC Filings    🤖 AI Research    📈 Markets ║
╚═════════════════════════════╤════════════════════════════════════╝
                              │
                              │  RSS · Tavily · EDGAR
                              │
              ┌───────────────▼──────────────────┐
              │                                  │
              │          ⚡  HERMES  ⚡           │
              │                                  │
              │    ( •_•)🪁   always watching    │
              │                                  │
              │   📡 RSS crawler   every 6h      │
              │   🔍 Tavily        weekly         │
              │   📑 EDGAR         daily          │
              │                                  │
              │   🧠 Claude Haiku                │
              │      classifies every item       │
              │      11 signal types             │
              │      HIGH / MEDIUM / LOW         │
              │                                  │
              │   ~250 companies · Railway 24/7  │
              │                                  │
              │   "I watch. You decide."         │
              └───────────────┬──────────────────┘
                              │
                    writes to Redis
                    hermes:* namespace only
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
   ┌─────────────────────┐    ┌─────────────────────┐
   │     🧠  ICARUS      │    │   📊  SPENDLENS     │
   │                     │    │                     │
   │   ( master agent )  │    │  ( procurement      │
   │                     │    │    dashboard )      │
   │  📱 Telegram        │    │                     │
   │  📧 Gmail           │    │  Pulls Hermes       │
   │  📅 Calendar        │    │  signals on every   │
   │  ✅ Tasks           │    │  analysis cycle     │
   │                     │    │  via HermesClient   │
   │  Natural language:  │    │                     │
   │  ┌─────────────┐    │    │  • Spend categories │
   │  │ "briefing"  │    │    │  • Risk flags       │
   │  │ "TSMC news" │    │    │  • Vendor scoring   │
   │  │ "Miro board"│    │    │  • Signal injection │
   │  └──────┬──────┘    │    │                     │
   │         │           │    └─────────────────────┘
   └─────────┼───────────┘
             │
             │  POST /miro/landscape
             │  POST /miro/signals
             │  (HERMES_API_KEY header)
             │
             ▼
   ┌─────────────────────┐
   │      🎨  MIRO       │
   │                     │
   │   Landscape boards  │
   │   Signal boards     │
   │   Colour-coded      │
   │   by urgency        │
   │                     │
   │   returns URL 🔗    │
   │   → back to you     │
   │     via Telegram    │
   └─────────────────────┘
```

---

## Data Flow in One Line

```
World → Hermes (crawl + classify) → Redis → Icarus / SpendLens → You
```

## Key Rule

```
Hermes WRITES to Redis.
Icarus and SpendLens READ from Redis.
Hermes never sends a message, never touches personal data, never pushes.
```
