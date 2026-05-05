# LinkedIn Post Examples — Style Reference

## Example 1: Building in Public
```
I automated the job I used to do manually.

For years, tracking supplier news meant opening 20 browser tabs every Monday morning.
NVIDIA earnings, TSMC capacity updates, AMD announcements.
It was slow, inconsistent, and I always missed something.

So I built Hermes.

An autonomous agent that crawls RSS feeds, SEC filings, and live news for 250 companies.
It classifies every item by signal type. Funding, supply chain risk, product launches.
Stores everything in Redis. Available on demand.

Last week it caught a TSMC capacity warning 48 hours before it hit procurement newsletters.

The tool took 3 weeks to build.
It saves me 4-5 hours every week.

The ROI math is obvious. The harder question: why did I wait so long to automate it?

What repetitive work in your role could an agent handle?

#Procurement #AI #Automation #SupplyChain #BuildingInPublic
```

## Example 2: Lesson Learned
```
The hardest part of building an AI agent isn't the AI.

It's deciding what it should NOT do.

Hermes monitors 250 suppliers. It classifies signals. It stores intelligence.
It does not send alerts. It does not make decisions. It does not access personal data.

That boundary was deliberate.

When I first designed it, I wanted it to do everything.
Crawl the web, summarise findings, send me Telegram messages, update my calendar.

The result was chaos. Tools conflicted. Permissions got messy. Debugging was a nightmare.

The fix was a hard architectural rule: Hermes writes to Redis. Icarus reads from Redis. Never the reverse.

One agent, one responsibility.

Suddenly everything got simpler. Faster. More reliable.

The best design decision I made was removing features, not adding them.

What's the last thing you removed from a system that made it better?

#SoftwareDesign #AIAgents #Procurement #LessonsLearned
```

## Key Patterns to Replicate
- Open with a short, punchy statement (under 10 words)
- Tell a specific story with concrete details
- One clear insight per post
- End with a question
- 3-5 hashtags on their own line
