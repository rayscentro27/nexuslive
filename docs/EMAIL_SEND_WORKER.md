# Email Send Worker

Consumes queued email experiment variants and logs send events.

File:

- `research_intelligence/email_send_worker.py`

Usage:

```bash
python3 -m research_intelligence.email_send_worker --limit 10 --dry-run
python3 -m research_intelligence.email_send_worker --limit 10
```

What it does:

1. reads `email_send_queue` rows with `queue_status = queued`
2. loads the linked campaign and variant
3. sends using the existing operator SMTP helper when not in dry-run mode
4. writes `email_send_events`
5. marks queue rows and variants/campaigns as `sent` or `failed`

Important boundary:

- `--dry-run` is the safe default workflow for validating the pipeline.
- Without `--dry-run`, this uses the configured Gmail SMTP credentials from
  `notifications/operator_notifications.py`.
