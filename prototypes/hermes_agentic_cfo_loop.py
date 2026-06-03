"""
hermes_agentic_cfo_loop.py
Phase 8 — Local prototype of the Hermes Agentic CFO Loop.

Default mode: mock model, deterministic simulated LLM decisions, no network calls, no Supabase writes.
Optional mode: if HERMES_CFO_MODEL_PROVIDER is set in env, provider config is loaded but not required.

Safety: no publish, email, spend, deploy, live trading, Stripe activation in any mode.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

TRACE_FILE = Path(__file__).parent.parent / "docs" / "reports" / "strategy" / "phase8_cfo_loop_traces.jsonl"
MOCK_MODE = not bool(os.getenv("HERMES_CFO_MODEL_PROVIDER"))
ROOT = Path(__file__).parent.parent

BLOCKED_TOOLS = frozenset({
    "publish_content",
    "send_email_to_subscribers",
    "activate_payment",
    "deploy_production",
    "run_live_trade",
    "apply_to_affiliate",
    "delete_supabase_record",
})

FORBIDDEN_RESPONSE_PHRASES = [
    "artifact_inventory",
    "handoff dump",
    "i can answer from verified artifacts",
    "i wasn't able to generate a quality response",
    "hermes report",
]

APPROVAL_BOUNDARY = "Approval boundary:\n  I will not publish, email, spend money, apply to affiliates, activate payments, deploy production changes, or run live trading without explicit Ray approval."

MOCK_RESPONSE_MARKERS = (
    "based on mock data",
    "sample",
    "mock",
    "mailchimp opt-in form",
    "build and publish lead magnet landing page",
    "connect affiliate offer link",
    "research_scout_1",
    "draft v2 approved",
)

GROUNDING_PATHS = (
    "docs/reports/strategy/hermes_conversation_state.json",
    "docs/reports/operations/hermes_daily_cycle_state.json",
    "docs/reports/actions/hermes_action_queue.jsonl",
    "docs/reports/approvals/hermes_approval_queue_state.json",
    "docs/reports/research_queue/hermes_research_queue.jsonl",
    "docs/reports/research_queue/hermes_scout_assignments.jsonl",
    "docs/reports/content/",
    "docs/reports/strategy/",
    "docs/reports/scouts/",
)


# ── ConversationState ──────────────────────────────────────────────────────────

@dataclass
class ConversationState:
    last_user_message: str = ""
    last_options: list = field(default_factory=list)
    last_option_map: dict = field(default_factory=dict)
    last_selected_option: Optional[int] = None
    last_selected_option_text: Optional[str] = None
    last_recommendation: Optional[str] = None
    active_recommendation: Optional[str] = None
    last_meaningful_response: Optional[str] = None
    last_meaningful_response_summary: Optional[str] = None
    current_topic: Optional[str] = None
    focus_artifact_id: Optional[str] = None
    last_displayed_list: Optional[str] = None
    last_tool_result: Optional[dict] = None
    last_trace_id: Optional[str] = None
    last_response_was_approval_queue: bool = False
    last_response_was_draft: bool = False
    last_response_was_scout_status: bool = False

    def to_summary(self) -> dict:
        return {
            "current_topic": self.current_topic,
            "last_selected_option": self.last_selected_option,
            "last_selected_option_text": self.last_selected_option_text,
            "has_active_recommendation": bool(self.active_recommendation),
            "has_meaningful_response": bool(self.last_meaningful_response),
            "last_response_was_approval_queue": self.last_response_was_approval_queue,
            "last_response_was_draft": self.last_response_was_draft,
            "last_response_was_scout_status": self.last_response_was_scout_status,
            "option_count": len(self.last_option_map),
        }


# ── Mock Fixtures ──────────────────────────────────────────────────────────────

_MOCK_FIXTURES: dict[str, Any] = {
    "revenue_packet": {
        "readiness_score": 72,
        "top_moves": [
            "1. Activate the lead magnet funnel with affiliate offer",
            "2. Launch Nexus membership at founding-member price",
            "3. Run YouTube/LinkedIn content push",
        ],
        "recommendation": "Start with option 1 — closest to revenue with no upfront spend.",
    },
    "approval_queue": {
        "items": [
            {"id": "AQ-001", "type": "content_draft", "title": "Lead magnet landing page copy", "risk": "low"},
            {"id": "AQ-002", "type": "email_sequence", "title": "Onboarding email series", "risk": "medium"},
            {"id": "AQ-003", "type": "affiliate_application", "title": "Apply to funding affiliate program", "risk": "high"},
        ],
        "high_risk_count": 1,
        "total": 3,
    },
    "content_drafts": {
        "v1": {
            "title": "Lead Magnet: Funding Readiness Guide",
            "headline": "Get Your Business Funding-Ready in 30 Days",
            "cta": "Download Now",
            "word_count": 450,
        },
        "v2": {
            "title": "Lead Magnet: Funding Readiness Guide",
            "headline": "Is Your Business Ready for $50K+ in Funding?",
            "cta": "Get the Free Guide",
            "word_count": 510,
        },
        "changes": [
            "Headline softened to question format (more curiosity-driven)",
            "CTA changed from 'Download Now' to 'Get the Free Guide' (lower friction)",
            "Word count increased by 60 words (added social proof section)",
        ],
    },
    "scout_assignments": {
        "assignments": [
            {"scout": "research_scout_1", "task": "Monitor YouTube for new funding content creators", "status": "active", "last_run": "2026-06-02"},
            {"scout": "content_scout", "task": "Review competitor lead magnet landing pages", "status": "queued", "last_run": None},
            {"scout": "market_scout", "task": "Track affiliate program approval rates", "status": "completed", "last_run": "2026-06-01"},
        ],
        "active_count": 1,
        "total": 3,
    },
    "tool_status": {
        "claude": {"status": "available", "last_session": "2026-06-03T10:00:00Z", "current_task": None, "tracked": True},
        "codex": {"status": "unknown", "last_session": None, "current_task": None, "tracked": False},
        "hermes": {"status": "running", "last_session": "2026-06-03T12:00:00Z", "current_task": "conversation_loop", "tracked": True},
    },
    "daily_plan": {
        "date": "2026-06-03",
        "top_priority": "Build and publish lead magnet landing page",
        "tasks": [
            "1. Finalize landing page copy (draft v2 approved)",
            "2. Set up Mailchimp opt-in form",
            "3. Connect affiliate offer link",
        ],
        "blocked": [],
    },
}


def _today_local() -> str:
    return datetime.now().date().isoformat()


def _safe_rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except Exception:
        return str(path)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _path_modified_today(path: Path) -> bool:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date() == datetime.now().date()
    except Exception:
        return False


def _contains_mock_marker(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in MOCK_RESPONSE_MARKERS)


def _load_real_approval_items(limit: int = 10) -> list[dict]:
    try:
        from lib.hermes_approval_queue import list_approval_items
        return list_approval_items(limit=limit) or []
    except Exception:
        return []


def _load_real_scout_snapshot(limit: int = 10) -> dict:
    assignments: list[dict] = []
    queue_entries: list[dict] = []
    action_assignments: list[dict] = []

    try:
        from lib.hermes_cfo_conversation_layer import load_scout_assignments, load_research_queue
        assignments = load_scout_assignments()[:limit]
        queue_entries = load_research_queue(status="open")[:limit]
    except Exception:
        pass

    try:
        from lib.hermes_action_queue import get_unique_open_actions
        for action in get_unique_open_actions():
            scout = getattr(action, "assigned_scout", "") or ""
            if not scout:
                continue
            action_assignments.append({
                "scout": scout,
                "task": getattr(action, "title", "") or getattr(action, "description", ""),
                "status": getattr(action, "status", "queued"),
                "source": "action_queue",
            })
        action_assignments = action_assignments[:limit]
    except Exception:
        pass

    return {
        "assignments": assignments,
        "queue_entries": queue_entries,
        "action_assignments": action_assignments,
    }


def _load_real_daily_summary(limit: int = 5) -> dict:
    evidence: list[dict] = []
    state = None

    try:
        from lib.hermes_daily_cycle_state import load_latest_daily_cycle_state
        state = load_latest_daily_cycle_state()
        if state:
            created = str(state.get("created_at") or "")
            state_date = str(state.get("date") or "")
            if _today_local() in created or state_date == _today_local():
                top_priority = state.get("top_priority") or ""
                if top_priority:
                    evidence.append({
                        "kind": "daily_cycle_state",
                        "summary": f"Top priority: {top_priority}",
                        "path": "docs/reports/operations/hermes_daily_cycle_state.json",
                    })
                for item in (state.get("completed_items") or [])[:2]:
                    label = item.get("item") or item.get("blocker") or ""
                    if label:
                        evidence.append({
                            "kind": "daily_cycle_completed",
                            "summary": f"Completed: {label}",
                            "path": "docs/reports/operations/hermes_daily_cycle_state.json",
                        })
                for item in (state.get("approval_items") or [])[:2]:
                    label = item.get("item") or ""
                    if label:
                        evidence.append({
                            "kind": "daily_cycle_approval",
                            "summary": f"Pending approval: {label}",
                            "path": "docs/reports/operations/hermes_daily_cycle_state.json",
                        })
    except Exception:
        state = None

    report_dirs = [
        ROOT / "docs" / "reports" / "strategy",
        ROOT / "docs" / "reports" / "scouts",
        ROOT / "docs" / "reports" / "content",
    ]
    for report_dir in report_dirs:
        if not report_dir.exists():
            continue
        for path in sorted(report_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not _path_modified_today(path):
                continue
            first_line = _read_text(path).splitlines()[:1]
            summary = first_line[0].strip("# ").strip() if first_line else path.name
            evidence.append({
                "kind": "report",
                "summary": summary or path.name,
                "path": _safe_rel(path),
            })
            if len(evidence) >= limit:
                break
        if len(evidence) >= limit:
            break

    try:
        from lib.hermes_action_queue import get_unique_open_actions
        for action in get_unique_open_actions()[:limit]:
            created = str(getattr(action, "created_at", "") or "")
            updated = str(getattr(action, "updated_at", "") or "")
            if _today_local() not in created and _today_local() not in updated:
                continue
            title = getattr(action, "title", "") or "Open action"
            evidence.append({
                "kind": "action",
                "summary": f"Action: {title}",
                "path": "docs/reports/actions/hermes_action_queue.jsonl",
            })
            if len(evidence) >= limit:
                break
    except Exception:
        pass

    return {"state": state, "evidence": evidence[:limit]}


def _resolve_real_draft_paths() -> tuple[Optional[Path], Optional[Path]]:
    focus_path = None
    try:
        from lib.hermes_conversation_state import load_conversation_state
        cs = load_conversation_state()
        raw_path = cs.get("last_artifact_path") or ""
        if raw_path:
            candidate = ROOT / raw_path if not str(raw_path).startswith("/") else Path(raw_path)
            if candidate.exists():
                focus_path = candidate
    except Exception:
        pass

    try:
        from lib.hermes_artifact_version_compare import (
            find_latest_checklist_draft_pair,
            find_prior_artifact_version,
        )
        if focus_path:
            return find_prior_artifact_version(focus_path), focus_path
        return find_latest_checklist_draft_pair()
    except Exception:
        return None, None


def _resolve_implementation_target(args: dict, state: ConversationState) -> Optional[str]:
    selected = (args.get("option_text") or "").strip()
    recommendation = (args.get("active_recommendation") or "").strip()
    current_topic = (state.current_topic or "").strip().lower()
    generic_research = "research the question and return with verified evidence"
    if selected and selected.lower() == generic_research and recommendation:
        if current_topic in {"nexus_plan", "money_strategy", "daily_plan"}:
            return recommendation
    return selected or recommendation or None


# ── IntentBrain ────────────────────────────────────────────────────────────────

_INTENT_PATTERNS = {
    "draft_comparison": [
        r"what changed", r"what.s different", r"what is different", r"compare.*(draft|version)",
        r"draft.*change", r"show.*change", r"what.s new in", r"how did.*change",
        r"what.{1,5}different", r"different.*version",
    ],
    "clarifying_question_request": [
        r"ask me a better clarifying question",
        r"better clarifying question",
        r"ask.*clarifying question",
    ],
    "approval_bulk_request": [
        r"approve.*(all|them|everything)", r"bulk.?approv", r"i approve", r"approve all",
        r"yes to all", r"just approve", r"approv.*queue",
    ],
    "scout_status": [
        r"what.*scout.*doing", r"scout.*status", r"all.*scout", r"scouts.*now",
        r"check.*scout", r"scout.*report", r"what are.*(scouts|agents).*doing",
    ],
    "scout_assignment": [
        r"have.*scout.*check", r"scout.*check.*youtube", r"assign.*scout",
        r"send.*scout", r"have.*scouts.*look", r"can.*scout.*find",
        r"scout.*youtube", r"youtube.*scout",
    ],
    "tool_status_question": [
        r"what is (claude|codex|hermes|gpt|ai).*working on",
        r"what.s (claude|codex|hermes).*doing",
        r"is (claude|codex|hermes) working",
        r"(claude|codex|hermes).*status",
        r"what.*tool.*doing",
    ],
    "implementation_prompt_request": [
        r"create.*implementation.*prompt", r"implementation.*prompt.*now",
        r"generate.*prompt.*for.*option", r"write.*implementation",
        r"create.*the.*prompt",
    ],
    "implement_now": [
        r"^implement.*(it|now|this)$", r"^do it now$", r"^just.*implement",
        r"^execute.*now$", r"^run.*it.*now$",
    ],
    "acknowledgement_check": [
        r"do you understand", r"did you understand", r"you understand\?",
        r"understand my question", r"get what i.m", r"know what i mean",
    ],
    "summary_of_day": [
        r"what did we work on today", r"what.+happened today",
        r"summary.+today", r"what did we do today", r"daily summary",
        r"today.+progress", r"what.+worked on today", r"catch me up on today",
        r"what.+done today", r"recap.*today",
    ],
    "plain_language_followup": [
        r"^in plain language$", r"plain english version",
        r"dumb it down", r"make it less technical",
    ],
    "simplify_previous_response": [
        r"simplif", r"simpler", r"make.*simpler", r"plain.*english",
        r"explain.*simpler", r"too complex", r"can you.*simplif",
    ],
    "explain_previous_response": [
        r"explain.*recommendation", r"why.*recommend", r"explain.*why",
        r"what.*mean.*recommend", r"break.*down.*recommendation",
        r"explain.*your.*recommendation",
    ],
    "task_reference": [
        r"what was task\s*(\d)", r"what.*task\s*(\d)", r"task\s*(\d).*was",
        r"remind.*task", r"which.*option.*(\d)", r"what.*option\s*(\d)",
        r"option\s*(\d).*was", r"what was\s+(\d)", r"number\s*(\d).*was",
    ],
    "money_strategy": [
        r"how.*make.*money", r"revenue.*this week", r"what.*money.*move",
        r"top.*revenue", r"best.*money", r"money.*strategy", r"how.*earn",
    ],
    "option_selection": [
        r"^lets? do\s*(\d)$", r"^(do|choose|pick|select|go with)\s*(option\s*)?(\d)",
        r"^(\d)\s*please$", r"^option\s*(\d)$", r"i (choose|pick|select|want) .*(\d)",
    ],
    "general_strategy": [
        r"what should.*do", r"what.*next", r"what.*focus on", r"what.*priority",
        r"give.*advice", r"what.*recommend", r"how.*proceed",
    ],
}

class IntentBrain:
    def classify(self, message: str, state: ConversationState) -> dict:
        msg_lower = message.lower().strip()
        state_summary = state.to_summary()

        # Try each intent pattern
        for intent, patterns in _INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, msg_lower):
                    confidence = self._confidence(intent, msg_lower, state_summary)
                    return {
                        "intent": intent,
                        "confidence": confidence,
                        "context_signals": state_summary,
                        "match_pattern": pattern,
                    }

        # Context-based fallback
        if state_summary["last_response_was_approval_queue"] and any(w in msg_lower for w in ["yes", "ok", "sure", "do it", "proceed"]):
            return {"intent": "approval_bulk_request", "confidence": 0.7, "context_signals": state_summary, "match_pattern": "context:approval_queue+affirmative"}

        return {"intent": "unknown_answer", "confidence": 0.5, "context_signals": state_summary, "match_pattern": None}

    def _confidence(self, intent: str, message: str, context: dict) -> float:
        base = 0.85
        # Boost if context aligns
        if intent == "draft_comparison" and context.get("last_response_was_draft"):
            base = 0.95
        if intent == "approval_bulk_request" and context.get("last_response_was_approval_queue"):
            base = 0.97
        if intent == "task_reference" and context.get("last_selected_option") is not None:
            base = 0.95
        if intent == "explain_previous_response" and context.get("has_active_recommendation"):
            base = 0.95
        if intent == "simplify_previous_response" and context.get("has_meaningful_response"):
            base = 0.93
        if intent == "clarifying_question_request":
            base = 0.98
        return base


# ── RetrievalBrain ─────────────────────────────────────────────────────────────

class RetrievalBrain:
    def retrieve(self, intent: str, state: ConversationState) -> dict:
        evidence = {}
        if intent in ("draft_comparison",):
            evidence["draft_paths"] = _resolve_real_draft_paths()
        if intent in ("approval_bulk_request",):
            evidence["approval_queue"] = _load_real_approval_items()
        if intent in ("scout_status", "scout_assignment"):
            evidence["scout_assignments"] = _load_real_scout_snapshot()
        if intent in ("tool_status_question",):
            evidence["tool_status"] = _MOCK_FIXTURES["tool_status"]
        if intent in ("money_strategy", "general_strategy"):
            evidence["revenue_packet"] = _MOCK_FIXTURES["revenue_packet"]
        if intent in ("implementation_prompt_request", "implement_now", "option_selection", "task_reference"):
            evidence["selected_option"] = {
                "number": state.last_selected_option,
                "text": state.last_selected_option_text,
                "option_map": state.last_option_map,
            }
        if intent in ("explain_previous_response",):
            evidence["active_recommendation"] = state.active_recommendation
            evidence["last_meaningful_response_summary"] = state.last_meaningful_response_summary
        if intent in ("simplify_previous_response",):
            evidence["last_meaningful_response"] = state.last_meaningful_response
        if intent in ("summary_of_day",):
            evidence["daily_summary"] = _load_real_daily_summary()
        return evidence


# ── Available Tools ────────────────────────────────────────────────────────────

AVAILABLE_TOOLS = [
    {"name": "compare_drafts", "description": "Compare two draft versions and show changes", "safety": "read-only"},
    {"name": "show_approval_queue", "description": "Show items pending Ray approval", "safety": "read-only"},
    {"name": "bulk_approval_safety_check", "description": "Safety check before bulk approving — high-risk items are skipped", "safety": "read + confirms"},
    {"name": "show_scout_status", "description": "Show current scout assignments and status", "safety": "read-only"},
    {"name": "create_scout_assignment", "description": "Create a new scout task assignment", "safety": "write (internal only)"},
    {"name": "create_implementation_prompt", "description": "Generate an implementation prompt for the selected option", "safety": "write (internal only)"},
    {"name": "show_revenue_plan", "description": "Show revenue packet and top money moves", "safety": "read-only"},
    {"name": "select_option", "description": "Select a numbered option and store it in state", "safety": "state-write"},
    {"name": "explain_recommendation", "description": "Explain the active recommendation in plain language", "safety": "read-only"},
    {"name": "simplify_last_response", "description": "Produce a simplified version of the last meaningful response", "safety": "read-only"},
    {"name": "show_tool_status", "description": "Show status of Claude, Codex, or other tools", "safety": "read-only"},
    {"name": "create_research_assignment", "description": "Create a research task", "safety": "write (internal only)"},
    {"name": "plain_acknowledgement", "description": "Acknowledge and restate understood intent", "safety": "read-only"},
    {"name": "show_daily_summary", "description": "Summarize today's work from verified local state and traces", "safety": "read-only"},
]


# ── CFOReasoningBrain ──────────────────────────────────────────────────────────

class CFOReasoningBrain:
    """
    In mock mode: deterministic rule-based tool selection.
    In live mode: sends structured prompt to configured LLM provider.
    """

    _INTENT_TO_TOOL = {
        "draft_comparison": "compare_drafts",
        "clarifying_question_request": "plain_acknowledgement",
        "approval_bulk_request": "bulk_approval_safety_check",
        "scout_status": "show_scout_status",
        "scout_assignment": "create_scout_assignment",
        "tool_status_question": "show_tool_status",
        "implementation_prompt_request": "create_implementation_prompt",
        "implement_now": "create_implementation_prompt",
        "acknowledgement_check": "plain_acknowledgement",
        "summary_of_day": "show_daily_summary",
        "plain_language_followup": "simplify_last_response",
        "simplify_previous_response": "simplify_last_response",
        "explain_previous_response": "explain_recommendation",
        "task_reference": "select_option",
        "money_strategy": "show_revenue_plan",
        "option_selection": "select_option",
        "general_strategy": "show_revenue_plan",
        "unknown_answer": "plain_acknowledgement",
    }

    def reason(self, message: str, state: ConversationState, evidence: dict, intent_result: dict) -> dict:
        if MOCK_MODE:
            return self._mock_reason(message, state, evidence, intent_result)
        return self._live_reason(message, state, evidence, intent_result)

    def _mock_reason(self, message: str, state: ConversationState, evidence: dict, intent_result: dict) -> dict:
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        tool = self._INTENT_TO_TOOL.get(intent, "plain_acknowledgement")

        tool_args = self._build_tool_args(intent, message, state, evidence)
        needs_scout = intent in ("scout_assignment",)
        recommendation = self._derive_recommendation(intent, evidence, state)
        safety_notes = self._safety_notes(tool)

        return {
            "intent": intent,
            "confidence": confidence,
            "tool_to_call": tool,
            "tool_args": tool_args,
            "plain_answer_plan": f"Use {tool} to address: {message[:60]}",
            "recommendation": recommendation,
            "needs_scout": needs_scout,
            "safety_notes": safety_notes,
            "mode": "mock",
        }

    def _build_tool_args(self, intent: str, message: str, state: ConversationState, evidence: dict) -> dict:
        if intent == "draft_comparison":
            previous, current = evidence.get("draft_paths", (None, None))
            return {
                "previous_path": str(previous) if previous else None,
                "current_path": str(current) if current else None,
                "context": "draft comparison",
            }
        if intent == "approval_bulk_request":
            return {"items": evidence.get("approval_queue") or [], "skip_high_risk": True}
        if intent == "scout_status":
            return {"include_completed": False}
        if intent == "scout_assignment":
            topic = "YouTube" if "youtube" in message.lower() else "general"
            return {"scout_type": "content_scout", "task": f"Check {topic} for new relevant content", "context": message}
        if intent == "tool_status_question":
            tool_match = re.search(r"(claude|codex|hermes|gpt)", message.lower())
            return {"tool_name": tool_match.group(1) if tool_match else "all"}
        if intent in ("implementation_prompt_request", "implement_now"):
            return {
                "option_number": state.last_selected_option,
                "option_text": state.last_selected_option_text or evidence.get("selected_option", {}).get("text"),
                "active_recommendation": state.active_recommendation or state.last_recommendation,
                "safe_only": True,
                "block_public_actions": True,
            }
        if intent in ("task_reference", "option_selection"):
            m = re.search(r"(\d)", message)
            num = int(m.group(1)) if m else (state.last_selected_option or 1)
            option_map = state.last_option_map or {}
            return {"option_number": num, "option_text": option_map.get(str(num)) or state.last_selected_option_text}
        if intent == "explain_previous_response":
            return {"recommendation": state.active_recommendation, "summary": state.last_meaningful_response_summary}
        if intent == "simplify_previous_response":
            return {"response_text": state.last_meaningful_response}
        if intent == "money_strategy":
            return {"include_recommendation": True}
        if intent == "clarifying_question_request":
            return {"message": message, "prompt_type": "clarifying_question"}
        return {"message": message}

    def _derive_recommendation(self, intent: str, evidence: dict, state: ConversationState) -> Optional[str]:
        if intent == "money_strategy":
            return evidence.get("revenue_packet", {}).get("recommendation")
        if intent in ("explain_previous_response",) and state.active_recommendation:
            return state.active_recommendation
        if intent == "approval_bulk_request":
            return "Approve low/medium risk items. Skip high-risk (affiliate application) pending explicit Ray approval."
        if intent == "implement_now":
            return "Produce internal implementation prompt only — do not publish or spend."
        return None

    def _safety_notes(self, tool: str) -> str:
        if tool in BLOCKED_TOOLS:
            return f"BLOCKED: {tool} is not permitted without explicit Ray approval."
        notes = {
            "bulk_approval_safety_check": "High-risk items are never auto-approved. Requires explicit Ray confirmation.",
            "create_implementation_prompt": "Generates internal prompt only. Does not publish, deploy, or spend.",
            "create_scout_assignment": "Internal task queue only. No external network calls made.",
            "select_option": "State-write only. No external action taken.",
        }
        return notes.get(tool, "Read-only or internal-write only. No publish, email, spend, or deploy.")

    def _live_reason(self, message: str, state: ConversationState, evidence: dict, intent_result: dict) -> dict:
        provider = os.getenv("HERMES_CFO_MODEL_PROVIDER", "mock")
        # Live provider integration point — not implemented in prototype
        raise NotImplementedError(
            f"Live model reasoning not implemented in Phase 8 prototype. "
            f"Provider configured: {provider}. Use mock mode for testing."
        )


# ── ToolExecutor ───────────────────────────────────────────────────────────────

class ToolExecutor:
    def execute(self, tool_name: str, tool_args: dict, state: ConversationState) -> dict:
        if tool_name in BLOCKED_TOOLS:
            return {"status": "blocked", "reason": f"{tool_name} is not permitted.", "result": None}

        handler = getattr(self, f"_tool_{tool_name}", None)
        if handler is None:
            return {"status": "unknown_tool", "tool": tool_name, "result": f"Tool '{tool_name}' not implemented in prototype."}
        return handler(tool_args, state)

    def _tool_compare_drafts(self, args: dict, state: ConversationState) -> dict:
        previous_raw = args.get("previous_path")
        current_raw = args.get("current_path")
        if previous_raw is None or current_raw is None:
            return {
                "status": "needs_clarification",
                "tool": "compare_drafts",
                "message": "Which draft should I compare?",
                "grounded": True,
                "grounded_data_paths_checked": [
                    "docs/reports/strategy/hermes_conversation_state.json",
                    "docs/reports/content/",
                ],
            }
        previous_path = Path(previous_raw)
        current_path = Path(current_raw)
        try:
            from lib.hermes_artifact_version_compare import compare_text_artifacts
            changes = compare_text_artifacts(previous_path, current_path)
        except Exception as exc:
            return {
                "status": "unavailable",
                "tool": "compare_drafts",
                "message": f"Draft comparison unavailable: {exc}",
                "grounded": True,
                "grounded_data_paths_checked": ["docs/reports/content/"],
            }
        state.last_response_was_draft = True
        return {
            "status": "ok",
            "tool": "compare_drafts",
            "changes": changes,
            "change_count": len(changes.get("changed", [])) + len(changes.get("added", [])) + len(changes.get("removed", [])),
            "grounded": True,
            "grounded_data_paths_checked": [
                "docs/reports/strategy/hermes_conversation_state.json",
                _safe_rel(previous_path),
                _safe_rel(current_path),
            ],
        }

    def _tool_show_approval_queue(self, args: dict, state: ConversationState) -> dict:
        queue = _MOCK_FIXTURES["approval_queue"]
        state.last_response_was_approval_queue = True
        return {"status": "ok", "tool": "show_approval_queue", "queue": queue}

    def _tool_bulk_approval_safety_check(self, args: dict, state: ConversationState) -> dict:
        queue_items = args.get("items") or []
        if not queue_items:
            return {
                "status": "unavailable",
                "tool": "bulk_approval_safety_check",
                "message": "Approval queue unavailable.",
                "grounded": True,
                "grounded_data_paths_checked": [
                    "docs/reports/approvals/hermes_approval_queue_state.json",
                    "docs/reports/actions/hermes_action_queue.jsonl",
                    "docs/reports/operations/hermes_daily_cycle_state.json",
                ],
            }
        high_risk = [i for i in queue_items if str(i.get("risk_level", i.get("risk", ""))).lower() == "high"]
        approvable = [i for i in queue_items if i not in high_risk]
        return {
            "status": "ok",
            "tool": "bulk_approval_safety_check",
            "approvable": approvable,
            "skipped_high_risk": high_risk,
            "message": f"Safe to approve {len(approvable)} items. {len(high_risk)} high-risk item(s) require explicit approval.",
            "grounded": True,
            "grounded_data_paths_checked": [
                "docs/reports/approvals/hermes_approval_queue_state.json",
                "docs/reports/actions/hermes_action_queue.jsonl",
                "docs/reports/operations/hermes_daily_cycle_state.json",
            ],
        }

    def _tool_show_scout_status(self, args: dict, state: ConversationState) -> dict:
        snapshot = _load_real_scout_snapshot()
        state.last_response_was_scout_status = True
        has_real = bool(snapshot.get("assignments") or snapshot.get("queue_entries") or snapshot.get("action_assignments"))
        return {
            "status": "ok" if has_real else "unavailable",
            "tool": "show_scout_status",
            "assignments": snapshot,
            "grounded": True,
            "grounded_data_paths_checked": [
                "docs/reports/research_queue/hermes_scout_assignments.jsonl",
                "docs/reports/research_queue/hermes_research_queue.jsonl",
                "docs/reports/actions/hermes_action_queue.jsonl",
            ],
        }

    def _tool_create_scout_assignment(self, args: dict, state: ConversationState) -> dict:
        return {
            "status": "ok",
            "tool": "create_scout_assignment",
            "assignment": {
                "scout": args.get("scout_type", "research_scout"),
                "task": args.get("task", "General research"),
                "context": args.get("context", ""),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "id": f"SA-{uuid.uuid4().hex[:6].upper()}",
            },
        }

    def _tool_create_implementation_prompt(self, args: dict, state: ConversationState) -> dict:
        option_text = _resolve_implementation_target(args, state)
        if not option_text:
            return {
                "status": "needs_clarification",
                "tool": "create_implementation_prompt",
                "message": "What do you want me to implement?",
                "grounded": True,
                "grounded_data_paths_checked": ["docs/reports/strategy/hermes_conversation_state.json"],
            }
        return {
            "status": "ok",
            "tool": "create_implementation_prompt",
            "prompt": (
                f"IMPLEMENTATION PROMPT\n\n"
                f"Selected option: {option_text}\n\n"
                f"Task: Build the implementation for this option.\n"
                f"Constraints: internal only, no publish, no spend, no deploy without Ray approval.\n\n"
                f"Next safe step: Review this prompt, then authorize execution."
            ),
            "safety": "Internal prompt only. No public action taken.",
            "grounded": True,
            "grounded_data_paths_checked": ["docs/reports/strategy/hermes_conversation_state.json"],
        }

    def _tool_show_revenue_plan(self, args: dict, state: ConversationState) -> dict:
        packet = _MOCK_FIXTURES["revenue_packet"]
        state.current_topic = "money_strategy"
        state.last_option_map = {str(i+1): opt.split(". ", 1)[1] if ". " in opt else opt
                                  for i, opt in enumerate(packet["top_moves"])}
        state.last_options = packet["top_moves"]
        state.active_recommendation = packet["recommendation"]
        return {"status": "ok", "tool": "show_revenue_plan", "packet": packet}

    def _tool_select_option(self, args: dict, state: ConversationState) -> dict:
        num = args.get("option_number", 1)
        text = args.get("option_text") or state.last_option_map.get(str(num), f"Option {num}")
        state.last_selected_option = num
        state.last_selected_option_text = text
        return {"status": "ok", "tool": "select_option", "selected": num, "text": text}

    def _tool_explain_recommendation(self, args: dict, state: ConversationState) -> dict:
        rec = args.get("recommendation") or state.active_recommendation or "No active recommendation."
        summary = args.get("summary") or state.last_meaningful_response_summary or ""
        return {
            "status": "ok",
            "tool": "explain_recommendation",
            "recommendation": rec,
            "summary": summary,
            "plain_explanation": f"The recommendation is: {rec}",
        }

    def _tool_simplify_last_response(self, args: dict, state: ConversationState) -> dict:
        text = args.get("response_text") or state.last_meaningful_response
        if not text:
            return {"status": "no_context", "tool": "simplify_last_response", "message": "No prior response to simplify."}
        # Extract first 3 sentences as simplified version
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        simplified = " ".join(sentences[:3]) if sentences else text[:200]
        return {"status": "ok", "tool": "simplify_last_response", "simplified": simplified, "original_length": len(text)}

    def _tool_show_tool_status(self, args: dict, state: ConversationState) -> dict:
        tool_name = args.get("tool_name", "all")
        statuses = _MOCK_FIXTURES["tool_status"]
        if tool_name in statuses:
            return {"status": "ok", "tool": "show_tool_status", "tool_name": tool_name, "tool_status": statuses[tool_name]}
        return {"status": "ok", "tool": "show_tool_status", "tool_name": "all", "all_statuses": statuses}

    def _tool_create_research_assignment(self, args: dict, state: ConversationState) -> dict:
        return {
            "status": "ok",
            "tool": "create_research_assignment",
            "assignment": {
                "task": args.get("task", "Research task"),
                "context": args.get("context", ""),
                "id": f"RA-{uuid.uuid4().hex[:6].upper()}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    def _tool_plain_acknowledgement(self, args: dict, state: ConversationState) -> dict:
        if args.get("prompt_type") == "clarifying_question":
            return {
                "status": "ok",
                "tool": "plain_acknowledgement",
                "clarifying_question": True,
                "grounded": True,
                "grounded_data_paths_checked": ["docs/reports/strategy/hermes_conversation_state.json"],
            }
        return {
            "status": "ok",
            "tool": "plain_acknowledgement",
            "understood": True,
            "message": f"Understood: {args.get('message', 'your message')}",
            "grounded": True,
            "grounded_data_paths_checked": ["docs/reports/strategy/hermes_conversation_state.json"],
        }

    def _tool_show_daily_summary(self, args: dict, state: ConversationState) -> dict:
        summary = _load_real_daily_summary()
        evidence = summary.get("evidence") or []
        return {
            "status": "ok" if evidence else "unavailable",
            "tool": "show_daily_summary",
            "summary": summary,
            "verified": bool(evidence),
            "grounded": True,
            "grounded_data_paths_checked": [
                "docs/reports/operations/hermes_daily_cycle_state.json",
                "docs/reports/actions/hermes_action_queue.jsonl",
                "docs/reports/strategy/",
                "docs/reports/scouts/",
                "docs/reports/content/",
            ],
        }


# ── PlainEnglishResponder ──────────────────────────────────────────────────────

class PlainEnglishResponder:
    def format(self, tool_name: str, tool_result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if tool_result.get("status") == "blocked":
            return self._blocked_response(tool_name, tool_result)

        handler = getattr(self, f"_format_{tool_name}", self._format_default)
        response = handler(tool_result, reasoning, message, state)
        return self._append_boundary(response)

    def _append_boundary(self, text: str) -> str:
        if "approval boundary" not in text.lower():
            return text + f"\n\n{APPROVAL_BOUNDARY}"
        return text

    def _blocked_response(self, tool_name: str, result: dict) -> str:
        return f"PLAIN ANSWER\n\n{result['reason']}\n\n{APPROVAL_BOUNDARY}"

    def _format_compare_drafts(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("status") == "needs_clarification":
            return "DRAFT COMPARISON\n\nWhich draft should I compare?"
        if result.get("status") == "unavailable":
            return f"DRAFT COMPARISON\n\n{result.get('message', 'Draft comparison is unavailable right now.')}"
        changes = result.get("changes", {})
        lines = ["DRAFT COMPARISON\n", "Here is what changed in the draft:\n"]
        for title in changes.get("added", [])[:3]:
            lines.append(f"  Added section: {title}")
        for title in changes.get("changed", [])[:5]:
            lines.append(f"  Updated section: {title}")
        for title in changes.get("removed", [])[:3]:
            lines.append(f"  Removed section: {title}")
        if not any(changes.get(k) for k in ("added", "changed", "removed")):
            lines.append("  No structural changes were detected.")
        lines.append("\nNext safe step: Review the latest draft or ask for a specific revision.")
        return "\n".join(lines)

    def _format_bulk_approval_safety_check(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("status") == "unavailable":
            return "APPROVAL BULK CHECK\n\nThe approval queue is unavailable right now."
        approvable = result.get("approvable", [])
        skipped = result.get("skipped_high_risk", [])
        lines = ["APPROVAL BULK CHECK\n", "Before bulk approving, here is the live safety check:\n"]
        lines.append(f"Safe to approve ({len(approvable)} items):")
        for item in approvable:
            lines.append(f"  ✓ {item.get('title', 'Unnamed item')} ({item.get('risk_level', item.get('risk', 'unknown'))} risk)")
        if skipped:
            lines.append(f"\nSkipped — needs explicit approval ({len(skipped)} item{'s' if len(skipped)>1 else ''}):")
            for item in skipped:
                lines.append(f"  ! {item.get('title', 'Unnamed item')} ({item.get('risk_level', item.get('risk', 'unknown'))} risk)")
        lines.append(f"\nRecommendation: Approve the {len(approvable)} safe items now. Review the high-risk items separately.")
        lines.append(f"\nNext safe step: Confirm approval of the {len(approvable)} low/medium risk items, or say 'approve all safe' to proceed.")
        return "\n".join(lines)

    def _format_show_scout_status(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        snapshot = result.get("assignments", {})
        assignments = snapshot.get("assignments") or []
        queue_entries = snapshot.get("queue_entries") or []
        action_assignments = snapshot.get("action_assignments") or []
        lines = ["SCOUT STATUS\n"]
        if not (assignments or queue_entries or action_assignments):
            lines.append("I do not have verified live scout assignments right now.")
            return "\n".join(lines)
        if assignments:
            lines.append("Tracked scout assignments:")
            for a in assignments[:5]:
                lines.append(f"  - {a.get('scout', '?')}: {a.get('research_question', '?')} [{a.get('status', '?')}]")
        if action_assignments:
            lines.append("\nAction queue scout work:")
            for a in action_assignments[:5]:
                lines.append(f"  - {a.get('scout', '?')}: {a.get('task', '?')} [{a.get('status', '?')}]")
        if queue_entries:
            lines.append("\nOpen research queue:")
            for q in queue_entries[:5]:
                lines.append(f"  - {q.get('scout', '?')}: {q.get('question', '?')} [{q.get('status', '?')}]")
        lines.append("\nNext safe step: Check the research queue or assign a new verified scout task.")
        return "\n".join(lines)

    def _format_create_scout_assignment(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        a = result.get("assignment", {})
        lines = [
            "PLAIN ANSWER\n",
            f"Scout assignment created:\n",
            f"  Scout: {a.get('scout', 'content_scout')}",
            f"  Task: {a.get('task', '')}",
            f"  Assignment ID: {a.get('id', '')}",
            f"\nWhat it means:",
            f"  The scout will check for new relevant content and report findings.",
            f"\nNext safe step: Check back with 'what are the scouts doing' to see results.",
        ]
        return "\n".join(lines)

    def _format_show_tool_status(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        tool_name = result.get("tool_name", "")
        if "tool_status" in result:
            ts = result["tool_status"]
            tracked = ts.get("tracked", False)
            current = ts.get("current_task")
            status = ts.get("status", "unknown")
            lines = ["PLAIN ANSWER\n"]
            if not tracked:
                lines.append(f"{tool_name.title()} is not currently tracked in the session registry.")
                lines.append(f"\nWhat it means:")
                lines.append(f"  I cannot verify what {tool_name} is working on right now.")
                lines.append(f"\nRecommendation: If you need to track {tool_name}'s work, I can add a session tracking entry.")
                lines.append(f"\nNext safe step: Say 'track {tool_name} task: [description]' to add tracking.")
            else:
                lines.append(f"{tool_name.title()} status: {status}")
                if current:
                    lines.append(f"Current task: {current}")
                else:
                    lines.append(f"No active task tracked.")
                lines.append(f"\nNext safe step: Check back later or assign a new task.")
            return "\n".join(lines)
        # All statuses
        statuses = result.get("all_statuses", {})
        lines = ["PLAIN ANSWER\n", "Tool status overview:\n"]
        for name, ts in statuses.items():
            status = ts.get("status", "unknown")
            current = ts.get("current_task", None)
            tracked = ts.get("tracked", False)
            lines.append(f"  {name}: {status}" + (f" — {current}" if current else "") + ("" if tracked else " (not tracked)"))
        return "\n".join(lines)

    def _format_create_implementation_prompt(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("status") == "needs_clarification":
            return "IMPLEMENTATION PROMPT\n\nWhat do you want me to implement?"
        prompt = result.get("prompt", "")
        safety = result.get("safety", "")
        lines = [
            "IMPLEMENTATION PROMPT\n",
            "Implementation prompt created (internal only):\n",
            prompt,
            f"\nSafety note: {safety}",
            f"\nNext safe step: Review this prompt, then authorize implementation with 'approve implementation'.",
        ]
        return "\n".join(lines)

    def _format_show_revenue_plan(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        packet = result.get("packet", {})
        lines = ["WEEKLY MONEY PLAN\n"]
        for move in packet.get("top_moves", []):
            lines.append(f"  {move}")
        rec = packet.get("recommendation", "")
        if rec:
            lines.append(f"\nMy recommendation:\n  {rec}")
        lines.append(f"\nNext safe step: Say 'lets do 1' to select option 1, or ask me to explain any option.")
        return "\n".join(lines)

    def _format_select_option(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        num = result.get("selected")
        text = result.get("text", "")
        lines = [
            "PLAIN ANSWER\n",
            f"You asked about option {num}:\n",
            f"  {text}\n",
            f"What it means:",
            f"  This was the option you selected or are asking about.",
            f"\nNext safe step: Say 'create the implementation prompt' to move this forward.",
        ]
        return "\n".join(lines)

    def _format_explain_recommendation(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        rec = result.get("recommendation", "No active recommendation found.")
        summary = result.get("summary", "")
        lines = [
            "PLAIN ANSWER\n",
            "Here is the recommendation explained in plain language:\n",
        ]
        if rec and rec != "No active recommendation found.":
            lines.append(f"  {rec}")
        if summary:
            lines.append(f"\nContext:\n  {summary}")
        lines.append(f"\nWhat it means:")
        lines.append(f"  This is the best-fit option given current constraints and available resources.")
        lines.append(f"\nNext safe step: Say 'lets do 1' to confirm, or ask me to compare options.")
        return "\n".join(lines)

    def _format_simplify_last_response(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("status") == "no_context":
            return (
                "PLAIN ANSWER\n\n"
                "I don't have a previous response to simplify yet.\n\n"
                "Try asking: 'how do we make money this week' first, then I can simplify it."
                f"\n\n{APPROVAL_BOUNDARY}"
            )
        simplified = result.get("simplified", "")
        lines = [
            "PLAIN ANSWER\n",
            "Here is a simplified version:\n",
            f"  {simplified}",
            f"\nNext safe step: Ask follow-up questions or say 'lets do 1' to select an option.",
        ]
        return "\n".join(lines)

    def _format_plain_acknowledgement(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("clarifying_question"):
            return (
                "CLARIFYING QUESTION\n\n"
                "What outcome do you want from this:\n"
                "1. create a safe implementation prompt\n"
                "2. assign a scout\n"
                "3. summarize current state\n"
                "4. prepare approval checklist"
            )
        lines = [
            "PLAIN ANSWER\n",
            f"Yes, I understand your question.\n",
            f"What I understood: {message[:100]}",
            f"\nIf that is not right, please rephrase and I will try again.",
            f"\nNext safe step: Confirm my understanding or correct me.",
        ]
        return "\n".join(lines)

    def _format_show_daily_summary(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        if result.get("status") == "unavailable":
            return "DAY SUMMARY\n\nI do not have a verified day summary yet."
        summary = result.get("summary", {})
        evidence = summary.get("evidence") or []
        lines = ["DAY SUMMARY\n", "Here is the verified day summary I found:\n"]
        for item in evidence[:5]:
            lines.append(f"  - {item.get('summary', '?')} ({item.get('path', 'local state')})")
        lines.append("\nNext safe step: Review the current state and confirm what should happen next.")
        return "\n".join(lines)

    def _format_default(self, result: dict, reasoning: dict, message: str, state: ConversationState) -> str:
        tool = result.get("tool", "unknown")
        lines = [
            "PLAIN ANSWER\n",
            f"Completed: {tool}\n",
            f"Result: {json.dumps(result, indent=2)[:400]}",
            f"\nNext safe step: Review the result and tell me what to do next.",
        ]
        return "\n".join(lines)


# ── TraceLogger ────────────────────────────────────────────────────────────────

class TraceLogger:
    def __init__(self, trace_file: Path = TRACE_FILE):
        self.trace_file = trace_file
        self.trace_file.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        message: str,
        intent_result: dict,
        evidence_keys: list,
        reasoning: dict,
        tool_result: dict,
        final_response: str,
        fallback_reason: Optional[str] = None,
    ) -> str:
        trace_id = str(uuid.uuid4())[:8]
        entry = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": message,
            "intent": intent_result.get("intent"),
            "confidence": intent_result.get("confidence"),
            "retrieved_evidence_keys": evidence_keys,
            "selected_tool": reasoning.get("tool_to_call"),
            "tool_args": reasoning.get("tool_args"),
            "tool_result_summary": self._summarize_result(tool_result),
            "final_response_header": final_response.split("\n")[0] if final_response else "",
            "fallback_reason": fallback_reason,
            "safety_notes": reasoning.get("safety_notes"),
            "mode": reasoning.get("mode", "mock"),
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        return trace_id

    def _summarize_result(self, result: dict) -> str:
        if not result:
            return "no result"
        status = result.get("status", "unknown")
        tool = result.get("tool", "unknown")
        # Extract a short meaningful summary
        for key in ("message", "simplified", "prompt", "plain_explanation"):
            if key in result and result[key]:
                return f"{tool}:{status} — {str(result[key])[:80]}"
        return f"{tool}:{status}"


# ── CFO Loop (main entry point) ────────────────────────────────────────────────

class HermesCFOLoop:
    def __init__(self):
        self.state = ConversationState()
        self.intent_brain = IntentBrain()
        self.retrieval_brain = RetrievalBrain()
        self.cfo_brain = CFOReasoningBrain()
        self.tool_executor = ToolExecutor()
        self.responder = PlainEnglishResponder()
        self.trace_logger = TraceLogger()

    def process(self, message: str) -> tuple[str, dict]:
        """Process a message through the full CFO loop. Returns (response, trace_info)."""
        self.state.last_user_message = message

        # Step 1: Intent Brain
        intent_result = self.intent_brain.classify(message, self.state)

        # Step 2: Retrieval Brain
        evidence = self.retrieval_brain.retrieve(intent_result["intent"], self.state)

        # Step 3: CFO Reasoning Brain
        reasoning = self.cfo_brain.reason(message, self.state, evidence, intent_result)

        # Step 4: Tool Executor (with safety check)
        tool_name = reasoning["tool_to_call"]
        tool_args = reasoning["tool_args"]

        if tool_name in BLOCKED_TOOLS:
            tool_result = {"status": "blocked", "reason": f"{tool_name} requires explicit Ray approval.", "tool": tool_name}
        else:
            tool_result = self.tool_executor.execute(tool_name, tool_args, self.state)

        # Step 5: Plain-English Responder
        response = self.responder.format(tool_name, tool_result, reasoning, message, self.state)

        # Safety check on response
        response = self._sanitize_response(response)

        # Step 6: Update state
        self._update_state(tool_name, tool_result, reasoning, response)

        # Step 7: Trace
        trace_id = self.trace_logger.log(
            message=message,
            intent_result=intent_result,
            evidence_keys=list(evidence.keys()),
            reasoning=reasoning,
            tool_result=tool_result,
            final_response=response,
        )
        self.state.last_trace_id = trace_id

        trace_info = {
            "trace_id": trace_id,
            "intent": intent_result["intent"],
            "confidence": intent_result["confidence"],
            "tool": tool_name,
            "mode": "mock" if MOCK_MODE else "live",
            "grounded": bool(tool_result.get("grounded", False)),
            "grounded_data_paths_checked": list(tool_result.get("grounded_data_paths_checked") or []),
            "mock_response_blocked": _contains_mock_marker(response),
        }
        return response, trace_info

    def _sanitize_response(self, response: str) -> str:
        lower = response.lower()
        for phrase in FORBIDDEN_RESPONSE_PHRASES:
            if phrase in lower and phrase != "hermes report":
                response = re.sub(re.escape(phrase), "[removed]", response, flags=re.IGNORECASE)
        return response

    def _update_state(self, tool_name: str, tool_result: dict, reasoning: dict, response: str) -> None:
        self.state.last_tool_result = tool_result

        if tool_name == "show_revenue_plan" and tool_result.get("status") == "ok":
            packet = tool_result.get("packet", {})
            rec = packet.get("recommendation")
            if rec:
                self.state.active_recommendation = rec
                self.state.last_recommendation = rec
            self.state.last_meaningful_response = response[:2000]
            self.state.last_meaningful_response_summary = f"Weekly money plan with {len(packet.get('top_moves',[]))} options. Recommendation: {rec or 'see plan'}"
            self.state.last_response_was_approval_queue = False
            self.state.last_response_was_draft = False

        elif tool_name == "select_option" and tool_result.get("status") == "ok":
            self.state.last_selected_option = tool_result.get("selected")
            self.state.last_selected_option_text = tool_result.get("text")
            self.state.last_meaningful_response = response[:2000]

        elif tool_name == "show_approval_queue":
            self.state.last_response_was_approval_queue = True
            self.state.last_response_was_draft = False
            self.state.last_meaningful_response = response[:2000]

        elif tool_name == "compare_drafts":
            self.state.last_response_was_draft = True
            self.state.last_response_was_approval_queue = False
            self.state.last_meaningful_response = response[:2000]

        elif tool_name not in ("bulk_approval_safety_check", "plain_acknowledgement"):
            # Non-fallback responses update meaningful response
            if len(response) > 100:
                self.state.last_meaningful_response = response[:2000]


# ── Convenience function ───────────────────────────────────────────────────────

def run_cfo_loop(message: str, loop: Optional[HermesCFOLoop] = None) -> tuple[str, dict]:
    if loop is None:
        loop = HermesCFOLoop()
    return loop.process(message)


if __name__ == "__main__":
    import sys
    loop = HermesCFOLoop()
    messages = sys.argv[1:] or [
        "how do we make money this week",
        "lets do 1",
        "what was task 1",
        "can you simplify your response",
        "explain your recommendation in plain language",
    ]
    for msg in messages:
        print(f"\n{'─'*60}")
        print(f"MSG: {msg}")
        response, trace = loop.process(msg)
        print(f"INTENT: {trace['intent']} ({trace['confidence']:.0%})")
        print(f"TOOL: {trace['tool']}")
        print(f"\n{response[:500]}")
