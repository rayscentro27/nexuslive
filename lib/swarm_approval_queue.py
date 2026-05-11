"""Approval queue state for planned swarm runs (preview-only)."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import threading
import uuid

from lib.swarm_scenarios import build_scenario_preview

_LOCK = threading.Lock()
_RUNS: dict[str, dict] = {}

ALLOWED_STATES = {
    "planned",
    "awaiting_approval",
    "approved",
    "rejected",
    "expired",
    "cancelled",
}

TRANSITIONS = {
    "planned": {"awaiting_approval", "cancelled", "expired"},
    "awaiting_approval": {"approved", "rejected", "cancelled", "expired"},
    "approved": {"cancelled"},
    "rejected": set(),
    "expired": set(),
    "cancelled": set(),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _snapshot(run: dict) -> dict:
    return deepcopy(run)


def _transition(planned_run_id: str, new_state: str, actor: str, note: str) -> dict:
    if new_state not in ALLOWED_STATES:
        return {"error": "invalid_state", "planned_run_id": planned_run_id}
    with _LOCK:
        row = _RUNS.get(planned_run_id)
        if not row:
            return {"error": "planned_run_not_found", "planned_run_id": planned_run_id}
        old_state = row.get("approval_status", "planned")
        allowed_next = TRANSITIONS.get(old_state, set())
        if new_state not in allowed_next:
            return {
                "error": "invalid_transition",
                "planned_run_id": planned_run_id,
                "from": old_state,
                "to": new_state,
            }
        row["approval_status"] = new_state
        row["updated_at"] = _now()
        row.setdefault("audit_log", []).append(
            {
                "at": row["updated_at"],
                "actor": actor or "unknown",
                "event": f"planned_run_{new_state}",
                "note": note,
            }
        )
        _RUNS[planned_run_id] = row
        return _snapshot(row)


def create_planned_run(
    scenario_id: str,
    requested_by: str,
    approval_status: str = "awaiting_approval",
) -> dict:
    preview = build_scenario_preview((scenario_id or "").strip())
    scenario = preview.get("scenario") or {}
    swarm_preview = preview.get("swarm_preview") or {}
    if not scenario or not swarm_preview:
        return {
            "error": "scenario_not_found",
            "scenario_id": scenario_id,
            "approval_required": True,
            "execution_mode": "preview_only",
            "can_execute": False,
        }
    state = approval_status if approval_status in ALLOWED_STATES else "awaiting_approval"
    if state == "approved":
        state = "awaiting_approval"
    planned_run_id = f"prun_{uuid.uuid4().hex[:12]}"
    now = _now()
    row = {
        "planned_run_id": planned_run_id,
        "scenario_id": scenario.get("scenario_id"),
        "initiating_role": scenario.get("initiating_role"),
        "delegated_roles": scenario.get("delegated_roles", []),
        "requested_by": (requested_by or "operator").strip() or "operator",
        "created_at": now,
        "updated_at": now,
        "approval_status": state,
        "approval_required": True,
        "execution_mode": "preview_only",
        "can_execute": False,
        "risk_level": scenario.get("risk_level") or swarm_preview.get("risk_level") or "medium",
        "preview_snapshot": preview,
        "audit_log": [
            {
                "at": now,
                "actor": (requested_by or "operator").strip() or "operator",
                "event": "planned_run_created",
                "note": "State-only queue record; no execution triggered.",
            }
        ],
    }
    with _LOCK:
        _RUNS[planned_run_id] = row
    return _snapshot(row)


def list_planned_runs() -> list[dict]:
    with _LOCK:
        rows = [_snapshot(v) for v in _RUNS.values()]
    rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return rows


def get_planned_run(planned_run_id: str) -> dict | None:
    with _LOCK:
        row = _RUNS.get(planned_run_id)
    return _snapshot(row) if row else None


def approve_planned_run(planned_run_id: str, actor: str = "operator") -> dict:
    return _transition(planned_run_id, "approved", actor, "Approval recorded; execution remains disabled.")


def reject_planned_run(planned_run_id: str, actor: str = "operator", reason: str = "") -> dict:
    note = f"Rejected: {reason}" if reason else "Rejected by operator."
    return _transition(planned_run_id, "rejected", actor, note)


def cancel_planned_run(planned_run_id: str, actor: str = "operator", reason: str = "") -> dict:
    note = f"Cancelled: {reason}" if reason else "Cancelled by operator."
    return _transition(planned_run_id, "cancelled", actor, note)
