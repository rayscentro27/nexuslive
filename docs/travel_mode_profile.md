# Travel Mode Profile

## Purpose
Run a minimum safe Nexus stack while Mac mini is unattended, preserving operator and CEO workflows.

## Required Processes
- `telegram_bot.py --monitor`
- `operations_center/scheduler.py`
- `control_center/control_center_server.py`
- `services/nexus-orchestrator/src/index.js`
- `services/nexus-research-worker/src/index.js`
- One remote access path: SSH plus either Tailscale or cloudflared

## Optional Processes to Pause in Travel Mode
- `ollama serve`
- `dashboard.py` (`127.0.0.1:3000`)
- `tradingview_router.py`
- `auto_executor.py`
- `tournament_service.py`
- `research_signal_bridge.py`

## Startup Order
1. Remote path (`sshd`, then Tailscale/cloudflared)
2. `control_center/control_center_server.py`
3. `services/nexus-orchestrator/src/index.js`
4. `services/nexus-research-worker/src/index.js`
5. `operations_center/scheduler.py`
6. `telegram_bot.py --monitor`

## Validation Checks (must all pass)
1. Telegram bot receives and responds to a safe status query
2. Admin auth still enforced on protected routes
3. Workforce endpoint returns expected authorized response shape
4. Email reporting path confirms send capability in configured runtime
5. Invite/onboarding path remains reachable

## Rollback Procedures
If any validation fails after optional service changes:
1. Restart last changed service via its launch agent label
2. Re-run validation checklist
3. If still failing, restore all optional services and return to baseline profile

## Travel-Mode Safety Rules
- One service change per cycle
- Observe at least one full scheduler interval before next change
- Do not modify auth, feature flags, or deployment configs during travel-mode tuning
