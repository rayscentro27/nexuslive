# Hermes Ops Commands

Use these from the repo root when Hermes needs a fast operator view without burning extra model cost.

## Snapshot

```bash
scripts/hermes_ops_snapshot.sh
```

Shows:
- autonomy stack health
- coordination summary
- recent scheduler activity

## Attention

```bash
scripts/hermes_ops_attention.sh
```

Shows:
- current FAIL/state lines from the autonomy stack
- pending tasks for `hermes`, `codex`, and `claude-code`
- recent scheduler error lines

## Suggested Hermes Phrases

Natural-language asks that should map well to these scripts:

- `status`
- `give me an ops snapshot`
- `what needs attention`
- `show pending tasks`
- `summarize system health`
