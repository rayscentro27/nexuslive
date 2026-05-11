# Hermes Workers Spec

## Overview
Hermes is the "Operations Copilot" for the Nexus AI Hedge Fund. It provides a Telegram-based control interface for the human operator and serves as an internal review layer for autonomous processes.

## Roles & Responsibilities
- **Status Monitoring**: Provides real-time snapshots of system health and worker status.
- **Task Management**: Syncs with `coord_tasks` in Supabase to show pending, in-progress, and completed tasks.
- **Signal Review**: Acts as a gateway for reviewing trading signals before execution.
- **Research Refinement**: Assists in the refinement of research results and strategy extraction.
- **Ops Command Interface**: Executes pre-defined operator phrases (e.g., `status`, `show pending tasks`) to run system diagnostics.

## Control Model
Hermes operates within a three-layer control architecture:
1. **Runtime Layer**: Actual processes (launchd, scheduled jobs, OpenClaw gateway).
2. **Control Layer**: Source of truth for desired state (Supabase `worker_control_plane`).
3. **Judgment Layer (Hermes)**: Explains state, recommends actions, and translates operator intent into structured control requests.

## Command Mappings
Hermes uses fixed operator phrases for common tasks:
- `status` -> `scripts/hermes_ops_snapshot.sh`
- `what needs attention` -> `scripts/hermes_ops_attention.sh`
- `show pending tasks` -> `python3 nexus_coord.py tasks codex`
- `run lead check` -> `python3 operations_center/scheduler.py --run-now leads`
- `run reputation check` -> `python3 operations_center/scheduler.py --run-now reputation`

## Safety Boundaries
- Hermes does not directly mutate infrastructure without a logged command path.
- Process mutations require human approval for risky changes.
- Decisions are logged in `worker_control_actions` for auditability.
- No direct exposure of secrets in Telegram replies.

## Files & Components
- `hermes_claude_bot.py`: Primary bot logic for operator interaction.
- `hermes_status_bot.py`: Specialized bot for status updates and alerts.
- `hermes_command_router/`: Logic for routing and parsing Telegram commands.
- `docs/AUTONOMOUS_OPERATIONS_AND_HERMES_CONTROL.md`: Detailed control model documentation.
