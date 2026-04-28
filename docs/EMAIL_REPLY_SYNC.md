# Email Reply Sync

Syncs Gmail inbox replies into `email_send_events` as `replied` rows so the
email experiment scorer can rank variants using actual response behavior.

Files:

- `research_intelligence/email_reply_sync.py`
- `research_intelligence/email_send_worker.py`

Usage:

```bash
python3 -m research_intelligence.email_reply_sync --days 14 --dry-run
python3 -m research_intelligence.email_reply_sync --days 14
```

How matching works:

1. scans the Nexus Gmail inbox over IMAP
2. ignores self-sent mailbox traffic
3. tries to match replies by explicit body marker:
   `NX-EMAIL <campaign_id> <variant_id>`
4. falls back to recipient email plus normalized subject matching for older sends
5. inserts `replied` events into `email_send_events`

The send worker now appends a plain-text reference marker to outgoing experiment
emails and also stores the original subject in event metadata, which makes
future reply matching much more reliable than subject-only inference.
