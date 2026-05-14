# Telegram Cron / Launchd / Env Removal

## Launchd actions

- Disabled launchd spam source:
  - `com.nexus.research-orchestrator-transcript` booted out
  - any paired research-orchestrator launchd summary path disabled during pass

## Cron actions

- Disabled Nexus One auto summary cron lines by commenting them in user crontab:
  - `python3 -m nexus_one.nexus_one_worker brief`
  - `python3 -m nexus_one.nexus_one_worker alert`

## Environment flags audited

- Existing confirmed false:
  - `TELEGRAM_AUTO_REPORTS_ENABLED=false`
  - `TELEGRAM_FULL_REPORTS_ENABLED=false`
  - `TELEGRAM_RESEARCH_ALERTS_ENABLED=false`

## Defaults enforced in code (when flags absent)

- `TELEGRAM_OPERATIONAL_NOTIFICATIONS_ENABLED=false` (default)
- policy-level default deny for blocked summary event types
- summary sender paths deny unless explicitly allowlisted and requested
