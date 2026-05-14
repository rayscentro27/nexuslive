# Final Cron Overlap Prune

Generated: 2026-05-14

## Current crontab review
- Nexus One summary lines are commented out and remain disabled.
- No explicit opportunity brief / grant brief cron lines found.
- Active cron entries retained for monitoring, readiness (`--silent`), provider health, research processing, and opportunity research.

## Prune decision
- No additional cron deletions made in this pass because summary-spam cron entries were already disabled/absent.
- Telegram spam risk reduced at sender layer (policy + gate), so retained jobs now write to logs/Supabase without auto-summary Telegram fanout.
