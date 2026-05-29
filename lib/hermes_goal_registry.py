"""
hermes_goal_registry.py
========================
Hermes live goal system. Tracks what Nexus is trying to accomplish,
success criteria, status, and required evidence.

Goals are stored in:
  docs/reports/goals/hermes_goal_registry.json  — machine-readable
  docs/reports/goals/hermes_goal_registry_latest.md  — human-readable
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_JSON = _ROOT / "docs" / "reports" / "goals" / "hermes_goal_registry.json"
_REGISTRY_MD = _ROOT / "docs" / "reports" / "goals" / "hermes_goal_registry_latest.md"

GoalStatus = Literal[
    "active", "paused", "blocked", "completed", "cancelled",
]

GoalCategory = Literal[
    "revenue_30_day", "content_engine", "credit_funding_education",
    "trading_education", "nexus_reliability", "monetization_intelligence",
    "other",
]


@dataclass
class Goal:
    goal_id: str
    title: str
    category: GoalCategory
    description: str
    success_criteria: list[str] = field(default_factory=list)
    current_status: GoalStatus = "active"
    priority: int = 50  # 1-100, higher = more urgent
    owner: str = "ray_davis"
    evidence_required: list[str] = field(default_factory=list)
    related_artifacts: list[str] = field(default_factory=list)
    next_action: str = ""
    autonomous_allowed: bool = True
    requires_ray_approval: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        status_emoji = {"active": "🟢", "paused": "⏸️", "blocked": "🔴",
                        "completed": "✅", "cancelled": "❌"}.get(self.current_status, "⚪")
        lines = [
            f"{status_emoji} **{self.title}** (priority {self.priority})",
            f"   Status: {self.current_status}",
        ]
        if self.success_criteria:
            lines.append(f"   Goal: {self.success_criteria[0]}")
        if self.next_action:
            lines.append(f"   Next: {self.next_action}")
        if self.requires_ray_approval:
            lines.append(f"   Needs approval for: {', '.join(self.requires_ray_approval[:2])}")
        return "\n".join(lines)


def _default_goals() -> list[Goal]:
    return [
        Goal(
            goal_id="goal_revenue_30day",
            title="30-Day Revenue Goal",
            category="revenue_30_day",
            description="Produce first monetizable outputs within 30 days",
            success_criteria=[
                "Produce finished products Ray can critique",
                "Identify fastest ethical revenue path",
                "Avoid paid tools unless approved",
                "Avoid public publishing unless approved",
            ],
            priority=95,
            next_action="Run operating loop to identify top revenue action this week",
            autonomous_allowed=True,
            requires_ray_approval=["public publishing", "paid tools", "billing clients"],
        ),
        Goal(
            goal_id="goal_content_engine",
            title="Content Engine Goal",
            category="content_engine",
            description="Convert YouTube/social/research into scripts, newsletters, posts, and offers",
            success_criteria=[
                "Generate reviewable content artifacts from registered sources",
                "Track what works and what fails",
                "Produce draft content for Ray review",
            ],
            priority=80,
            next_action="Process registered YouTube sources through content scout",
            autonomous_allowed=True,
            requires_ray_approval=["public publishing", "client distribution"],
        ),
        Goal(
            goal_id="goal_credit_funding_edu",
            title="Credit/Funding Education Goal",
            category="credit_funding_education",
            description="Create safe education around funding readiness, business credit, credit repair",
            success_criteria=[
                "Build compliance-checked educational content",
                "Reference verified sources only",
                "No client-facing content without compliance review",
            ],
            priority=70,
            next_action="Review registered funding research sources for content creation",
            autonomous_allowed=True,
            requires_ray_approval=["public/client use of content", "compliance review"],
        ),
        Goal(
            goal_id="goal_trading_education",
            title="Trading Education / Demo Strategy Goal",
            category="trading_education",
            description="Backtest strategies, demo/paper test safely under caps",
            success_criteria=[
                "Run backtests on verified strategies",
                "OANDA practice under caps only",
                "No live/funded trading without approval",
                "Education artifacts only",
            ],
            priority=65,
            next_action="Review vibe-trading backtest results and identify next strategy to test",
            autonomous_allowed=True,
            requires_ray_approval=["live trading", "funded broker", "live account"],
        ),
        Goal(
            goal_id="goal_nexus_reliability",
            title="Nexus Reliability Goal",
            category="nexus_reliability",
            description="Keep Hermes stable, evidence-gated, no fake claims",
            success_criteria=[
                "Hermes always answers from evidence",
                "Source intake works reliably",
                "Scout dispatch works",
                "No demo responses or fake claims",
                "Provider failure does not break Telegram",
            ],
            priority=90,
            next_action="Run provider policy check and verify source intake pipeline",
            autonomous_allowed=True,
            requires_ray_approval=[],
        ),
        Goal(
            goal_id="goal_monetization_intelligence",
            title="Monetization Intelligence Goal",
            category="monetization_intelligence",
            description="Discover opportunities from YouTube, social, GitHub, affiliates",
            success_criteria=[
                "Score opportunities against Nexus goals",
                "Turn top opportunities into action packets",
                "Surface opportunities that fit zero/low-cost approach",
            ],
            priority=75,
            next_action="Run monetization scout on registered YouTube sources",
            autonomous_allowed=True,
            requires_ray_approval=["paid affiliate spend", "buying courses/tools"],
        ),
    ]


def load_goals() -> list[Goal]:
    """Load goals from registry JSON, or return defaults if not found."""
    if _REGISTRY_JSON.exists():
        try:
            data = json.loads(_REGISTRY_JSON.read_text())
            goals = []
            for g in (data if isinstance(data, list) else data.get("goals", [])):
                goals.append(Goal(**{k: v for k, v in g.items()
                                     if k in Goal.__dataclass_fields__}))
            return goals
        except Exception:
            pass
    return _default_goals()


def save_goals(goals: list[Goal]) -> None:
    """Persist goals to JSON and markdown."""
    _REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_JSON.write_text(json.dumps([g.to_dict() for g in goals], indent=2))
    _write_markdown(goals)


def _write_markdown(goals: list[Goal]) -> None:
    active = [g for g in goals if g.current_status == "active"]
    blocked = [g for g in goals if g.current_status == "blocked"]
    lines = [
        "# Hermes Goal Registry",
        f"*Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        f"**{len(active)} active goals | {len(blocked)} blocked | {len(goals)} total**",
        "",
        "## Active Goals (by priority)",
    ]
    for g in sorted(active, key=lambda x: -x.priority):
        lines.append("")
        lines.append(g.to_plain_english())
    if blocked:
        lines.append("\n## Blocked Goals")
        for g in blocked:
            lines.append(g.to_plain_english())
    _REGISTRY_MD.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_MD.write_text("\n".join(lines))


def get_goal(goal_id: str) -> Goal | None:
    goals = load_goals()
    return next((g for g in goals if g.goal_id == goal_id), None)


def upsert_goal(goal: Goal) -> None:
    goals = load_goals()
    idx = next((i for i, g in enumerate(goals) if g.goal_id == goal.goal_id), None)
    goal.updated_at = datetime.now(timezone.utc).isoformat()
    if idx is not None:
        goals[idx] = goal
    else:
        goals.append(goal)
    save_goals(goals)


def top_active_goals(limit: int = 3) -> list[Goal]:
    goals = load_goals()
    active = [g for g in goals if g.current_status == "active"]
    return sorted(active, key=lambda g: -g.priority)[:limit]


def goals_summary_plain_english() -> str:
    goals = load_goals()
    active = [g for g in goals if g.current_status == "active"]
    blocked = [g for g in goals if g.current_status == "blocked"]
    top = sorted(active, key=lambda g: -g.priority)[:3]

    lines = [
        f"Nexus has {len(active)} active goals.",
        "",
        "Top priorities right now:",
    ]
    for g in top:
        lines.append(f"  • {g.title} (priority {g.priority})")
        if g.next_action:
            lines.append(f"    Next: {g.next_action}")
    if blocked:
        lines.append(f"\n{len(blocked)} goal(s) blocked — run 'show action queue' to see blockers.")
    lines.append(f"\nSource: {_REGISTRY_JSON.relative_to(_ROOT)}")
    return "\n".join(lines)


def initialize_registry() -> None:
    """Create the default registry if it does not exist."""
    if not _REGISTRY_JSON.exists():
        goals = _default_goals()
        save_goals(goals)
