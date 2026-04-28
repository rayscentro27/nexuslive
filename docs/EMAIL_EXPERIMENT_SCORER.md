# Email Experiment Scorer

Rolls raw `email_send_events` into `email_experiment_results` so email topics
and hooks can be ranked without manually tallying opens, clicks, and replies.

File:

- `research_intelligence/email_experiment_scorer.py`

Usage:

```bash
python3 -m research_intelligence.email_experiment_scorer --limit 1000
python3 -m research_intelligence.email_experiment_scorer --limit 1000 --mark-winners
```

What it does:

1. reads recent `email_send_events`
2. aggregates by `(campaign_id, variant_id)`
3. writes/upserts `email_experiment_results`
4. can optionally mark the strongest queued variant per campaign as `winner`

Current scoring:

- reply = `4`
- click = `2`
- open = `0.5`
- conversion = `6`

This is a simple starting heuristic intended for ranking tests, not a final
attribution model.
