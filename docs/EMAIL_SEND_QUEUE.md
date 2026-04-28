# Email Send Queue

Adds an explicit approval and queue layer for email experiment variants before
anything is actually sent.

Files:

- `supabase/migrations/20260425163000_email_send_queue.sql`
- `research_intelligence/email_send_queue.py`

Usage:

```bash
python3 -m research_intelligence.email_send_queue list --limit 10
python3 -m research_intelligence.email_send_queue approve <variant_id> --note "ready for review"
python3 -m research_intelligence.email_send_queue queue <variant_id> --note "first batch" --scheduled-for 2026-04-26T18:00:00+00:00
```

What it does:

1. reads draft email variants
2. records explicit approval into `email_send_queue`
3. updates the linked variant and campaign statuses
4. does not send email on its own

Important boundary:

- This is a staging and approval layer only.
- It is safe to use before any provider integration exists.
