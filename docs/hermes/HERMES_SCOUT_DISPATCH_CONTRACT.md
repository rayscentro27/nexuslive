# Hermes Scout Dispatch Contract

## When to Dispatch

A scout should be dispatched when:
1. Ray asks a question Hermes cannot answer with verified evidence
2. Ray explicitly asks "can your scouts figure it out?"
3. A CFO response has unknowns that require external research
4. Ray asks about competitor data, market rates, or real-time pricing

## Scout Roster

| Scout | Handles |
|-------|---------|
| monetization_scout | Revenue streams, affiliate offers, pricing benchmarks |
| affiliate_monetization_scout | Specific affiliate programs, commissions, approval requirements |
| content_intelligence_scout | Content gaps, SEO opportunities, competitor content |
| credit_repair_research_scout | Credit programs, funding requirements, FICO guidelines |
| funding_opportunity_scout | Grants, loans, SBA programs, funding checklists |
| system_reliability_scout | Technical failures, performance issues, architecture concerns |
| trading_research_scout | Market conditions, strategy performance, backtest results |
| strategy_scout | Product direction, competitive positioning, market fit |
| market_research_scout | Customer research, audience analysis, survey data |
| hermes_behavior_scout | Hermes response quality, command coverage gaps |
| general_research_scout | Anything not covered by the above |

## File Storage

All scout assignments are written to:
  `docs/reports/research_queue/hermes_scout_assignments.jsonl`

All research queue entries are written to:
  `docs/reports/research_queue/hermes_research_queue.jsonl`

## No Automatic Actions

Scouts are research assignments, not execution agents. A scout assignment:
- Writes to the research queue file
- Records what evidence is needed
- Does NOT make network calls automatically
- Does NOT approve or publish anything
- Requires Ray to review findings before action
