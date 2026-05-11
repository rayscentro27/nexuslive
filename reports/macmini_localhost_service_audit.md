# Mac mini Localhost Service Audit

Date: 2026-05-11
Host: 2014 Intel Mac mini
Scope: audit/classification only. No services were stopped or modified.

## 1) Localhost Ports (listening)
- `127.0.0.1:11434` -> `ollama serve` (`/usr/local/bin/ollama`)
- `127.0.0.1:3000` -> `dashboard.py` (Nexus local dashboard)
- `127.0.0.1:4000` -> `control_center/control_center_server.py` (AI Ops/Workforce backend)
- `*:5000` -> `nexus_trading_engine.py`
- `127.0.0.1:8000` -> `signal-router/tradingview_router.py`
- `127.0.0.1:20241` -> `cloudflared tunnel`
- `*:22` -> SSH daemon
- `127.0.0.1:25` and `127.0.0.1:587` -> local postfix mail listeners

## 2) Process Inventory (Nexus-relevant)
- Python: `telegram_bot.py --monitor`, `scheduler.py`, `control_center_server.py`, `dashboard.py`, `nexus_trading_engine.py`, `auto_executor.py`, `tradingview_router.py`, `tournament_service.py`, `research_signal_bridge.py`
- Node: `services/nexus-orchestrator/src/index.js`, `services/nexus-research-worker/src/index.js`, `mac-mini-worker` node process
- Infra helpers: `cloudflared tunnel`, `ollama serve`, Tailscale network extension

## 3) launchctl Inventory (Nexus labels seen)
- Running labels observed: `com.nexus.orchestrator`, `com.nexus.research-worker`, `com.nexus.cloudflare-tunnel`, `com.nexus.mac-mini-worker`, `com.nexus.ollama`, `com.raymonddavis.nexus.dashboard`
- Additional loaded Nexus labels present (some not currently active PID): scheduler/telegram/control-center/trading/signal/autonomy/ops worker families

## 4) Resource Usage Summary
- System snapshot: ~8.1 GB used / ~8.2 GB total, ~55 MB free at sample moment
- Load average: ~3.53 / 3.57 / 2.88
- CPU snapshot: ~24.7% user, ~42.8% system, ~32.5% idle
- Swap activity historically high (`swapins`/`swapouts` non-trivial), consistent with memory pressure history on 8 GB hardware

### Highest memory consumers (not all Nexus)
- Chrome renderer + Chrome parent processes dominate memory footprint (multiple 50 MB-1.1 GB processes)
- `opencode` session process ~700 MB class
- `claude` process ~400 MB class
- Nexus processes are generally moderate per-process (roughly ~20-100 MB per Python/Node service)

## 5) Dependency Mapping (high-level)
- **Hermes/Telegram path**: `telegram_bot.py`, scheduler, orchestrator/research workers, outbound HTTPS, local email notifier path
- **Admin/Workforce path**: `control_center_server.py` on `127.0.0.1:4000`
- **Client dashboard path**: `dashboard.py` on `127.0.0.1:3000`
- **Trading path**: trading engine + signal router + auto executor + tournament service
- **Knowledge/research path**: research worker + research signal bridge + orchestrator
- **Remote access path**: SSH + Tailscale + cloudflared tunnel

## 6) Critical Services (must remain)
- `telegram_bot.py --monitor`
- `operations_center/scheduler.py`
- `control_center/control_center_server.py`
- `services/nexus-orchestrator/src/index.js`
- `services/nexus-research-worker/src/index.js`
- `cloudflared tunnel` (if used for remote ingress)
- SSH/Tailscale (if relied on for remote ops)

## 7) Optional Services (use-case dependent)
- `ollama serve` (only needed for local model workflows)
- `dashboard.py` on `:3000` (optional if admin/workforce access is primary and dashboard can be accessed elsewhere)
- local postfix listeners if not actively used by current flow

## 8) Likely Legacy / Idle Candidates
- Long-running local dev-oriented workers with low current activity signals may be idle candidates:
  - `tournament_service.py`
  - `research_signal_bridge.py`
  - trading auxiliaries (`auto_executor.py`, `tradingview_router.py`) if not currently trading/testing
- Chrome-heavy local UI sessions appear to be the largest memory burden and are operationally separate from backend service continuity.

## 9) Unknown / Manual Review Needed
- launchctl labels loaded without active PID for multiple `com.nexus.*` families (could be on-demand jobs)
- whether `dashboard.py` and control-center are both required 24/7 in travel mode
- whether local Ollama is required continuously or only on-demand

## 10) Safe Optimization Recommendations (no action executed)
- Prioritize reducing Chrome tab/process count before touching core Nexus daemons.
- Keep core Hermes/admin services running; move non-critical model/research/trading auxiliaries to on-demand schedule.
- Convert selected workers to time-window execution (business hours only) instead of continuous runtime.
- Keep remote ingress minimal: retain one primary path (Tailscale and/or cloudflared based on operational preference).

## 11) Estimated Savings (order-of-magnitude)
- Reducing heavy Chrome session load: potentially **1.5-3.0+ GB RAM** reclaimed.
- Stopping optional local model service (`ollama`) when unused: small-to-moderate background savings, larger during active inference.
- Pausing idle auxiliary Python workers: roughly **20-100 MB each** plus reduced wakeups.

## 12) Travel-Mode Recommendations
- Keep only critical ops set live: Telegram bot, scheduler, control center, orchestrator, research worker, remote access channel.
- Place optional components (local model server, trading auxiliaries, secondary dashboards) into on-demand mode.
- Pre-flight checklist before travel: verify Telegram replies, admin auth, workforce endpoint, and one remote SSH/Tailscale path.

## Highest-Risk Unknowns
- Unknown dependency coupling among dormant `com.nexus.*` launch agents could cause surprise behavior if disabled without staged testing.
- Current memory pressure appears influenced by user-session apps as much as backend services; optimization should avoid misattributing root cause.
