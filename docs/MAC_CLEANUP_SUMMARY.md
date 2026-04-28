# Mac Mini Cleanup Summary
_Scope correction pass — 2026-03-10_

## Files Identified as Oracle-Deployment-Related

| File | Location | Classification |
|------|----------|----------------|
| `nexus-oracle-api/` (entire repo) | `~/nexus-oracle-api/` | Reference only — belongs on Windows/Oracle |
| `/tmp/nexus-oracle-api-deploy.tar.gz` | `/tmp/` | Deprecated — temp artifact, removed |
| `/tmp/oracle_deploy.sh` | `/tmp/` | Deprecated — temp artifact, removed |

## Files Kept (Mac Mini local scope — untouched)

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Telegram alerts — core local service |
| `dashboard.py` | Local Flask dashboard (port 3000) |
| `control_center/control_center_server.py` | Bloomberg terminal (port 4000) |
| `operations_center/` | Ops engine, hedge fund panel, scheduler |
| `research-engine/` | Full research pipeline (collector, summarize, store) |
| `research/ai_research_brain.py` | Research orchestrator |
| `signal-router/tradingview_router.py` | Local webhook receiver (port 8000) |
| `trading-engine/` | Local strategy agent, risk manager, backtester |
| `marketing_automation/`, `lead_intelligence/`, `reputation_engine/` | Local CRM modules |
| `scripts/` | launchd management scripts |
| `docs/LAUNCHD_AUTOSTART.md` | Local service docs |
| `AGENTS.md`, `IDENTITY.md`, `SOUL.md`, `TOOLS.md`, `USER.md` | AI employee identity files |
| `.env` | Local credentials |

## Files Deprecated / Removed

| File | Action | Reason |
|------|--------|--------|
| `/tmp/nexus-oracle-api-deploy.tar.gz` | Deleted | Oracle deployment artifact — wrong machine |
| `/tmp/oracle_deploy.sh` | Deleted | Oracle deploy script — wrong machine |

## nexus-oracle-api Repo Status

`~/nexus-oracle-api/` is kept on this Mac Mini as a **reference copy only**.
- It has its own `.git` history
- It must be deployed from the **Windows machine** to the Oracle VM
- No launchd service, no PM2, no nginx config should be created here for it
- The `.env` inside it has live credentials — do not expose or commit

## Notes on NEXUS_SYSTEM_OVERVIEW.md

`NEXUS_SYSTEM_OVERVIEW.md` mentions Oracle/goclearonline in the architecture diagram (correct —
it's documenting the system). No change needed. The diagram accurately shows Oracle VM as a
separate tier.
