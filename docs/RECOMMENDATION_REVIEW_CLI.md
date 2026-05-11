# Recommendation Review CLI

Use the review CLI to inspect and action `research_recommendations` without
manually patching Supabase rows.

CLI:

- `research_intelligence/recommendation_review_cli.py`

Examples:

```bash
python3 -m research_intelligence.recommendation_review_cli list --limit 10
python3 -m research_intelligence.recommendation_review_cli show 4cd93fa3-d146-592b-8010-1be0b5f0782d
python3 -m research_intelligence.recommendation_review_cli approve 4cd93fa3-d146-592b-8010-1be0b5f0782d --note "Approved for execution"
python3 -m research_intelligence.recommendation_review_cli reject 4cd93fa3-d146-592b-8010-1be0b5f0782d --note "Needs stronger evidence"
python3 -m research_intelligence.recommendation_review_cli mark-review 4cd93fa3-d146-592b-8010-1be0b5f0782d --note "Send back to pending review"
```

Supported actions:

- `list`: shows recent recommendation rows
- `show`: shows the full packet for one recommendation
- `approve`: sets `approval_status = 'approved'`
- `reject`: sets `approval_status = 'rejected'`
- `mark-review`: sets `approval_status = 'pending'`
- `run-approved`: approves, hands off, and runs the downstream execution workers

Notes:

- `approve` is intended to be followed by:

```bash
python3 -m research_intelligence.approval_handoff_worker --once
python3 -m research_intelligence.site_build_worker --limit 5
```

- Review metadata is stored in `metadata.reviewed_at`, `metadata.review_action`,
  and `metadata.review_note`.
