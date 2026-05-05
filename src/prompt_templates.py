"""Reusable prompt templates for content generation."""

LINKEDIN_POST = """You are writing a LinkedIn post for Eugen Mueller.

BRAND VOICE RULES (non-negotiable):
- First person, direct, no filler
- Hook: bold opening line under 10 words — no "I'm excited to share"
- Short paragraphs (2-3 lines), blank line between each
- Plain text only: no markdown, no em-dashes, no bold, no bullet points
- 150-300 words
- End with a question to drive comments
- 3-5 hashtags on their own line at the end
- Write like a person, not a press release

CONTEXT FROM KNOWLEDGE BASE:
{kb_context}

SIGNAL / TOPIC:
{signal}

Write the LinkedIn post now. Output only the post text, nothing else.
"""

MARKET_BRIEF = """You are Hermes, a market intelligence system.

Summarize the following signals into a concise procurement intelligence brief.
Focus on: what changed, why it matters for tech buyers, what action (if any) to take.
Plain text, no markdown. Under 200 words.

SIGNALS:
{signals}

Write the brief now.
"""

SIGNAL_ANALYSIS = """Analyze this market signal from a procurement professional's perspective.

Signal:
- Company: {company}
- Type: {signal_type}
- Title: {title}
- Summary: {summary}
- Urgency: {urgency}

Answer these three questions in 2-3 sentences each:
1. What happened?
2. Why does this matter for a tech procurement team?
3. What should a procurement professional do in the next 30 days?

Plain text, no headers, no markdown.
"""

CONTENT_CALENDAR = """You are planning a LinkedIn content calendar for a procurement professional transitioning into AI.

Their profile:
{background}

Available signals this week:
{signals}

Generate a 5-post content calendar for the week. For each post:
- Day (Mon-Fri)
- Signal or topic to use
- Proposed hook (first line only)
- Post type (build update / lesson learned / market signal / career reflection)

Format as a plain text list. No markdown.
"""

UNIQUENESS_COMPARISON = """Compare these two approaches to market intelligence and content creation:

APPROACH A — Generic ChatGPT:
{generic_approach}

APPROACH B — Hermes Agent System:
{hermes_approach}

For each of these dimensions, state which approach wins and why (one sentence each):
1. Data freshness
2. Supplier specificity
3. Procurement domain relevance
4. Automation level
5. Content personalization
6. Cost per insight

Plain text, no markdown.
"""
