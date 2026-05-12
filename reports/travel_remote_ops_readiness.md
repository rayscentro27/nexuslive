# Travel Remote Ops Readiness

Date: 2026-05-10

## Remote Access Checklist
- Chrome Remote Desktop: verify host online, backup access code path, and unattended access.
- VS Code Remote SSH: validate host key trust and SSH auth before travel.
- Oracle/backend access: verify credentials and network path from travel device.

## Emergency Procedures
- Restart services:
  - `launchctl kickstart -k "gui/$(id -u)/ai.nexus.control-center"`
  - `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.telegram"`
  - `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.scheduler"`
- Telegram SSL CA reset (if needed): see `reports/telegram_ssl_repair_summary.md` rollback section.

## Log Locations
- Telegram logs: `openclaw/logs/telegram.log`, `openclaw/logs/telegram.err.log`
- Additional ops reports: `reports/`

## Troubleshooting Notes
- If Telegram send fails with SSL trust error, verify `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` in launchctl env.
- Keep manual-only posture and avoid enabling autonomous execution while remote.

## Status
- Remote infrastructure is ready with documented recovery steps.
