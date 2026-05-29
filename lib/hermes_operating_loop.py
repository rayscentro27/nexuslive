"""
hermes_operating_loop.py
=========================
The Hermes operating loop. Turns goals + intake + tools into action.

Process:
  1. Load goals
  2. Load tool/scout registry
  3. Load source intake queue
  4. Load artifact registry
  5. Load open actions
  6. Identify blockers
  7. Select top 3 next actions
  8. Assign scouts/workers if safe
  9. Create handoffs if needed
  10. Log decisions
  11. Update action queue
  12. Produce Telegram-ready digest in common language

Modes: validation, daily, continue, digest-only
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_OUT_DIR = _ROOT / "docs" / "reports" / "operations"


@dataclass
class LoopResult:
    mode: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    goals_loaded: int = 0
    tools_loaded: int = 0
    intake_pending: int = 0
    open_actions: int = 0
    blocked_actions: int = 0
    actions_created: list[str] = field(default_factory=list)
    decisions_logged: list[str] = field(default_factory=list)
    scouts_assigned: list[str] = field(default_factory=list)
    approval_requests: list[str] = field(default_factory=list)
    digest: str = ""
    artifact_path: str = ""

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "timestamp": self.timestamp,
            "goals_loaded": self.goals_loaded,
            "tools_loaded": self.tools_loaded,
            "intake_pending": self.intake_pending,
            "open_actions": self.open_actions,
            "blocked_actions": self.blocked_actions,
            "actions_created": self.actions_created,
            "decisions_logged": self.decisions_logged,
            "scouts_assigned": self.scouts_assigned,
            "approval_requests": self.approval_requests,
            "artifact_path": self.artifact_path,
        }


def run_operating_loop(
    mode: str = "validation",
    max_actions: int = 5,
    dry_run: bool = True,
) -> LoopResult:
    """
    Run the Hermes operating loop.

    Args:
        mode: validation | daily | continue | digest-only
        max_actions: max actions to create or assign
        dry_run: if True, log decisions but do not create real tasks

    Returns:
        LoopResult with what was done and a plain-language digest
    """
    result = LoopResult(mode=mode)

    # 1. Load goals
    try:
        from lib.hermes_goal_registry import load_goals, top_active_goals
        goals = load_goals()
        result.goals_loaded = len(goals)
        top_goals = top_active_goals(limit=3)
    except Exception as exc:
        top_goals = []
        result.goals_loaded = 0

    # 2. Load tool/scout registry
    try:
        from lib.hermes_tool_scout_registry import load_registry, get_scouts
        tools = load_registry()
        result.tools_loaded = len(tools)
        scouts = get_scouts()
    except Exception:
        tools = []
        scouts = []
        result.tools_loaded = 0

    # 3. Load source intake queue (pending items)
    intake_records: list[dict] = []
    try:
        intake_log = _ROOT / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
        if intake_log.exists():
            lines = intake_log.read_text().splitlines()
            for line in lines[-50:]:
                if line.strip():
                    try:
                        r = json.loads(line)
                        if r.get("status") in ("pending", "queued", None):
                            intake_records.append(r)
                    except Exception:
                        pass
        result.intake_pending = len(intake_records)
    except Exception:
        pass

    # 4. Load artifact inventory
    artifact_count = 0
    try:
        for rel in ["docs/reports/evidence", "docs/reports/handoffs", "docs/reports/intake"]:
            p = _ROOT / rel
            if p.exists():
                artifact_count += len(list(p.iterdir()))
    except Exception:
        pass

    # 5. Load open actions
    try:
        from lib.hermes_action_queue import get_open_actions, get_blocked_actions
        open_actions = get_open_actions()
        result.open_actions = len(open_actions)
        result.blocked_actions = len(get_blocked_actions())
    except Exception:
        open_actions = []

    # 6. Select top 3 next actions to propose
    proposed_actions: list[dict] = []

    # Action: Process pending intake records
    if intake_records and len(proposed_actions) < max_actions:
        sample = intake_records[:3]
        for record in sample:
            url = str(record.get("url", ""))[:60]
            proposed_actions.append({
                "title": f"Process intake: {url}",
                "description": f"Assign {url} to appropriate scout for analysis",
                "scout": _route_intake_to_scout(url, scouts),
                "goal_id": "goal_content_engine",
                "autonomous_allowed": True,
                "priority": 70,
            })

    # Action: Based on top goals
    for goal in top_goals[:2]:
        if len(proposed_actions) >= max_actions:
            break
        if goal.next_action:
            proposed_actions.append({
                "title": goal.next_action,
                "description": f"Goal: {goal.title}",
                "scout": "",
                "goal_id": goal.goal_id,
                "autonomous_allowed": goal.autonomous_allowed,
                "priority": goal.priority,
            })

    # 7. Create or propose actions (dry_run = just log)
    from lib.hermes_decision_log import log_decision
    from lib.hermes_action_queue import create_action

    for pa in proposed_actions[:max_actions]:
        if dry_run:
            result.actions_created.append(f"[DRY RUN] {pa['title']}")
        else:
            action = create_action(
                title=pa["title"],
                description=pa.get("description", ""),
                goal_id=pa.get("goal_id", ""),
                assigned_scout=pa.get("scout", ""),
                priority=pa.get("priority", 50),
                autonomous_allowed=pa.get("autonomous_allowed", True),
                status="queued",
            )
            result.actions_created.append(action.action_id)

        # Log decision
        dec = log_decision(
            question_or_trigger=f"Operating loop ({mode}) — evaluating next action",
            decision=f"Propose action: {pa['title']}",
            why_selected=f"Aligned with goal '{pa.get('goal_id','')}', priority {pa.get('priority',50)}",
            goal_alignment=pa.get("goal_id", ""),
            risk_level="low",
            autonomous_allowed=pa.get("autonomous_allowed", True),
        )
        result.decisions_logged.append(dec.decision_id)

        if pa.get("scout"):
            result.scouts_assigned.append(f"{pa['scout']} → {pa['title'][:40]}")

    # 8. Build plain-language digest
    result.digest = _build_digest(result, top_goals, intake_records, artifact_count, dry_run)

    # 9. Write artifact
    result.artifact_path = _write_artifact(result)

    return result


def _route_intake_to_scout(url: str, scouts: list) -> str:
    url_lower = url.lower()
    if "youtube" in url_lower or "youtu.be" in url_lower:
        return "youtube_research_scout"
    if "github.com" in url_lower:
        return "github_trend_scout"
    return "content_intelligence_scout"


def _build_digest(
    result: LoopResult,
    top_goals: list,
    intake_records: list,
    artifact_count: int,
    dry_run: bool,
) -> str:
    mode_label = "Validation run" if result.mode == "validation" else f"Operating loop ({result.mode})"
    dry_note = " (dry-run — no real tasks created)" if dry_run else ""

    lines = [
        f"**{mode_label}**{dry_note}",
        "",
        f"Here is what Hermes found:",
        f"  • {result.goals_loaded} active goals loaded",
        f"  • {result.tools_loaded} tools/scouts registered",
        f"  • {result.intake_pending} intake records pending processing",
        f"  • {artifact_count} artifacts in evidence directories",
        f"  • {result.open_actions} open actions ({result.blocked_actions} blocked)",
        "",
    ]

    if top_goals:
        lines.append("Top 3 priorities right now:")
        for g in top_goals[:3]:
            lines.append(f"  {g.title} (priority {g.priority})")
            if g.next_action:
                lines.append(f"    → {g.next_action}")
        lines.append("")

    if result.actions_created:
        lines.append(f"Actions proposed this run ({len(result.actions_created)}):")
        for a in result.actions_created[:5]:
            lines.append(f"  • {a}")
        lines.append("")

    if result.scouts_assigned:
        lines.append("Scouts assigned:")
        for s in result.scouts_assigned[:3]:
            lines.append(f"  • {s}")
        lines.append("")

    if result.approval_requests:
        lines.append("⏳ Waiting for Ray approval:")
        for r in result.approval_requests:
            lines.append(f"  • {r}")
        lines.append("")

    lines.append("Ask Hermes: 'show action queue', 'show decision log', 'what should we work on today'")
    return "\n".join(lines)


def _write_artifact(result: LoopResult) -> str:
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = _OUT_DIR / f"hermes_operating_loop_{ts}.json"
    md_path = _OUT_DIR / f"hermes_operating_loop_{ts}.md"

    json_path.write_text(json.dumps(result.to_dict(), indent=2))
    md_path.write_text(
        f"# Hermes Operating Loop — {result.mode}\n"
        f"*{result.timestamp}*\n\n"
        + result.digest
    )
    return str(md_path.relative_to(_ROOT))
