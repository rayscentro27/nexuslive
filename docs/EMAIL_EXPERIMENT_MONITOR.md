# Email Experiment Monitor

Operator view for checking what happened after send without manually querying
multiple tables.

Files:

- `research_intelligence/email_experiment_monitor.py`

Usage:

```bash
python3 -m research_intelligence.email_experiment_monitor --limit 10
python3 -m research_intelligence.email_experiment_monitor --limit 10 --no-refresh-score
```

What it does:

1. optionally reruns `email_experiment_scorer`
2. reads current `email_experiment_results`
3. reads recent `email_send_events`
4. joins in campaign, variant, and queue status context
5. prints a compact JSON snapshot for operator review

This is useful right after sending or when checking whether replies, opens,
clicks, or conversions have started to show up.
