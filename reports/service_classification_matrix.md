# Service Classification Matrix

Date: 2026-05-11
Source inputs: localhost audit snapshots, launchctl inventory, process/listener mapping.

| service/process | port | purpose | required 24/7? | travel-mode required? | estimated RAM impact | estimated CPU impact | safe to stop manually? | rollback command | dependency risk |
|---|---|---|---|---|---|---|---|---|---|
| `telegram_bot.py --monitor` | outbound (no fixed listen) | Hermes Telegram operations + operator loop | Yes | Yes | Medium (~20-40 MB) | Low/variable | No (except supervised test) | restart launch agent `com.raymonddavis.nexus.telegram` | High |
| `operations_center/scheduler.py` | outbound | cadence/jobs/reporting triggers | Yes | Yes | Low (~5-20 MB) | Low | No (except supervised test) | restart launch agent `com.raymonddavis.nexus.scheduler` | High |
| `control_center/control_center_server.py` | `127.0.0.1:4000` | AI Ops/admin + workforce backend | Yes | Yes | Medium (~35-60 MB) | Low | No | restart launch agent `ai.nexus.control-center` | High |
| `services/nexus-orchestrator/src/index.js` | outbound | orchestration and worker coordination | Yes | Yes | Medium (~35-60 MB) | Low/medium | No | restart launch agent `com.nexus.orchestrator` | High |
| `services/nexus-research-worker/src/index.js` | outbound | research workflow runtime | Yes | Yes (if research briefs required) | Medium (~35-60 MB) | Low/medium | No | restart launch agent `com.nexus.research-worker` | High |
| `cloudflared tunnel` | `127.0.0.1:20241` | remote ingress/tunnel path | Usually | One remote path required | Low/medium (~15-30 MB) | Low | Yes, if alternate remote path active | restart launch agent `com.nexus.cloudflare-tunnel` | Medium |
| SSH daemon (`sshd`) | `*:22` | remote shell/recovery | Yes | Yes | Low | Low | No | system launchd-managed | High |
| Tailscale network extension | local control + tunnel socket | remote private connectivity | Optional baseline, recommended | Yes (if primary remote path) | Low/medium | Low | Yes only if cloudflared+SSH path verified | start Tailscale app/login item | Medium |
| `dashboard.py` | `127.0.0.1:3000` | legacy/local dashboard surface | Optional | No | Medium (~50-80 MB) | Low | Yes (supervised) | restart launch agent `com.raymonddavis.nexus.dashboard` | Medium |
| `ollama serve` | `127.0.0.1:11434` | local model inference | Optional/on-demand | No | Low idle / high when active | Low idle / high when active | Yes (supervised) | restart launch agent `com.nexus.ollama` | Low/medium |
| `trading-engine/nexus_trading_engine.py` | `*:5000` | trading engine runtime | Optional (if trading inactive) | Usually no | Medium (~15-40 MB) | Low/medium | Yes (supervised) | restart launch agent `com.nexus.trading-engine` | Medium/high |
| `signal-router/tradingview_router.py` | `127.0.0.1:8000` | signal intake/routing | Optional (if no active trading) | No | Medium (~20-40 MB) | Low | Yes (supervised) | restart launch agent `com.nexus.signal-router` | Medium |
| `trading-engine/auto_executor.py` | outbound | execution helper path | Optional (must stay off for safety policy) | No | Medium (~20-40 MB) | Low | Yes (supervised) | restart launch agent `com.nexus.auto-executor` | Medium |
| `trading-engine/tournament_service.py` | outbound | trading tournament workflow | Optional | No | Medium (~30-45 MB) | Low | Yes (supervised) | restart launch agent `com.nexus.tournament` | Low/medium |
| `research_intelligence/research_signal_bridge.py` | outbound | research signal bridge | Optional/on-demand | No | Medium (~60-110 MB) | Low | Yes (supervised) | restart launch agent `com.nexus.research-signal-bridge` | Medium |
| Local postfix (`master`, `pickup`, `qmgr`) | `127.0.0.1:25`, `127.0.0.1:587` | local mail transport path | Optional (depends on notifier route) | No | Low | Low | Yes after email validation | launchd/system mail service start | Medium |

Notes:
- RAM/CPU estimates are based on observed snapshots and should be confirmed over a longer sampling window.
- “Safe to stop manually” means only one-at-a-time with immediate health validation and rollback readiness.
