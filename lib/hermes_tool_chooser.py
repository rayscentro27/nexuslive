"""
hermes_tool_chooser.py
Phase 7B: Map natural language intent to existing Hermes tools.

Ray says natural things like "what tasks are in the queue?"
Tool chooser maps that to the correct run_command() call.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Tool → run_command phrase mapping ─────────────────────────────────────────
_TOOL_COMMAND_MAP: dict[str, str] = {
    "daily_operating_cycle":    "run daily operating cycle",
    "approval_queue":           "show approval queue",
    "revenue_asset_packet":     "show revenue asset packet",
    "research_queue":           "show research queue",
    "scout_assignment":         "show scout assignments",
    "learning_loop":            "show pending lessons",
    "memory_v2_status":         "show memory v2 primary status",
    "while_out_summary":        "continue while i am out",
    "pending_daily_items":      "show pending cycle items",
    "implementation_prompt":    "create prompt from this",
    "unknown_answer_protocol":  None,   # handled by CFO brain directly
    "failure_review":           "show failed responses",
    "task_queue_status":        "show approval queue",
    "morning_activity":         "continue while i am out",
    "rescore":                  "rescore after fixes",
    "revenue_improvement":      "improve revenue asset packet",
    "unresolved_questions":     "show unresolved questions",
    "dedupe_queue":             "dedupe research queue",
}

# ── Intent → tool mapping ─────────────────────────────────────────────────────
_INTENT_TO_TOOL: dict[str, str] = {
    "daily_operating_cycle":        "daily_operating_cycle",
    "approval_decision":            "approval_queue",
    "queue_status_question":        "task_queue_status",
    "task_reference":               "task_queue_status",
    "morning_activity_question":    "morning_activity",
    "money_strategy_question":      "revenue_asset_packet",
    "unknown_answer":               "unknown_answer_protocol",
    "scout_dispatch_request":       "unknown_answer_protocol",
    "implementation_prompt_request":"implementation_prompt",
    "research_queue_question":      "research_queue",
    "memory_status":                "memory_v2_status",
    "pending_items":                "pending_daily_items",
    "learning_loop":                "learning_loop",
    "failure_feedback":             "failure_review",
    "general_business_conversation":"daily_operating_cycle",
}


def choose_tool_for_intent(intent: str, message: str, context: Optional[dict] = None) -> Optional[str]:
    """Return the tool name for a given CFO brain intent."""
    tool = _INTENT_TO_TOOL.get(intent)
    if tool:
        return tool

    # Pattern-based fallback
    msg_lower = (message or "").lower()

    if any(k in msg_lower for k in ["approval", "approve", "needs review", "what needs my"]):
        return "approval_queue"
    if any(k in msg_lower for k in ["research queue", "what did scouts", "scout"]):
        return "research_queue"
    if any(k in msg_lower for k in ["task", "queue", "what is open", "pending", "what is in"]):
        return "task_queue_status"
    if any(k in msg_lower for k in ["morning", "this morning", "what did you do", "catch me up", "while i was out"]):
        return "morning_activity"
    if any(k in msg_lower for k in ["money", "revenue", "earn", "make money", "monetize"]):
        return "revenue_asset_packet"
    if any(k in msg_lower for k in ["daily", "today", "plan", "cycle"]):
        return "daily_operating_cycle"
    if any(k in msg_lower for k in ["memory", "v2", "primary status"]):
        return "memory_v2_status"

    return None


def execute_chosen_tool(tool_name: str, message: str, context: Optional[dict] = None) -> Optional[str]:
    """Run the chosen tool and return its output."""
    command = _TOOL_COMMAND_MAP.get(tool_name)
    if not command:
        return None
    try:
        from hermes_command_router.router import run_command
        return run_command(command)
    except Exception as exc:
        logger.warning("execute_chosen_tool error tool=%s exc=%s", tool_name, exc)
        return None


def format_tool_result_plainly(tool_name: str, result: str, context: Optional[dict] = None) -> str:
    """Post-process a tool result to ensure plain language."""
    if not result:
        return ""
    try:
        from lib.hermes_plain_language_rewriter import compress_technical_output, remove_jargon
        return remove_jargon(compress_technical_output(result))
    except Exception:
        return result


def get_available_tools() -> list[str]:
    """Return list of available tool names."""
    return list(_TOOL_COMMAND_MAP.keys())
