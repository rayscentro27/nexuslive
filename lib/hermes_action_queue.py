"""
hermes_action_queue.py
=======================
Hermes action tracker. Every Hermes action is registered here.

Hermes creates actions when:
  - Ray gives a goal
  - Ray sends a link
  - Hermes finds an opportunity
  - A scout is assigned
  - A blocker appears
  - An artifact is created
  - A decision requires approval

Stored in:
  docs/reports/actions/hermes_action_queue.jsonl  — append-only log
  docs/reports/actions/hermes_action_queue_latest.md  — plain-language summary
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_ROOT = Path(__file__).resolve().parent.parent
_QUEUE_JSONL = _ROOT / "docs" / "reports" / "actions" / "hermes_action_queue.jsonl"
_QUEUE_MD = _ROOT / "docs" / "reports" / "actions" / "hermes_action_queue_latest.md"
_MAX_LOAD = 200  # last N records to load

ActionStatus = Literal[
    "proposed", "queued", "assigned", "in_progress", "blocked",
    "completed_with_artifact", "failed", "needs_ray_approval",
]


@dataclass
class Action:
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:10]}")
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    goal_id: str = ""
    source_id: str = ""  # intake_id if triggered by a source
    title: str = ""
    description: str = ""
    assigned_to: str = ""  # agent/worker name
    assigned_scout: str = ""
    status: ActionStatus = "proposed"
    priority: int = 50
    evidence_used: list[str] = field(default_factory=list)
    artifact_outputs: list[str] = field(default_factory=list)
    next_step: str = ""
    autonomous_allowed: bool = True
    requires_ray_approval: bool = False
    approval_reason: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        status_emoji = {
            "proposed": "💡", "queued": "📋", "assigned": "👷", "in_progress": "🔄",
            "blocked": "🔴", "completed_with_artifact": "✅", "failed": "❌",
            "needs_ray_approval": "⏳",
        }.get(self.status, "⚪")
        lines = [f"{status_emoji} **{self.title}**"]
        if self.assigned_to or self.assigned_scout:
            worker = self.assigned_scout or self.assigned_to
            lines.append(f"   Assigned to: {worker}")
        if self.next_step:
            lines.append(f"   Next: {self.next_step}")
        if self.requires_ray_approval and self.status == "needs_ray_approval":
            lines.append(f"   ⏳ Waiting for Ray approval: {self.approval_reason}")
        if self.artifact_outputs:
            lines.append(f"   Evidence: {self.artifact_outputs[0]}")
        return "\n".join(lines)


def _load_records(max_records: int = _MAX_LOAD) -> list[Action]:
    if not _QUEUE_JSONL.exists():
        return []
    try:
        lines = _QUEUE_JSONL.read_text().splitlines()
        records: list[Action] = []
        for line in lines[-max_records:]:
            if line.strip():
                d = json.loads(line)
                records.append(Action(**{k: v for k, v in d.items()
                                         if k in Action.__dataclass_fields__}))
        return records
    except Exception:
        return []


def _save_record(action: Action) -> None:
    _QUEUE_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(_QUEUE_JSONL, "a") as f:
        f.write(json.dumps(action.to_dict()) + "\n")


def create_action(
    title: str,
    description: str = "",
    goal_id: str = "",
    source_id: str = "",
    assigned_to: str = "",
    assigned_scout: str = "",
    priority: int = 50,
    autonomous_allowed: bool = True,
    requires_ray_approval: bool = False,
    approval_reason: str = "",
    status: ActionStatus = "queued",
) -> Action:
    """Create and persist a new action."""
    action = Action(
        title=title,
        description=description,
        goal_id=goal_id,
        source_id=source_id,
        assigned_to=assigned_to,
        assigned_scout=assigned_scout,
        priority=priority,
        autonomous_allowed=autonomous_allowed,
        requires_ray_approval=requires_ray_approval,
        approval_reason=approval_reason,
        status=status,
    )
    _save_record(action)
    return action


def update_action_status(action_id: str, status: ActionStatus,
                         artifact_outputs: list[str] | None = None,
                         next_step: str = "") -> bool:
    """Update an existing action's status by rewriting the line (append new version)."""
    records = _load_records()
    target = next((a for a in records if a.action_id == action_id), None)
    if not target:
        return False
    target.status = status
    target.updated_at = datetime.now(timezone.utc).isoformat()
    if artifact_outputs:
        target.artifact_outputs = artifact_outputs
    if next_step:
        target.next_step = next_step
    _save_record(target)
    return True


def get_open_actions() -> list[Action]:
    """Return actions that are not completed or failed."""
    records = _load_records()
    open_statuses = {"proposed", "queued", "assigned", "in_progress", "needs_ray_approval", "blocked"}
    # Deduplicate by action_id — keep latest version
    seen: dict[str, Action] = {}
    for a in records:
        seen[a.action_id] = a  # last write wins
    return [a for a in seen.values() if a.status in open_statuses]


def get_blocked_actions() -> list[Action]:
    open_actions = get_open_actions()
    return [a for a in open_actions if a.status == "blocked"]


def get_pending_approval_actions() -> list[Action]:
    open_actions = get_open_actions()
    return [a for a in open_actions if a.status == "needs_ray_approval"]


def top_priority_actions(limit: int = 5) -> list[Action]:
    open_actions = get_open_actions()
    ready = [a for a in open_actions
             if a.status in ("proposed", "queued", "assigned") and a.autonomous_allowed]
    return sorted(ready, key=lambda a: -a.priority)[:limit]


def normalize_action_title(title: str) -> str:
    """Normalize a title for deduplication. Strips status prefixes and bracket annotations."""
    import re
    t = (title or "").strip()
    # Remove leading [status] bracket annotations like "[product_candidate] ..."
    t = re.sub(r"^\[[^\]]+\]\s*", "", t)
    # Remove leading status labels like "Status: X — "
    t = re.sub(r"^Status:\s*\w+\s*[—–]\s*", "", t)
    # Collapse whitespace, lowercase for comparison
    return " ".join(t.lower().split())


def action_dedupe_key(action: "Action") -> tuple:
    """Return a key that identifies duplicate actions (same work, different record)."""
    return (normalize_action_title(action.title), action.goal_id, action.assigned_scout)


def get_unique_open_actions() -> list["Action"]:
    """Return open actions deduplicated by (normalized_title, goal_id, assigned_scout)."""
    open_actions = get_open_actions()
    seen: dict[tuple, "Action"] = {}
    for a in sorted(open_actions, key=lambda x: -x.priority):
        key = action_dedupe_key(a)
        if key not in seen:
            seen[key] = a
    return list(seen.values())


def format_action_queue_summary_common_language() -> str:
    """Plain-language action queue with deduplicated unique actions."""
    all_open = get_open_actions()
    unique = get_unique_open_actions()
    dup_count = len(all_open) - len(unique)

    blocked = [a for a in unique if a.status == "blocked"]
    approval_needed = [a for a in unique if a.status == "needs_ray_approval"]
    in_progress = [a for a in unique if a.status == "in_progress"]
    ready = sorted(
        [a for a in unique if a.status in ("proposed", "queued", "assigned")],
        key=lambda x: -x.priority,
    )

    lines = ["ACTION QUEUE", ""]
    if dup_count > 0:
        lines.append(
            f"I have {len(all_open)} open action records, but {dup_count} are duplicates. "
            f"The top {min(5, len(unique))} unique actions are:"
        )
    else:
        lines.append(f"I have {len(unique)} unique open actions. Top actions:")

    lines.append("")
    shown = 0
    for group in [in_progress, ready]:
        for a in group:
            if shown >= 5:
                break
            shown += 1
            display_title = normalize_action_title(a.title) or a.title
            # Title-case for readability
            display_title = display_title[:80]
            scout_tag = f"\n   Scout: {a.assigned_scout}" if a.assigned_scout else ""
            next_tag = f"\n   Next: {a.next_step}" if a.next_step else ""
            status_label = {
                "in_progress": "in progress", "queued": "ready",
                "assigned": "assigned", "proposed": "proposed",
            }.get(a.status, a.status)
            lines.append(f"{shown}. {display_title}")
            lines.append(f"   Status: {status_label}{scout_tag}{next_tag}")
            lines.append("")

    if blocked:
        lines.append(f"Blocked ({len(blocked)}) — need Ray to unblock:")
        for a in blocked[:3]:
            lines.append(f"  🔴 {a.title}")
        lines.append("")
    if approval_needed:
        lines.append(f"Waiting for approval ({len(approval_needed)}):")
        for a in approval_needed[:3]:
            lines.append(f"  ⏳ {a.title}")
        lines.append("")
    if dup_count > 0:
        lines.append(f"Duplicates suppressed: {dup_count} repeated operating-loop actions.")
        lines.append("")
    try:
        src = _QUEUE_JSONL.relative_to(_ROOT)
    except ValueError:
        src = _QUEUE_JSONL
    lines.append(f"Evidence: {src}")
    return "\n".join(lines)


def action_queue_plain_english() -> str:
    return format_action_queue_summary_common_language()


def get_open_action_by_title(normalized_title: str) -> "Action | None":
    """Return existing open action matching a normalized title, or None."""
    for a in get_unique_open_actions():
        if normalize_action_title(a.title) == normalized_title:
            return a
    return None


def write_latest_markdown() -> None:
    open_actions = get_open_actions()
    lines = [
        "# Hermes Action Queue",
        f"*Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        f"\n**{len(open_actions)} open actions**\n",
    ]
    for a in sorted(open_actions, key=lambda x: -x.priority):
        lines.append(a.to_plain_english())
        lines.append("")
    _QUEUE_MD.parent.mkdir(parents=True, exist_ok=True)
    _QUEUE_MD.write_text("\n".join(lines))
