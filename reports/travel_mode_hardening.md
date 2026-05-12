# Travel Mode Hardening

Date: 2026-05-10

## Travel Mode Checklist
- Telegram operational and SSL trust verified.
- Email operational and report delivery verified.
- Launchctl restart commands documented and tested.
- Report paths and log locations documented for remote access.

## Remote Ops Commands
- `launchctl kickstart -k "gui/$(id -u)/ai.nexus.control-center"`
- `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.telegram"`
- `launchctl kickstart -k "gui/$(id -u)/com.raymonddavis.nexus.scheduler"`

## Recovery Notes
- If Telegram HTTPS fails, verify launchctl `SSL_CERT_FILE` and `REQUESTS_CA_BUNDLE` values.
- Use email summary route when mobile network conditions degrade Telegram responsiveness.
