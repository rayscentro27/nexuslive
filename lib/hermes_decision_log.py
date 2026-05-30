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


_GENERIC_DECISION_PREFIXES = (
    "propose action: run operating loop",
    "propose action: run provider policy",
    "[dry run] propose action",
)


def _decision_is_meaningful(d: "Decision") -> bool:
    """Return True if this decision is worth showing (not a generic loop iteration)."""
    dec_lower = (d.decision or "").lower()
    return not any(dec_lower.startswith(p) for p in _GENERIC_DECISION_PREFIXES)


_STATUS_TO_LABEL = {
    "content_candidate": "Selected as content candidate",
    "product_candidate": "Selected as product opportunity",
    "affiliate_candidate": "Selected for affiliate research",
    "client_education_candidate": "Selected for client education content",
    "needs_more_research": "Flagged for deeper research",
    "rejected": "Rejected",
    "watch": "Added to watch list",
    "high_priority": "Marked high priority",
}


def _format_decision_human(d: "Decision", index: int) -> list[str]:
    """Format one decision as a plain-language item with index."""
    ts = (d.timestamp or "")[:10]
    dec = (d.decision or "").strip()
    trigger = (d.question_or_trigger or "").strip()
    why = (d.why_selected or "").strip()

    # Strip internal routing instructions
    for prefix in ("Status: ", "Propose action: "):
        if dec.startswith(prefix):
            dec = dec[len(prefix):]

    # Strip trailing routing suffix like " — Route to content_intelligence_scout..."
    for marker in [" — Route to ", " — Assign to ", " — route to "]:
        idx = dec.find(marker)
        if idx > 0:
            dec = dec[:idx].strip()

    # Convert bare status codes to human labels
    dec_lower = dec.lower().replace("-", "_").replace(" ", "_")
    if dec_lower in _STATUS_TO_LABEL:
        # Try to attach the source name from the trigger
        if "score intake source:" in trigger.lower():
            source = trigger[trigger.lower().find("score intake source:") + len("score intake source:"):].strip()
            dec = f"{_STATUS_TO_LABEL[dec_lower]}: {source[:55]}"
        else:
            dec = _STATUS_TO_LABEL[dec_lower]

    # Simplify trigger labels
    if "score intake source:" in trigger.lower():
        source = trigger[trigger.lower().find("score intake source:") + len("score intake source:"):].strip()
        trigger = f"Scored: {source[:55]}"
    elif trigger.lower().startswith("operating loop"):
        trigger = "Operating loop run"

    lines = [f"{index}. {dec[:90]}"]
    lines.append(f"   When: {ts} — {trigger[:65]}")
    if why:
        lines.append(f"   Why: {why[:90]}")
    if d.action_created:
        lines.append(f"   Action: {d.action_created}")
    if d.artifact_paths:
        lines.append(f"   Evidence: {d.artifact_paths[0]}")
    return lines


def decision_log_plain_english(limit: int = 10) -> str:
    all_decisions = load_recent_decisions(100)
    if not all_decisions:
        return (
            "DECISION LOG\n\n"
            "No decisions recorded yet.\n"
            "Hermes logs a decision every time it selects an action, assigns a scout, "
            "or routes a request.\n\n"
            "Run: 'Hermes, continue research while I am out' to generate the first decisions.\n"
            f"Source: {_LOG_JSONL.relative_to(_ROOT)}"
        )

    # Prefer meaningful decisions; fall back to all if too few
    meaningful = [d for d in all_decisions if _decision_is_meaningful(d)]
    shown = meaningful[:limit] if len(meaningful) >= 3 else all_decisions[:limit]

    lines = ["DECISION LOG", "", f"Recent Hermes decisions ({len(shown)} shown):", ""]
    for i, d in enumerate(shown, 1):
        lines.extend(_format_decision_human(d, i))
        lines.append("")

    if len(all_decisions) > len(shown):
        lines.append(f"({len(all_decisions) - len(shown)} routine loop decisions not shown.)")
        lines.append("")

    lines.append("Say 'show approval policy' to see what Hermes can and cannot do autonomously.")
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
