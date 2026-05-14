# Mac Mini Full Process Inventory

Generated: 2026-05-14

## Commands Run
- `ps aux`
- `launchctl list`
- `crontab -l`
- `lsof -i -P`
- `pm2 list` (not installed)
- `brew services list`

## Active Nexus/Hermes Processes (Observed)
- PID `96995` `python .../telegram_bot.py --monitor` (`/Users/raymonddavis/nexus-ai`) via launchd label `com.raymonddavis.nexus.telegram`; Telegram sender: yes; email: no; Supabase: yes; should exist: yes.
- PID `97001` `python .../operations_center/scheduler.py` (`/Users/raymonddavis/nexus-ai`) via launchd label `com.raymonddavis.nexus.scheduler`; Telegram sender: indirect via `lib/hermes_gate`; email: yes (`operator_notifications`); Supabase: yes; should exist: yes.
- PID `579` `python control_center/control_center_server.py` (`/Users/raymonddavis/nexus-ai`) via launchd `ai.nexus.control-center`; Telegram sender: control-plane only; email: yes; Supabase: yes; should exist: yes.
- PID `591` `python -m hermes_cli.main gateway run` (`~/.hermes/hermes-agent`) via launchd `ai.hermes.gateway`; Telegram sender: no direct send API; should exist: yes.
- PID `557` `node services/nexus-orchestrator/src/index.js` via launchd `com.nexus.orchestrator`; Telegram sender path exists in code; should exist: conditional.
- PID `561` `node services/nexus-research-worker/src/index.js` via launchd `com.nexus.research-worker`; Telegram sender path exists in code; should exist: conditional.
- PID `575` `node mac-mini-worker/src/mac-mini-worker.js` via launchd `com.nexus.mac-mini-worker`; Telegram sender: no direct evidence in runtime sample; should exist: yes.
- PID `558` `ollama serve` via launchd `com.nexus.ollama`; provider backend only; should exist: yes.
- PID `565` `python .../dashboard.py`; launchd `com.raymonddavis.nexus.dashboard`; Telegram: no; should exist: optional.
- PID `555` `python .../signal-router/tradingview_router.py`; launchd `com.nexus.signal-router`; Telegram: indirect path in stack; should exist: optional.

## Network Endpoints (Relevant)
- `localhost:11434` (`ollama`)
- `localhost:4000` (`control_center_server.py`)
- `localhost:3000` (`dashboard.py`)
- `localhost:8000` (`tradingview_router.py`)
- Telegram outbound session observed from PID `96995` to `149.154.166.110:443`.

## Process Source Classification
- launchd: primary source for all Nexus services listed above.
- cron: secondary periodic workers (see scheduler forensics report).
- pm2: not installed.
- brew services: `cloudflared` shown but status `none`.

## Immediate Findings
- Spam risk primarily comes from legacy worker modules with direct Telegram API calls and no central policy call.
- `com.nexus.opportunity-worker` / `com.nexus.grant-worker` were present as LaunchAgent files and were removed in this pass.
