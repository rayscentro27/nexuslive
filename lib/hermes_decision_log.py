"""
hermes_decision_log.py
=======================
Hermes decision recorder. Every significant Hermes decision is logged here.

Hermes logs decisions for:
  - What to work on today
  - Which opportunity to pursue
  - Which scout to assign
  - Which source to reject
  - Which strategy to test
  - Which blocker/fallback to use
  - What requires Ray approval

Stored in:
  docs/reports/decisions/hermes_decision_log.jsonl  — append-only log
  docs/reports/decisions/hermes_decision_log_latest.md  — plain-language summary
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

_ROOT = Path(__file__).resolve().parent.parent
_LOG_JSONL = _ROOT / "docs" / "reports" / "decisions" / "hermes_decision_log.jsonl"
_LOG_MD = _ROOT / "docs" / "reports" / "decisions" / "hermes_decision_log_latest.md"
_MAX_LOAD = 100

RiskLevel = Literal["low", "medium", "high", "requires_approval"]


@dataclass
class Decision:
    decision_id: str = field(default_factory=lambda: f"dec_{uuid.uuid4().hex[:10]}")
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    question_or_trigger: str = ""
    decision: str = ""
    evidence_used: list[str] = field(default_factory=list)
    goal_alignment: str = ""
    options_considered: list[str] = field(default_factory=list)
    why_selected: str = ""
    risk_level: RiskLevel = "low"
    autonomous_allowed: bool = True
    requires_ray_approval: bool = False
    action_created: str = ""  # action_id if action was created
    artifact_paths: list[str] = field(default_factory=list)
    result_status: str = "pending"  # pending, completed, failed, cancelled

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        ts = self.timestamp[:10]
        risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴",
                      "requires_approval": "⏳"}.get(self.risk_level, "⚪")
        lines = [
            f"{risk_emoji} [{ts}] **{self.decision[:80]}**",
            f"   Trigger: {self.question_or_trigger[:80]}",
            f"   Why: {self.why_selected[:80]}",
        ]
        if self.artifact_paths:
            lines.append(f"   Evidence: {self.artifact_paths[0]}")
        if self.requires_ray_approval:
            lines.append(f"   ⏳ Requires Ray approval")
        return "\n".join(lines)


def log_decision(
    question_or_trigger: str,
    decision: str,
    why_selected: str = "",
    evidence_used: list[str] | None = None,
    options_considered: list[str] | None = None,
    goal_alignment: str = "",
    risk_level: RiskLevel = "low",
    autonomous_allowed: bool = True,
    requires_ray_approval: bool = False,
    action_created: str = "",
    artifact_paths: list[str] | None = None,
    result_status: str = "pending",
) -> Decision:
    """Record a Hermes decision. Returns the Decision object."""
    d = Decision(
        question_or_trigger=question_or_trigger,
        decision=decision,
        why_selected=why_selected,
        evidence_used=evidence_used or [],
        options_considered=options_considered or [],
        goal_alignment=goal_alignment,
        risk_level=risk_level,
        autonomous_allowed=autonomous_allowed,
        requires_ray_approval=requires_ray_approval,
        action_created=action_created,
        artifact_paths=artifact_paths or [],
        result_status=result_status,
    )
    _LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_JSONL, "a") as f:
        f.write(json.dumps(d.to_dict()) + "\n")
    return d


def load_recent_decisions(limit: int = 20) -> list[Decision]:
    if not _LOG_JSONL.exists():
        return []
    try:
        lines = _LOG_JSONL.read_text().splitlines()
        records = []
        for line in lines[-limit:]:
            if line.strip():
                d = json.loads(line)
                records.append(Decision(**{k: v for k, v in d.items()
                                           if k in Decision.__dataclass_fields__}))
        return list(reversed(records))  # most recent first
    except Exception:
        return []


def decision_log_plain_english(limit: int = 10) -> str:
    decisions = load_recent_decisions(limit)
    if not decisions:
        return (
            "No decisions recorded yet.\n"
            "Hermes logs a decision every time it selects an action, assigns a scout, "
            "or routes a request.\n"
            f"Source: {_LOG_JSONL.relative_to(_ROOT)}"
        )
    lines = [
        f"Recent Hermes decisions ({len(decisions)} shown):",
        "",
    ]
    for d in decisions[:limit]:
        lines.append(d.to_plain_english())
        lines.append("")
    try:
        src = _LOG_JSONL.relative_to(_ROOT)
    except ValueError:
        src = _LOG_JSONL
    lines.append(f"Source: {src}")
    return "\n".join(lines)


def write_latest_markdown(limit: int = 50) -> None:
    decisions = load_recent_decisions(limit)
    lines = [
        "# Hermes Decision Log",
        f"*Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        f"\n**{len(decisions)} recent decisions**\n",
    ]
    for d in decisions:
        lines.append(d.to_plain_english())
        lines.append("")
    _LOG_MD.parent.mkdir(parents=True, exist_ok=True)
    _LOG_MD.write_text("\n".join(lines))
