# Travel Emergency Operations v2

Date: 2026-05-10

## Emergency Restart Commands
- `launchctl kickstart -k "gui/$(id -u)/ai.nexus.control-center"`
- `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.telegram"`
- `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.scheduler"`

## Telegram SSL Recovery Check
- Confirm `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` are set in launchctl to certifi bundle path.

## Fallback Ops Path
- If Telegram degraded: send/report via email route and pull latest under `reports/`.

## Critical Log Paths
- `openclaw/logs/telegram.log`
- `openclaw/logs/telegram.err.log`
- `reports/` for generated summaries
