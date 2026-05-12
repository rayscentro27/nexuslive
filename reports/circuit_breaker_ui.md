# Circuit Breaker Dashboard UI — Report
**Date:** 2026-05-12 | **Pass:** Trading Demo Platform | **Admin:** isAdmin gate enforced

## CircuitBreakerDashboard.tsx

### Sections
1. **Kill Switch Panel** — shows 4 env flags (nexus_dry_run, live_trading, auto_trading, swarm_execution). Green check if safe, red warning if unsafe. Emergency Halt button (admin only) calls POST /api/admin/kill-switch.

2. **Active Circuit Breakers** — empty state shows green "All Clear" card. If breakers active: `ActiveBreakerCard` per entry with:
   - Trigger type + icon + color
   - Description + fired timestamp
   - HALT ALL vs STRATEGY PAUSE badge
   - Auto-reset vs manual-reset note
   - Reset button (admin only, non-auto-reset events)

3. **Trigger Reference Table** — all 9 trigger types with icon, label, and reset type (AUTO or MANUAL).

4. **Recent Events History** — resolved/unresolved icons, trigger label, timestamp, resolved_by.

### 9 Trigger Types
| Trigger | Reset | Halt All |
|---|---|---|
| daily_loss_exceeded | AUTO | Yes |
| weekly_drawdown_exceeded | AUTO | Yes |
| consecutive_losses | AUTO | No |
| volatility_spike | AUTO | No |
| api_failure | MANUAL | Yes |
| slippage_anomaly | MANUAL | No |
| abnormal_pnl | MANUAL | Yes |
| operator_halt | MANUAL | Yes |
| market_gap | AUTO | No |

### Production Wiring Notes
- Replace `MOCK_CB_STATUS` with `GET /api/admin/circuit-breakers` (X-Admin-Token required)
- Replace `MOCK_KS_STATE` with `GET /api/admin/kill-switch`
- Emergency Halt: `POST /api/admin/kill-switch {"action":"halt"}`
- Reset breaker: `DELETE /api/admin/circuit-breakers {"trigger_type":"..."}`

### Admin Gate
`canReset={isAdmin && !event.auto_reset}` — only super_admin/admin roles can manually reset. All other users see read-only view.
