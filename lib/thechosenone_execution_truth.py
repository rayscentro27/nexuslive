"""
TheChoseone — Execution Truth Layer.

Every command/task gets a receipt with an HONEST execution_state and
worker_target. TheChoseone must never claim a worker ran when it did not.

Receipts: logs/thechosenone/command_receipts.jsonl (append) +
          logs/thechosenone/latest_command_receipt.json (latest).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs" / "thechosenone"
RECEIPTS = LOG_DIR / "command_receipts.jsonl"
LATEST = LOG_DIR / "latest_command_receipt.json"

# Honest lifecycle states.
EXECUTION_STATES = [
    "received", "parsed", "queued", "routed_to_worker", "worker_started",
    "worker_completed", "blocked", "dry_run_only", "report_ready", "failed",
]
WORKER_TARGETS = [
    "none", "internal_script", "proof_automation", "showroom", "codex",
    "claude", "opencode", "hermes_mobile", "external_unknown",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_command_receipt(command_text: str, source: str = "telegram",
                           user: str = "ray") -> dict:
    cid = "cmd_" + uuid.uuid4().hex[:10]
    rec = {
        "command_id": cid,
        "timestamp": _now(),
        "source": source,
        "user": user,
        "command_text": command_text,
        "parsed_intent": None,
        "worker_target": "none",
        "execution_state": "received",
        "safety_gate_result": "pending",
        "report_path": None,
        "job_id": None,
        "next_action": None,
        "history": [{"state": "received", "at": _now()}],
    }
    _persist(rec)
    return rec


def update_command_receipt(rec: dict, **fields) -> dict:
    if "execution_state" in fields:
        st = fields["execution_state"]
        if st not in EXECUTION_STATES:
            raise ValueError(f"invalid execution_state {st!r}")
        rec.setdefault("history", []).append({"state": st, "at": _now()})
    if "worker_target" in fields and fields["worker_target"] not in WORKER_TARGETS:
        raise ValueError(f"invalid worker_target {fields['worker_target']!r}")
    rec.update(fields)
    rec["timestamp"] = _now()
    _persist(rec)
    return rec


def verify_worker_handoff(rec: dict) -> dict:
    """Truth check: a worker_started/worker_completed state is only honest if a
    real job_id exists from a live worker. Otherwise downgrade and flag."""
    state = rec.get("execution_state")
    target = rec.get("worker_target")
    job = rec.get("job_id")
    if state in ("worker_started", "worker_completed") and (not job or str(job).startswith("none")):
        rec["execution_state"] = "queued"
        rec["truth_note"] = f"downgraded: claimed {state} but no live job_id for {target}"
        _persist(rec)
    return rec


def summarize_execution_receipt(rec: dict) -> str:
    return (f"[{rec['command_id']}] intent={rec.get('parsed_intent')} · "
            f"worker={rec.get('worker_target')} · state={rec.get('execution_state')} · "
            f"safety={rec.get('safety_gate_result')} · job={rec.get('job_id') or '-'}")


def _persist(rec: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(json.dumps(rec, indent=2, default=str))
    # append a compact line to the jsonl ledger (one event per update)
    with RECEIPTS.open("a") as fh:
        fh.write(json.dumps({"command_id": rec["command_id"], "at": rec["timestamp"],
                             "intent": rec.get("parsed_intent"),
                             "worker_target": rec.get("worker_target"),
                             "execution_state": rec.get("execution_state"),
                             "safety_gate_result": rec.get("safety_gate_result"),
                             "job_id": rec.get("job_id")}, default=str) + "\n")


def list_recent_commands(n: int = 10) -> list[dict]:
    if not RECEIPTS.exists():
        return []
    lines = RECEIPTS.read_text().splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def get_command_status(command_id: str) -> dict | None:
    """Return the latest known state for a command_id from the ledger."""
    latest = None
    for ev in list_recent_commands(500):
        if ev.get("command_id") == command_id:
            latest = ev
    return latest
