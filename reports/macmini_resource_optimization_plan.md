# Mac mini Resource Optimization Plan (Safe Execution Plan)

Date: 2026-05-11
Type: planning-only (no service shutdowns executed)

## Objective
Reduce sustained load on 2014 Intel Mac mini without breaking:
- Hermes Telegram operations
- Admin/workforce dashboards
- onboarding/invite flows
- email/reporting continuity

## Phase 1 — Zero-Risk Improvements (Immediate)
1. Reduce Chrome process footprint (tabs/windows/extensions) during backend operation windows.
2. Keep Activity Monitor and additional dev terminals minimal during unattended runtime.
3. Limit concurrent interactive agent sessions when not needed.

Expected benefit:
- Largest RAM reduction with near-zero Nexus platform risk.

## Phase 2 — On-Demand Service Model (Low Risk)
Move these to start-on-demand or scheduled windows where feasible:
- `ollama serve`
- `dashboard.py` (`127.0.0.1:3000`) when not actively used
- research/trading auxiliary workers not needed 24/7

Keep always-on:
- `telegram_bot.py --monitor`
- `operations_center/scheduler.py`
- `control_center/control_center_server.py`
- `nexus-orchestrator`
- `nexus-research-worker`
- remote access path (SSH/Tailscale/cloudflared as chosen)

Expected benefit:
- incremental RAM/CPU reduction while preserving operator continuity.

## Phase 3 — Placement Strategy (Oracle vs Local)
Candidate to move to Oracle (if stable there):
- compute-heavy or periodic research workers
- non-latency-critical auxiliary jobs
- optional local model inference jobs

Keep local on Mac mini:
- operator-facing control plane requiring low-latency local recovery
- minimal Telegram/control-center stack for emergency continuity

## Phase 4 — Travel Mode Profile
Travel profile should run only:
- Telegram bot
- scheduler
- control center/workforce backend
- orchestrator + research worker (if needed for reporting cadence)
- one reliable remote access channel

Suspend in travel profile (if not needed that day):
- local model server
- trading lab auxiliaries
- extra dashboards/dev servers

## Phase 5 — Validation Before Any Disablement
For each service considered for disable/on-demand:
1. Stop in staging window (manual, supervised).
2. Run quick checks:
   - Telegram response
   - admin auth + workforce endpoint
   - invite/email report path
3. Observe for one business cycle.
4. Promote change to travel profile only after clean observation.

## Risk Matrix
- Low risk to optimize: Chrome/user-session load, idle dev terminals, unused local model runtime.
- Medium risk: trading/research auxiliary workers (dependency uncertainty).
- High risk: Telegram bot, scheduler, control center, orchestrator, remote access channel.

## Suggested Next Pass (separate from this audit)
Create a supervised, reversible execution runbook that:
- toggles one optional service at a time
- validates health checks after each toggle
- records measured RAM/CPU deltas per change
- includes rollback command for each step
