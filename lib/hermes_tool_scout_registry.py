"""
hermes_tool_scout_registry.py
================================
Registry of all tools, scouts, agents, and systems available to Hermes.

Hermes uses this when deciding:
  - Which scout handles a YouTube link
  - Which worker handles a coding task
  - Which system processes a trading idea
  - Which tasks require Ray approval
  - Whether a tool is available or missing

Stored in:
  docs/reports/core/hermes_tool_scout_registry.json
  docs/reports/core/hermes_tool_scout_registry_latest.md
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_REGISTRY_JSON = _ROOT / "docs" / "reports" / "core" / "hermes_tool_scout_registry.json"
_REGISTRY_MD = _ROOT / "docs" / "reports" / "core" / "hermes_tool_scout_registry_latest.md"


@dataclass
class ToolOrScout:
    id: str
    name: str
    type: str  # "core_memory", "agent", "scout", "system"
    purpose: str
    input_types: list[str] = field(default_factory=list)
    output_artifacts: list[str] = field(default_factory=list)
    autonomous_allowed: bool = True
    requires_ray_approval: list[str] = field(default_factory=list)
    current_status: str = "available"  # available, unavailable, experimental, missing
    command_or_handler: str = ""
    fallback: str = "evidence_only"
    failure_mode: str = "log and continue"
    evidence_path: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_plain_english(self) -> str:
        icon = {"available": "✅", "unavailable": "❌", "experimental": "⚠️",
                "missing": "❓"}.get(self.current_status, "⚪")
        return f"  {icon} **{self.name}** — {self.purpose}"


def _build_default_registry() -> list[ToolOrScout]:
    return [
        # ── Core memory / tools ────────────────────────────────────────────────
        ToolOrScout(
            id="artifact_registry",
            name="Artifact Registry",
            type="core_memory",
            purpose="Track all generated artifacts with metadata",
            input_types=["any artifact"],
            output_artifacts=["docs/reports/artifact_registry/"],
            command_or_handler="lib/hermes_artifact_memory.py",
            evidence_path="docs/reports/artifact_registry/",
        ),
        ToolOrScout(
            id="source_intake_registry",
            name="Source Intake Registry",
            type="core_memory",
            purpose="Register URLs, links, and source content sent by Ray",
            input_types=["url", "youtube_url", "github_url", "text"],
            output_artifacts=["docs/reports/intake/telegram_source_intake.jsonl"],
            command_or_handler="lib/hermes_telegram_source_intake.py",
            evidence_path="docs/reports/intake/",
        ),
        ToolOrScout(
            id="youtube_source_registry",
            name="YouTube Source Registry",
            type="core_memory",
            purpose="Track registered YouTube channels and videos",
            input_types=["youtube_url"],
            output_artifacts=["docs/reports/intake/"],
            command_or_handler="lib/hermes_telegram_source_intake.py",
            evidence_path="docs/reports/intake/",
        ),
        ToolOrScout(
            id="goal_registry",
            name="Goal Registry",
            type="core_memory",
            purpose="Track Nexus goals, priorities, and success criteria",
            input_types=["goal_definition"],
            output_artifacts=["docs/reports/goals/hermes_goal_registry.json",
                              "docs/reports/goals/hermes_goal_registry_latest.md"],
            command_or_handler="lib/hermes_goal_registry.py",
            evidence_path="docs/reports/goals/",
        ),
        ToolOrScout(
            id="action_queue",
            name="Action Queue",
            type="core_memory",
            purpose="Track all actions Hermes has created, assigned, or completed",
            input_types=["goal", "intake", "opportunity"],
            output_artifacts=["docs/reports/actions/hermes_action_queue.jsonl"],
            command_or_handler="lib/hermes_action_queue.py",
            evidence_path="docs/reports/actions/",
        ),
        ToolOrScout(
            id="decision_log",
            name="Decision Log",
            type="core_memory",
            purpose="Record every Hermes decision with evidence and reasoning",
            input_types=["decision_event"],
            output_artifacts=["docs/reports/decisions/hermes_decision_log.jsonl"],
            command_or_handler="lib/hermes_decision_log.py",
            evidence_path="docs/reports/decisions/",
        ),
        ToolOrScout(
            id="context_pack_builder",
            name="Context Pack Builder",
            type="core_memory",
            purpose="Build compact evidence packs for LLM providers (≤2500 tokens for local models)",
            input_types=["question"],
            output_artifacts=["in-memory ContextPack"],
            command_or_handler="lib/hermes_context_pack_builder.py",
        ),
        ToolOrScout(
            id="final_response_gate",
            name="Final Response Gate",
            type="core_memory",
            purpose="Block fabricated data, raw tool call leaks, and fake metrics before Telegram delivery",
            input_types=["response_text"],
            output_artifacts=["blocked or passed"],
            command_or_handler="lib/hermes_final_response_gate.py",
        ),
        ToolOrScout(
            id="handoff_registry",
            name="Claude Code Handoff Registry",
            type="core_memory",
            purpose="Track Claude Code session outputs and what was built",
            input_types=["session_output"],
            output_artifacts=["docs/reports/handoffs/"],
            evidence_path="docs/reports/handoffs/",
        ),
        # ── Agents / workers ───────────────────────────────────────────────────
        ToolOrScout(
            id="claude_code",
            name="Claude Code",
            type="agent",
            purpose="Build, fix, and implement code tasks assigned by Hermes",
            input_types=["handoff_file", "task_record", "instruction"],
            output_artifacts=["code changes", "docs/reports/handoffs/"],
            autonomous_allowed=True,
            requires_ray_approval=["deploy to production", "paid services"],
            command_or_handler="claude (CLI)",
            failure_mode="log failure, create blocker",
        ),
        ToolOrScout(
            id="codex_agent",
            name="Codex Agent",
            type="agent",
            purpose="AI coding sessions via Codex CLI",
            input_types=["task_file", "instruction"],
            output_artifacts=["code changes", "completion summaries"],
            autonomous_allowed=True,
            command_or_handler="codex (CLI)",
            current_status="experimental",
        ),
        ToolOrScout(
            id="hermes_gateway",
            name="Hermes Gateway",
            type="agent",
            purpose="Strategic conversation via local Hermes API at :8642",
            input_types=["question", "evidence_pack"],
            output_artifacts=["reply"],
            autonomous_allowed=True,
            current_status="experimental",
            command_or_handler="HERMES_ALLOW_HERMES_GATEWAY=true",
            failure_mode="fall back to local_ollama",
        ),
        ToolOrScout(
            id="local_ollama",
            name="Local Ollama",
            type="agent",
            purpose="Local LLM reasoning (qwen3:8b or configured model)",
            input_types=["compact_context_pack", "question"],
            output_artifacts=["reply"],
            autonomous_allowed=True,
            command_or_handler="OLLAMA_HOST=http://localhost:11434",
            failure_mode="fall back to evidence_only",
        ),
        ToolOrScout(
            id="evidence_only_mode",
            name="Evidence-Only Mode",
            type="agent",
            purpose="Always-available fallback — answers from verified artifacts with no LLM",
            input_types=["context_pack"],
            output_artifacts=["formatted_reply"],
            autonomous_allowed=True,
            command_or_handler="lib/hermes_evidence_summary_formatter.py",
            failure_mode="never fails",
        ),
        # ── Scouts ─────────────────────────────────────────────────────────────
        ToolOrScout(
            id="youtube_research_scout",
            name="YouTube Research Scout",
            type="scout",
            purpose="Extract transcript insights, content ideas, and monetization angles from YouTube videos",
            input_types=["youtube_url"],
            output_artifacts=["docs/reports/intake/", "artifacts/youtube_intel/"],
            command_or_handler="lib/youtube_intelligence_worker.py",
            evidence_path="docs/reports/intake/",
        ),
        ToolOrScout(
            id="content_intelligence_scout",
            name="Content Intelligence Scout",
            type="scout",
            purpose="Turn research into draft scripts, newsletters, and social posts",
            input_types=["transcript", "intake_record", "goal"],
            output_artifacts=["docs/content/", "artifacts/content/"],
            autonomous_allowed=True,
            requires_ray_approval=["publishing publicly"],
        ),
        ToolOrScout(
            id="monetization_scout",
            name="Monetization Scout",
            type="scout",
            purpose="Discover and score monetization opportunities from sources and goals",
            input_types=["intake_record", "youtube_intel", "research"],
            output_artifacts=["docs/reports/monetization/", "artifacts/opportunities/"],
            command_or_handler="lib/opportunity_analyzer.py",
        ),
        ToolOrScout(
            id="credit_repair_research_scout",
            name="Credit Repair Research Scout",
            type="scout",
            purpose="Research credit repair strategies from registered sources",
            input_types=["youtube_url", "research_link"],
            output_artifacts=["artifacts/credit_research/"],
            requires_ray_approval=["client-facing content"],
        ),
        ToolOrScout(
            id="funding_readiness_scout",
            name="Funding Readiness Scout",
            type="scout",
            purpose="Assess funding readiness and track grant/funding intelligence",
            input_types=["intake_record", "goal"],
            output_artifacts=["docs/reports/", "artifacts/funding/"],
            command_or_handler="lib/hermes_knowledge_brain.py",
        ),
        ToolOrScout(
            id="compliance_guard",
            name="Compliance Guard",
            type="scout",
            purpose="Review content for compliance before client/public use",
            input_types=["draft_content"],
            output_artifacts=["compliance_report"],
            autonomous_allowed=False,
            requires_ray_approval=["all compliance reviews"],
        ),
        ToolOrScout(
            id="trading_research_scout",
            name="Trading Research Scout",
            type="scout",
            purpose="Research trading strategies from registered sources",
            input_types=["youtube_url", "strategy_note"],
            output_artifacts=["docs/reports/trading/", "artifacts/trading_research/"],
        ),
        ToolOrScout(
            id="vibe_trading_backtest",
            name="Vibe-Trading Backtest Engine",
            type="scout",
            purpose="Run backtests on trading strategies (EUR/USD and others)",
            input_types=["strategy_config"],
            output_artifacts=["integrations/vibe_trading/reports/backtest_*.json"],
            command_or_handler="integrations/vibe_trading/vibe_trading_adapter.py",
            evidence_path="integrations/vibe_trading/reports/",
        ),
        ToolOrScout(
            id="oanda_demo_adapter",
            name="OANDA Demo Adapter",
            type="scout",
            purpose="Paper/demo trade evaluation on OANDA practice account",
            input_types=["strategy_signal", "backtest_result"],
            output_artifacts=["integrations/oanda_demo/reports/"],
            requires_ray_approval=["live/funded trading", "live account"],
            command_or_handler="integrations/oanda_demo/oanda_demo_adapter.py",
            evidence_path="integrations/oanda_demo/reports/",
        ),
        ToolOrScout(
            id="github_trend_scout",
            name="GitHub Trend Scout",
            type="scout",
            purpose="Monitor GitHub trends for AI/SaaS/automation opportunities",
            input_types=["github_url", "trend_query"],
            output_artifacts=["docs/reports/github_trends/"],
            evidence_path="docs/reports/github_trends/",
        ),
        ToolOrScout(
            id="system_improvement_scout",
            name="System Improvement Scout",
            type="scout",
            purpose="Identify and queue autonomous improvements to Nexus systems",
            input_types=["failure_log", "feedback"],
            output_artifacts=["docs/reports/", "autonomous_improvement_queue"],
            command_or_handler="lib/autonomous_improvement_queue.py",
        ),
        ToolOrScout(
            id="affiliate_monetization_scout",
            name="Affiliate Monetization Scout",
            type="scout",
            purpose="Research affiliate programs aligned with Nexus content and audience",
            input_types=["research_link", "goal"],
            output_artifacts=["artifacts/affiliate_research/"],
            requires_ray_approval=["signing affiliate agreements", "paid campaigns"],
        ),
        ToolOrScout(
            id="newsletter_builder",
            name="Newsletter Builder Scout",
            type="scout",
            purpose="Draft newsletter content from research and source intake",
            input_types=["intake_record", "research_summary"],
            output_artifacts=["docs/content/newsletters/"],
            requires_ray_approval=["sending to subscribers"],
        ),
        ToolOrScout(
            id="shorts_script_builder",
            name="Shorts Script Builder Scout",
            type="scout",
            purpose="Create short-form video scripts from research insights",
            input_types=["youtube_intel", "research_summary"],
            output_artifacts=["docs/content/scripts/"],
            requires_ray_approval=["publishing videos"],
        ),
    ]


def load_registry() -> list[ToolOrScout]:
    """Load registry from JSON, or return defaults."""
    if _REGISTRY_JSON.exists():
        try:
            data = json.loads(_REGISTRY_JSON.read_text())
            items = data if isinstance(data, list) else data.get("tools", [])
            return [ToolOrScout(**{k: v for k, v in item.items()
                                   if k in ToolOrScout.__dataclass_fields__})
                    for item in items]
        except Exception:
            pass
    return _build_default_registry()


def save_registry(items: list[ToolOrScout]) -> None:
    _REGISTRY_JSON.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_JSON.write_text(json.dumps([i.to_dict() for i in items], indent=2))
    _write_markdown(items)


def _write_markdown(items: list[ToolOrScout]) -> None:
    by_type: dict[str, list[ToolOrScout]] = {}
    for item in items:
        by_type.setdefault(item.type, []).append(item)
    lines = [
        "# Hermes Tool and Scout Registry",
        f"*Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        f"\n**{len(items)} total tools/scouts/agents registered**\n",
    ]
    for type_name, group in by_type.items():
        lines.append(f"## {type_name.replace('_', ' ').title()}")
        for item in sorted(group, key=lambda x: x.name):
            lines.append(item.to_plain_english())
        lines.append("")
    _REGISTRY_MD.parent.mkdir(parents=True, exist_ok=True)
    _REGISTRY_MD.write_text("\n".join(lines))


def get_tool(tool_id: str) -> ToolOrScout | None:
    return next((t for t in load_registry() if t.id == tool_id), None)


def get_scouts() -> list[ToolOrScout]:
    return [t for t in load_registry() if t.type == "scout"]


def get_available_tools() -> list[ToolOrScout]:
    return [t for t in load_registry() if t.current_status == "available"]


def route_to_scout(input_type: str) -> ToolOrScout | None:
    """Find the best available scout for a given input type."""
    available = [t for t in load_registry()
                 if t.type == "scout" and t.current_status in ("available", "experimental")
                 and input_type in t.input_types]
    return available[0] if available else None


def registry_summary_plain_english() -> str:
    items = load_registry()
    scouts = [t for t in items if t.type == "scout"]
    agents = [t for t in items if t.type == "agent"]
    tools = [t for t in items if t.type == "core_memory"]
    lines = [
        f"Hermes has {len(scouts)} scouts, {len(agents)} agents, and {len(tools)} core tools available.",
        "",
        "Scouts (handle research and source intake):",
    ]
    for s in scouts[:8]:
        lines.append(f"  • {s.name} — {s.purpose[:60]}")
    lines.append("")
    lines.append("Agents (do work):")
    for a in agents:
        lines.append(f"  • {a.name} — {a.purpose[:60]}")
    lines.append(f"\nFull registry: {_REGISTRY_JSON.relative_to(_ROOT)}")
    return "\n".join(lines)


def initialize_registry() -> None:
    if not _REGISTRY_JSON.exists():
        items = _build_default_registry()
        save_registry(items)
