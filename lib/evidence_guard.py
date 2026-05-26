"""
Evidence Guard — Anti-Demo Safeguard
=====================================
Enforces that task completions carry verifiable evidence.
Workers may NEVER mark status='completed' without evidence.

Valid statuses:
  planned              — only a plan exists, no execution started
  awaiting_approval    — work done but needs human sign-off
  completed_with_evidence — done AND evidence provided

Evidence types:
  file_path       — absolute path to output file
  db_row_id       — UUID of the Supabase row created/updated
  screenshot      — path to screenshot file
  commit_hash     — git commit SHA
  url             — live URL of published artifact
  execution_log   — path to log file or log excerpt
  message_id      — Telegram/email message ID proving delivery

Usage:
  from lib.evidence_guard import require_evidence, safe_complete_task, VALID_STATUSES
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

VALID_EVIDENCE_TYPES = frozenset({
    "file_path",
    "db_row_id",
    "screenshot",
    "commit_hash",
    "url",
    "execution_log",
    "message_id",
})

# The ONLY valid operational statuses — "completed" alone is banned
VALID_STATUSES = frozenset({
    "planned",
    "awaiting_approval",
    "completed_with_evidence",
    "running",           # allowed as transient state only
    "received",          # allowed as initial state
    "failed",            # allowed with failure reason
})

# Legacy statuses that exist in DB but are grandfathered — do not create new ones
LEGACY_STATUSES = frozenset({"completed", "queued", "assigned"})


class EvidenceError(ValueError):
    """Raised when a task completion lacks required evidence."""


@dataclass
class Evidence:
    evidence_type: str
    evidence_ref: str
    notes: str = ""

    def validate(self) -> None:
        if self.evidence_type not in VALID_EVIDENCE_TYPES:
            raise EvidenceError(
                f"Invalid evidence_type '{self.evidence_type}'. "
                f"Must be one of: {sorted(VALID_EVIDENCE_TYPES)}"
            )
        if not self.evidence_ref or not str(self.evidence_ref).strip():
            raise EvidenceError(
                f"evidence_ref cannot be empty for type '{self.evidence_type}'"
            )
        # For file_path and screenshot — verify the file actually exists
        if self.evidence_type in ("file_path", "screenshot", "execution_log"):
            p = Path(self.evidence_ref)
            if not p.exists():
                raise EvidenceError(
                    f"Evidence file does not exist: {self.evidence_ref}\n"
                    f"Cannot mark task complete — verify the output was actually written."
                )
        # For URL — basic sanity check
        if self.evidence_type == "url":
            if not (self.evidence_ref.startswith("http://") or
                    self.evidence_ref.startswith("https://")):
                raise EvidenceError(
                    f"Evidence URL must start with http:// or https://: {self.evidence_ref}"
                )
        # For commit_hash — must be hex, 7–40 chars
        if self.evidence_type == "commit_hash":
            ref = self.evidence_ref.strip()
            if not (7 <= len(ref) <= 40 and all(c in "0123456789abcdefABCDEF" for c in ref)):
                raise EvidenceError(
                    f"commit_hash must be a hex SHA (7–40 chars): {ref}"
                )


def require_evidence(evidence: Evidence) -> Evidence:
    """Validate evidence or raise EvidenceError. Returns validated Evidence."""
    evidence.validate()
    return evidence


def safe_complete_task(
    task_id: str,
    evidence: Evidence,
    notes: str = "",
) -> dict:
    """
    Mark a task as completed_with_evidence in Supabase.
    Refuses to proceed if evidence fails validation.
    Returns the Supabase response dict.
    """
    evidence.validate()

    import json
    import urllib.request
    import os

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return {"error": "supabase_not_configured"}

    payload = {
        "status": "completed_with_evidence",
        "evidence_type": evidence.evidence_type,
        "evidence_ref": evidence.evidence_ref,
        "evidence_notes": (evidence.notes or notes or "").strip(),
        "false_completion": False,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/agent_dispatch_tasks?id=eq.{task_id}",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"error": str(exc)}


def flag_false_completion(task_id: str, reason: str = "") -> dict:
    """
    Flag a task as a false completion (claimed done without evidence).
    Used by the audit system to mark legacy bad records.
    """
    import json
    import urllib.request
    import os

    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return {"error": "supabase_not_configured"}

    payload = {
        "false_completion": True,
        "evidence_notes": f"FLAGGED: {reason}" if reason else "FLAGGED: no evidence provided",
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/agent_dispatch_tasks?id=eq.{task_id}",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as exc:
        return {"error": str(exc)}


def audit_false_completions(limit: int = 20) -> list[dict]:
    """
    Return tasks marked 'completed' that have no evidence_type set.
    These are candidates for false_completion=true flagging.
    """
    try:
        from scripts.prelaunch_utils import rest_select
        rows = rest_select(
            f"agent_dispatch_tasks"
            f"?select=id,status,normalized_goal,created_at,evidence_type,false_completion"
            f"&status=eq.completed"
            f"&evidence_type=is.null"
            f"&false_completion=eq.false"
            f"&order=created_at.desc"
            f"&limit={limit}",
            timeout=10,
        )
        return rows or []
    except Exception:
        return []


def status_summary() -> str:
    """One-line summary for Hermes replies about evidence guard status."""
    try:
        false = audit_false_completions(limit=100)
        return (
            f"Evidence guard ACTIVE. "
            f"{len(false)} legacy tasks flagged as possible false completions. "
            f"All new completions require evidence_type + evidence_ref."
        )
    except Exception:
        return "Evidence guard ACTIVE. Status check failed — Supabase may be unreachable."
