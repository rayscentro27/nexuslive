# Oracle Offload Candidates

Date: 2026-05-11
Goal: reduce sustained Mac mini load while preserving local operational control.

## Best Offload Candidates (Oracle)
1. `research_intelligence/research_signal_bridge.py`
2. `trading-engine/tournament_service.py`
3. `trading-engine/auto_executor.py` (kept disabled/guarded per policy)
4. `signal-router/tradingview_router.py` (if low-latency local intake is not required)
5. Batch/periodic research enrichment tasks from orchestrator satellites

## Keep Local (Mac mini)
1. `telegram_bot.py --monitor`
2. `operations_center/scheduler.py`
3. `control_center/control_center_server.py`
4. `services/nexus-orchestrator/src/index.js`
5. `services/nexus-research-worker/src/index.js` (unless fully stable Oracle failover exists)
6. Primary remote access channel and auth-critical endpoints

## On-Demand / Scheduled Candidates
- `ollama serve` (start only when local inference needed)
- `dashboard.py` (`:3000`) outside active operator windows
- non-critical experimental workers and monitors

## Offload Decision Rules
- Offload if workload is compute-heavy, periodic, and non-interactive
- Keep local if workload is operator-facing, recovery-critical, or auth-control-plane related
- Move only one service at a time with rollback path and health validation

## Rollback Strategy
For each offloaded service:
1. Preserve local launch agent definition
2. Keep documented local restart command
3. Validate Telegram/admin/workforce/remote access before and after cutover
