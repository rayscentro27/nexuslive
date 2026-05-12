# Animated Workforce Operations Dashboard — Implementation Plan
**Date:** 2026-05-11  
**Route:** `/admin/workforce-operations`  
**Inspired by:** pixel-agents (pablodelucca) — structural inspiration only, no code copied

---

## Objectives

1. Replace the basic worker heartbeat table with a visually impressive, demo-ready animated dashboard
2. Map real Supabase data (`worker_heartbeats`, `job_queue`, `workflow_outputs`) to visual worker states
3. Never show fake activity — fallback to OFFLINE/empty-desk state when data unavailable
4. Maintain all safety flags unchanged
5. Mobile-responsive, accessible, lightweight (no external JS dependencies)

---

## Architecture Decision

**Approach:** Replace the inline HTML return in `admin_workforce_operations_page()` with a module-level `_WORKFORCE_OPS_HTML` constant. The route function simply returns this constant after admin auth check.

**Why not a separate template file?**  
The rest of the control center (TERMINAL_HTML, ~2800 lines) uses the same inline constant pattern. Consistency prevents introducing a new file dependency for a single page.

---

## Data Sources (Existing APIs — No New Endpoints)

| API | Data Used | Purpose |
|-----|-----------|---------|
| `/api/admin/ai-operations/workforce` | `worker_heartbeats`, `queue_load`, `recent_activity`, `online_offline_summary` | Worker states, queue pressure, activity feed |
| `/api/admin/ai-operations/overview` | `approval_summary.pending_count` | Pending approvals metric |
| `/api/admin/ai-operations/timeline` | `timeline[]` | Activity feed merge |

All APIs pre-existed. No new endpoints created.

---

## Worker Roster (Static Definition)

9 workers defined statically. Live heartbeat data is matched onto them by `worker_id` substring comparison.

| ID Key | Display Name | Role | Color |
|--------|-------------|------|-------|
| `hermes` | Hermes | Command & Routing | #6366f1 (indigo) |
| `funding` | Funding AI | Funding Intelligence | #10b981 (green) |
| `credit` | Credit AI | Credit Workflow | #3b82f6 (blue) |
| `marketing` | Marketing AI | Content & Growth | #f59e0b (amber) |
| `grant` | Grant AI | Grant Research | #8b5cf6 (purple) |
| `research` | Research AI | Signal Research | #06b6d4 (cyan) |
| `operations` | Operations AI | Ops Monitor | #64748b (slate) |
| `crm` | CRM Copilot | Client Intelligence | #ec4899 (pink) |
| `trading` | Trading Lab | Market Research (RO) | #f97316 (orange) |

---

## Status Mapping

| Data Condition | Visual State | Animation | Badge |
|---------------|-------------|-----------|-------|
| `status=running/active` + recent heartbeat | `st-active` | Green breathing ring, avatar bobs | ACTIVE (green) |
| `status=running/active` + open queue jobs | `st-working` | Blue spinning dashed ring, cursor blink | WORKING (blue) |
| `status=pending_approval/waiting` | `st-waiting` | Amber pulse ring | WAITING (amber) |
| `status=stale` OR heartbeat >30min old | `st-stale` | No animation, reduced opacity | STALE (gray) |
| `status=error/failed` | `st-error` | Red flashing ring | ERROR (red) |
| No heartbeat row at all | `st-offline` | No animation, low opacity | OFFLINE (dim) |

---

## Visual Design System

**Theme:** Dark command-center (#080d12 background), subtle dot-grid floor plan pattern  
**Typography:** System UI sans-serif for UI chrome, monospace for status badges  
**Animations:** Pure CSS `@keyframes` — no JavaScript animation loops  
**Pixel-office feel:**
- Dot-grid background on floor plan (CSS `radial-gradient`)
- Slightly squared avatar border-radius (6px) evoking pixel characters
- Small CSS desk icon decoration on each station
- Color-coded desk accent bar at station bottom

---

## Layout Structure

```
[HEADER] Title | Clock | Refresh
[SAFETY STRIP] 6 active safety flags
[METRIC ROW] Roster | Online | Working | Stale | Queue Pending | Approvals
[MAIN GRID: 2/3 + 1/3]
  [FLOOR PLAN: 3×3 grid of worker stations]
  [LIVE ACTIVITY FEED]
[QUEUE LOAD STRIP: bar chart + legend]
```

---

## Accessibility

- `role="main"`, `role="banner"`, `role="list"`, `role="listitem"` on structural elements
- `aria-label` on all interactive and status elements
- `aria-live="polite"` on all dynamically-updated metric values and feeds
- `@media (prefers-reduced-motion: reduce)` disables all CSS animations
- Status descriptions exposed via `title` and `aria-label` attributes
- No color-only status encoding — badge text always present

---

## Performance

- Zero external dependencies (no CDN scripts, no external fonts)
- CSS animations only (no JS animation frames)
- Auto-refresh every 30 seconds via `setInterval`
- Three API calls in parallel via `Promise.all`
- Feed items capped at 40 items

---

## Safety Guarantees

All safety flags displayed in UI strip. No changes to:
- `SWARM_EXECUTION_ENABLED`
- `HERMES_SWARM_DRY_RUN`  
- `HERMES_CLI_EXECUTION_ENABLED`
- `TRADING_LIVE_EXECUTION_ENABLED`
- `TELEGRAM_AUTO_REPORTS_ENABLED`
- `HERMES_KNOWLEDGE_AUTO_STORE_ENABLED`

The dashboard is **read-only** — it calls only `GET` endpoints. No POST, no execution triggers.

---

## Fallback Behavior

If `worker_heartbeats` returns empty:
- Banner: "No live worker data found. Workers offline or database unreachable."
- All 9 roster stations shown in `st-offline` state
- Metrics show `—` (em-dash) until data arrives
- No fake "working" or "active" states are inferred

---

## Files Modified

| File | Change |
|------|--------|
| `control_center/control_center_server.py` | Replaced `admin_workforce_operations_page()` return HTML with new `_WORKFORCE_OPS_HTML` constant (~280 lines HTML/CSS/JS) |

---

## Manual Route Validation

Since there are no frontend unit tests, validate manually:

1. Start control center: `launchctl kickstart -k gui/$(id -u)/ai.nexus.control-center`
2. Visit: `http://localhost:4000/admin/workforce-operations?admin_token=nexus-admin-2026-safe`
3. Verify: 9 worker stations rendered, metrics populated, activity feed visible
4. Without live DB: confirm "No live worker data found" shown, all 9 stations show OFFLINE
5. Mobile: resize to <600px, verify 2-column grid and stacked layout
