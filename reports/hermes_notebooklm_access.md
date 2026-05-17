# Hermes NotebookLM Access

## Objective
Make NotebookLM intelligence directly usable in Hermes decision support.

## Current State
- Hermes internal-first supports NotebookLM intake queue summaries.
- Hermes Supabase-first includes broad ops/revenue/trading intents but limited explicit NotebookLM command set in operator language.

## Required Command Coverage
- "What did NotebookLM learn?"
- "Summarize the forex notebook"
- "Show strongest trading concepts"
- "What funding insights were added?"
- "What strategies are appearing repeatedly?"
- "What opportunities are trending?"
- "What should we research deeper?"

## Operational Response Contract
For NotebookLM intents Hermes should return:
1. Recency: last sync + notebook coverage.
2. Confidence: high/medium/low and why.
3. Repetition: repeated concepts and count.
4. Contradictions: conflicting lessons/claims.
5. Action: next best research or implementation step.

## Integration Requirements
- Supabase-first retrieval from approved notebook-derived records.
- Fallback to dry-run queue summary if no approved records exist.
- Route high-confidence strategy/opportunity patterns into Hall of Fame candidate lists.

## Trust Guardrails
- Mark notebook insights as guidance, not guarantees.
- Preserve demo/paper-only trading posture.
- Do not auto-execute trades or publish content from Hermes suggestions.
