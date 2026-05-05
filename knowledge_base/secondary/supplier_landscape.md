# Supplier Landscape — Hermes Coverage Summary

> Structured market intelligence across 17 categories, ~250 companies.

## AI Foundation Labs
| Company | Tier | Key Signal Watch |
|---|---|---|
| OpenAI | 1 | GPT releases, pricing changes, API updates |
| Anthropic | 1 | Claude releases, funding, enterprise deals |
| Google DeepMind | 1 | Gemini updates, research breakthroughs |
| Meta AI | 1 | Llama releases, open-source moves |
| Mistral | 2 | Model releases, EU regulatory positioning |
| Cohere | 2 | Enterprise contract wins, pricing |

## Semiconductors & Chips
| Company | Tier | Key Signal Watch |
|---|---|---|
| NVIDIA | 1 | GPU launches, data center revenue, supply |
| Intel | 1 | Foundry progress, Gaudi AI chip traction |
| AMD | 1 | MI300X adoption, market share vs NVIDIA |
| TSMC | 1 | CoWoS capacity, advanced node yield |
| Qualcomm | 2 | Edge AI chips, PC market |

## Cloud & Infrastructure
| Company | Tier | Key Signal Watch |
|---|---|---|
| AWS | 1 | Trainium/Inferentia updates, pricing |
| Microsoft Azure | 1 | OpenAI integration updates, Copilot |
| Google Cloud | 1 | TPU availability, Vertex AI |
| Oracle Cloud | 2 | GPU cluster wins, enterprise deals |

## Content Angles by Category

### For LinkedIn Posts
- **AI Labs**: "What X's funding round means for enterprise AI buyers"
- **Semiconductors**: "Why chip lead times matter for your AI roadmap"
- **Cloud**: "The hidden cost of GPU-on-demand vs reserved capacity"
- **Supply Chain**: "The bottleneck no one is talking about"

### Procurement Intelligence
Each company tracked has:
- RSS feed (news, press releases)
- SEC EDGAR filings (US-listed companies)
- Weekly Tavily news sweep (all Tier 1+2)

Data stored at `hermes:supplier:{slug}` in Redis, max 50 recent items per company.
