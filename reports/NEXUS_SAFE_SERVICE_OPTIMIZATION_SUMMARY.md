# NEXUS Safe Service Optimization Summary

Date: 2026-05-11
Branch: `origin/agent-coord-clean`
Mode: safe planning and validation framework only

## 1) Critical Services
- `telegram_bot.py --monitor`
- `operations_center/scheduler.py`
- `control_center/control_center_server.py`
- `services/nexus-orchestrator/src/index.js`
- `services/nexus-research-worker/src/index.js`
- one reliable remote access path (`sshd` + Tailscale or cloudflared)

## 2) Optional Services
- `ollama serve`
- `dashboard.py` (`127.0.0.1:3000`)
- `tradingview_router.py`
- `auto_executor.py`
- `tournament_service.py`
- `research_signal_bridge.py`

## 3) Travel-Mode Profile
- Defined and documented in `docs/travel_mode_profile.md`
- Uses minimum critical stack and one-at-a-time reversible adjustments

## 4) Safest Optimization Opportunities
1. Reduce Chrome memory footprint first
2. Move optional services to on-demand windows
3. Validate after each single service change

## 5) Biggest Resource Consumers
- Primary: Chrome renderer/process footprint and active interactive AI sessions
- Secondary: cumulative baseline of multiple always-on workers

## 6) Chrome Impact Findings
- Chrome contributes the largest memory pressure spikes on 8 GB hardware
- Practical savings likely exceed most single-service backend tuning

## 7) Oracle Offload Recommendations
- Offload non-interactive periodic workloads first (research/trading auxiliaries)
- Keep operator-critical control plane local unless fully proven remote failover exists

## 8) Rollback Procedures
- One service change at a time
- Immediate rollback on any failed check
- Standard validation order: remote access -> Telegram -> admin/workforce -> email/report -> invite/onboarding

## 9) Highest-Risk Unknowns
- Hidden dependencies among loaded-but-idle `com.nexus.*` launch labels
- Potential coupling of optional services to niche reporting paths not exercised continuously

## 10) GO / NO-GO Recommendation for Travel Profile
Recommendation: **GO (conditional)**

Conditions:
- Follow one-service-at-a-time plan in `docs/safe_shutdown_test_plan.md`
- Execute full checklist in `docs/service_health_validation.md` after each change
- Maintain at least one verified fallback remote access path before any optional pause

## Safety Verification
- No mass stops/disables performed in this pass
- No auth weakening or config mutations introduced
- Unsafe automation flags were not enabled
