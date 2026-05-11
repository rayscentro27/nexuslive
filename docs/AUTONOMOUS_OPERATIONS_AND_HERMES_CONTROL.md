# Nexus Autonomous Operations And Hermes Control

This document defines how Nexus should operate when:

- core processes run autonomously
- the human operator can still intervene
- Hermes can be used as an internal review/control layer without becoming an unsafe auto-admin

---

## Goal

Nexus should support both:

1. **Autonomous background operation**
   - ingestion, scoring, routing, monitoring, alerts
2. **Operator-directed control**
   - activate, pause, reconfigure, or inspect workers and schedules

Hermes should help with decision support and controlled workflow changes, but it should not silently mutate infrastructure on its own.

---

## Current State

### Already autonomous

- `nexus-orchestrator`
- `nexus-research-worker`
- transcript ingestion scheduler
- grant browser ingestion scheduler
- `grant_worker` scheduler
- `opportunity_worker` scheduler
- OpenClaw gateway
- Hermes runtime/gateway

### Hermes is currently wired into

- research result refinement via `services/nexus-research-worker/src/hermes.js`
- trading signal review via `trading-engine/hermes/trade_reviewer.py`

### Missing today

- one canonical control surface for starting/stopping/reloading workers
- one canonical registry of worker desired-state
- one Hermes-facing command path for process changes
- one approval path for infrastructure mutations

---

## Recommended Control Model

Nexus should have three separate layers:

### 1. Runtime Layer

This is the actual process/scheduler layer.

**Owns:**
- launchd services
- scheduled jobs
- local gateways
- process health

**Examples:**
- `com.nexus.orchestrator`
- `com.nexus.research-worker`
- `com.nexus.opportunity-worker`
- `com.nexus.grant-worker`
- `ai.openclaw.gateway`
- `ai.hermes.gateway`

### 2. Control Layer

This is the source of truth for what should be running.

**Should own:**
- desired enabled/disabled state per worker
- schedule settings
- pause/resume commands
- maintenance mode
- last operator action

**Recommended storage:**
- Supabase table such as `worker_control_plane`
- optional local fallback JSON for emergency use

### 3. Judgment Layer

This is where Hermes belongs.

Hermes should:
- explain process state
- recommend actions
- validate requested changes
- translate operator intent into structured control actions

Hermes should not:
- directly edit launchd files on its own
- directly kill/start services without a logged command path
- bypass human approval for risky changes

---

## Best-Fit Hermes Role

Hermes should act as an **operations copilot**, not a hidden root user.

That means Hermes can:
- answer: "what is down?"
- answer: "why is grant ingestion quiet?"
- suggest: "restart OpenClaw"
- suggest: "pause transcript ingestion for 2 hours"
- draft a structured action:
  - `restart_service`
  - `pause_worker`
  - `resume_worker`
  - `update_schedule`
  - `set_maintenance_mode`

Then Nexus applies that action through a controlled executor.

---

## Recommended Command Flow

### Read-only path

1. Operator asks Hermes about worker/process status.
2. Hermes reads status inputs:
   - `worker_heartbeats`
   - `job_queue`
   - `system_events`
   - recent logs
   - local service status
3. Hermes returns:
   - current state
   - likely issue
   - recommended next action

### Controlled write path

1. Operator asks Hermes to make a process change.
2. Hermes converts that into a structured control request.
3. Request is written to a control table such as `worker_control_actions`.
4. A local control executor validates and applies the request.
5. Result is written back to Supabase and surfaced by Telegram/dashboard.

This keeps Hermes useful without giving it invisible admin power.

---

## Minimum Tables To Add

### `worker_control_plane`

One row per worker/service.

Suggested fields:
- `worker_id`
- `worker_type`
- `enabled`
- `desired_state`
- `schedule_seconds`
- `maintenance_mode`
- `last_changed_by`
- `last_changed_at`
- `notes`

### `worker_control_actions`

Append-only command log.

Suggested fields:
- `id`
- `target_worker_id`
- `action_type`
- `payload`
- `status`
- `requested_by`
- `requested_at`
- `approved_by`
- `executed_at`
- `execution_result`

---

## Minimum Components To Add

### `ops_control_worker`

A new local executor service that:
- polls `worker_control_actions`
- validates requested actions
- later applies safe launchd/process changes
- writes execution results back

### `hermes_ops_adapter`

A lightweight adapter that:
- gathers runtime health
- asks Hermes for recommendations when needed
- optionally turns approved operator intent into structured control requests

### Current first slice now scaffolded

- `docs/migrations/20260419_worker_control_plane.sql`
- `workflows/ai_workforce/ops_control_worker/ops_control_worker.js`
- `workflows/ai_workforce/ops_control_worker/hermes_ops_adapter.js`

Current behavior is intentionally safe:
- reads control-plane state
- validates pending actions
- supports read-only Hermes diagnosis
- lets Hermes draft and queue structured control actions
- executes only safe control-plane state changes
- does **not** directly restart or mutate launchd services yet

---

## Safety Rules

Hermes-assisted control should follow these rules:

- read-only diagnosis can be automatic
- process mutations must be logged
- risky mutations should require human confirmation
- no direct secrets exposure in Hermes responses
- no destructive commands without explicit operator intent
- launchd/service changes should be reversible

---

## Recommended Implementation Order

1. Keep current autonomous services as the runtime base.
2. Add `worker_control_plane` and `worker_control_actions`.
3. Build `ops_control_worker` for safe service control.
4. Add a Hermes ops adapter for read-only diagnosis first.
5. Add write-capable Hermes control only after action logging is in place.
6. Expose the same control state in Telegram/dashboard.

---

## Plain-English Summary

Yes, Nexus should run autonomously.

But Hermes should not be the thing directly flipping services on and off in the dark.

The clean model is:

- workers run automatically
- orchestrator routes work
- Hermes explains and recommends
- a control worker executes approved changes

That gives you autonomy, operator visibility, and a safe way to "talk to Hermes" when you want the system changed.
