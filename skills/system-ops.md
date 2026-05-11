# Skill: System Operations — Worker Health & Self-Healing

## Worker Hierarchy

| Tier | Worker | Label | Control |
|---|---|---|---|
| 0 | hermes-gateway | ai.hermes.gateway | automatic |
| 1 | ops-control-worker | com.nexus.ops-control-worker | automatic |
| 1 | monitoring-worker | com.nexus.monitoring-worker | automatic |
| 2 | nexus-orchestrator | com.nexus.nexus-orchestrator | automatic |
| 2 | autonomy-worker | com.nexus.autonomy-worker | automatic |
| 2 | email-pipeline | ai.nexus.email-pipeline | automatic |
| 2 | coordination-worker | com.nexus.coordination-worker | automatic |
| 2 | grant-worker | com.nexus.grant-worker | automatic |
| 2 | opportunity-worker | com.nexus.opportunity-worker | automatic |
| 2 | nexus-research-worker | com.nexus.nexus-research-worker | automatic |
| 2 | research-orchestrator-transcript | com.nexus.research-orchestrator-transcript | automatic |
| 2 | research-orchestrator-grants-browser | com.nexus.research-orchestrator-grants-browser | automatic |
| 3 | signal-router | com.nexus.signal-router | automatic |
| 3 | trading-engine | com.nexus.trading-engine | manual |
| 3 | cloudflare-tunnel | com.nexus.cloudflare-tunnel | automatic |

## Self-Healing
`ops-control-worker` runs every 10 minutes. It reads `worker_control_plane` in
Supabase and restarts any worker with `control_mode='automatic'` whose launchd
service is not running. Trading engine is `manual` — ops-control never restarts it.

## Quick Health Commands
```bash
# All worker processes
ps aux | grep -E "nexus|hermes|trading|signal|orchestrator" | grep -v grep

# Launchd registration
launchctl list | grep -E "nexus|hermes|trading"

# Trading engine status
cat ~/nexus-ai/logs/trading_engine_status.json

# Cloudflare tunnel URL (changes on restart)
grep "trycloudflare.com" ~/nexus-ai/logs/cloudflare-tunnel.log | tail -1

# Signal router health
curl -s http://127.0.0.1:8000/health

# Trading engine health
curl -s http://127.0.0.1:5000/health
```

## Restart a Worker
```bash
launchctl unload ~/Library/LaunchAgents/<label>.plist
sleep 2
launchctl load ~/Library/LaunchAgents/<label>.plist
```

## Common Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| Hermes not responding | Stale lock file | `rm ~/.local/state/hermes/gateway-locks/*.lock` then restart |
| autonomy_worker import error | PYTHONPATH missing | Ensure `PYTHONPATH=/Users/raymonddavis/nexus-ai` in plist |
| Trading engine KeyError api_key | broker_config not set in JSON | Add explicit broker_config to trading_config.json |
| Signal rejected: instrument invalid | Symbol format wrong | Oanda needs EUR_USD not EURUSD |
| Monitoring worker Telegram spam | EXPECTED_WORKERS mismatch | Edit monitoring_worker.py EXPECTED_WORKERS list |

## Logs Location
- Hermes gateway: `~/.hermes/logs/gateway.log`
- Trading engine: `~/nexus-ai/logs/trading_engine.log`
- Trading engine status: `~/nexus-ai/logs/trading_engine_status.json`
- Signal router: `~/nexus-ai/signal-router/signal-router.log`
- Cloudflare tunnel: `~/nexus-ai/logs/cloudflare-tunnel.log`
- Worker logs: `~/nexus-ai/logs/<worker-name>.log`

## Supabase Tables (Core)
- `worker_control_plane` — desired state for all workers
- `system_events` — event queue (autonomy_worker polls this)
- `user_profiles` — client records
- `tasks` — agent-created tasks
- `job_events` — job execution log
- `error_log` — system errors
- `hermes_reviews` — trade signal audit log
