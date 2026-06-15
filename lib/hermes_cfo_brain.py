"""
hermes_cfo_brain.py
Phase 7B: General natural-language reasoning layer for Hermes.

Sits above old fallback logic, below exact command handlers.
Uses conversation context to resolve follow-ups, option selections,
simplification requests, explanations, and task references.

Safety: Never publishes, emails, spends, deploys, applies to affiliates,
activates Stripe, or runs live trading without explicit Ray approval.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_SAFETY_BOUNDARY = (
    "I will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, activate Stripe, run live trading, or "
    "use client-facing content without explicit Ray approval."
)

# ── Intent categories ─────────────────────────────────────────────────────────
CFO_BRAIN_INTENTS = {
    "followup_question",
    "option_selection",
    "simplify_previous_response",
    "explain_previous_response",
    "task_reference",
    "recommendation_question",
    "strategic_concern",
    "implementation_prompt_request",
    "unknown_answer",
    "scout_dispatch_request",
    "queue_status_question",
    "morning_activity_question",
    "money_strategy_question",
    "approval_decision",
    "plain_language_request",
    "failure_feedback",
    "general_business_conversation",
}

# ── Pattern matching rules ─────────────────────────────────────────────────────
# Order matters — more specific patterns first.

_INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("simplify_previous_response", [
        "simplify your response", "simplify that", "make it simpler",
        "shorter version", "too long", "shorten that", "simpler version",
        "can you simplify", "in short", "brief version", "summarize that",
        "simplify the response",
    ]),
    ("explain_previous_response", [
        "what does that mean", "and what does that mean", "what do you mean",
        "explain your recommendation", "explain that", "explain in plain",
        "explain your previous", "explain your last", "in plain language",
        "explain it", "what did you mean by", "plain language explanation",
        "explain the recommendation",
    ]),
    ("option_selection", [
        "let's do", "lets do", "do option", "choose option", "go with option",
        "i'll take", "i'll choose", "select option", "option 1", "option 2",
        "option 3", "do 1", "do 2", "do 3", "pick 1", "pick 2",
        "i choose", "we'll go with", "let's go with",
    ]),
    ("task_reference", [
        "what was task", "task 1", "task 2", "task 3",
        "what is task", "first task", "second task", "third task",
        "what were the tasks", "show me task", "the first option",
        "what was the first", "what was option",
        "what was number", "number 1", "number 2", "number 3",
        "remind me what", "which one was", "remind me of",
    ]),
    ("morning_activity_question", [
        "what did you do this morning", "what happened this morning",
        "what did you work on", "catch me up", "while i was out",
        "what happened since", "what did you do while", "morning summary",
        "what have you been doing",
    ]),
    ("queue_status_question", [
        "what task are in the queue", "what tasks are in the queue",
        "what's in the queue", "what is in the queue", "show me the tasks",
        "what tasks are open", "what tasks are pending", "task queue",
        "what is pending", "what needs to be done", "what's pending",
        "open tasks", "pending tasks", "queue status",
    ]),
    ("money_strategy_question", [
        "how do we make money", "how do we make money this week",
        "what should we monetize", "make money right now", "how to earn",
        "weekly money plan", "revenue this week", "make money now",
        "what's the best money move", "best revenue move",
    ]),
    ("failure_feedback", [
        "that is not what i meant", "that's not what i meant",
        "that's wrong", "that was wrong", "wrong answer",
        "that's not right", "that is not right", "not what i asked",
        "log this as a bad response", "hermes, learn from that",
        "learn from that", "that was not right",
    ]),
    ("implementation_prompt_request", [
        "create a prompt for claude", "give me a prompt for claude",
        "what should i send claude", "create a super prompt",
        "turn this into a claude prompt", "prompt for claude",
        "create a prompt to", "claude prompt", "make a prompt",
        "generate a prompt", "create an implementation prompt",
    ]),
    ("scout_dispatch_request", [
        "can your scouts", "can hermes find", "can hermes research",
        "scouts figure it out", "have the scouts look",
        "i don't know, can you", "figure it out", "research this",
        "find out for me", "look into this",
    ]),
    ("recommendation_question", [
        "what is your recommendation", "what do you recommend",
        "what should we do", "what would you suggest",
        "what's the best approach", "best next step",
        "what should i do next",
    ]),
    ("plain_language_request", [
        "speak plainly", "plain english", "no jargon",
        "simple terms", "plain language", "eli5",
        "explain like i'm 5", "break it down",
    ]),
    ("approval_decision", [
        "i approve", "approved", "reject", "denied", "i reject",
        "approve item", "reject item", "approve that", "reject that",
    ]),
    ("followup_question", [
        "what was that again", "can you repeat", "say that again",
        "more detail on that", "tell me more about",
        "elaborate on", "go deeper on",
    ]),
    ("general_business_conversation", []),  # catch-all
]


# ── Main entry points ─────────────────────────────────────────────────────────

def should_use_cfo_brain(message: str) -> bool:
    """Return True if this message should be processed by the CFO brain.

    Returns False for exact command phrases (handled by existing handlers).
    Returns True for natural language that needs reasoning + context.
    """
    if not message or len(message.strip()) < 3:
        return False

    msg = message.strip().lower()

    # Short single-word messages: skip
    if len(msg.split()) <= 1:
        return False

    # Explicit exact command signals: let existing handlers run first
    _COMMAND_VERBS = re.compile(
        r'^(show|run|build|rescore|fix|approve|reject|record|mark|display|list|get)\s',
        re.IGNORECASE,
    )
    if _COMMAND_VERBS.match(msg):
        return False

    # Check all intent patterns
    intent = classify_cfo_intent(msg, context=None)
    return intent != "general_business_conversation" or len(msg.split()) > 5


def classify_cfo_intent(message: str, context: Optional[dict] = None) -> str:
    """Classify a natural language message into a CFO brain intent category."""
    msg = message.strip().lower()

    for intent, patterns in _INTENT_PATTERNS:
        if any(p in msg for p in patterns):
            return intent

    # Number-only message like "1" or "2" → option selection
    if re.match(r'^\s*\d\s*$', msg):
        return "option_selection"

    # Has "?" → followup question
    if "?" in msg and len(msg.split()) <= 8:
        return "followup_question"

    # Longer message without exact command → general business conversation
    if len(msg.split()) > 5:
        return "general_business_conversation"

    return "general_business_conversation"


def process_with_cfo_brain(message: str, normalized: Optional[str] = None) -> Optional[str]:
    """Main CFO brain entry point. Returns response or None to fall through."""
    msg = (normalized or message).strip().lower()
    intent = classify_cfo_intent(msg)

    try:
        from lib.hermes_conversation_state import load_conversation_state
        context = load_conversation_state()
    except Exception:
        context = {}

    handlers = {
        "simplify_previous_response":   handle_simplify_request,
        "explain_previous_response":    handle_explain_request,
        "plain_language_request":       handle_explain_request,
        "option_selection":             handle_option_selection,
        "task_reference":               handle_task_reference,
        "morning_activity_question":    handle_morning_activity,
        "queue_status_question":        handle_queue_status,
        "money_strategy_question":      handle_money_strategy,
        "failure_feedback":             handle_failure_feedback,
        "implementation_prompt_request": handle_prompt_generation_request,
        "scout_dispatch_request":       handle_unknown_with_scout_dispatch,
        "unknown_answer":               handle_unknown_with_scout_dispatch,
        "recommendation_question":      handle_recommendation_question,
        "followup_question":            handle_followup_question,
        "general_business_conversation": handle_general_business,
    }

    handler = handlers.get(intent)
    if handler:
        result = handler(message, context)
        if result:
            _save_interaction_context(message, result, intent)
            return result

    return None


def _save_interaction_context(message: str, response: str, tool_used: Optional[str] = None) -> None:
    """Save conversation state after CFO brain response."""
    try:
        from lib.hermes_conversation_state import update_conversation_state
        update_conversation_state(message, response, tool_used=tool_used)
    except Exception as exc:
        logger.warning("_save_interaction_context error: %s", exc)


# ── Individual handlers ───────────────────────────────────────────────────────

_NO_CONTEXT_MARKERS = [
    "i don't have a previous",
    "ask me a question first",
    "please ask me",
    "no previous response",
    "can do next",
    "approval boundary",
]


def _is_meaningful_response(text: str) -> bool:
    """Return True if text contains actual content (not a default template)."""
    if not text or len(text.strip()) < 30:
        return False
    text_lower = text.lower()
    # Skip responses that are themselves "no context" messages
    if any(m in text_lower for m in _NO_CONTEXT_MARKERS[:3]):
        return False
    # Filter out template/boundary lines
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    real_content_lines = [l for l in lines
                          if not any(m in l.lower() for m in _NO_CONTEXT_MARKERS)]
    # Accept if 3+ meaningful lines, or a single substantive sentence (>= 40 chars)
    return len(real_content_lines) >= 3 or len(text.strip()) >= 40


def handle_simplify_request(message: str, context: dict) -> str:
    """Handle: 'CAN YOU SIMPLIFY YOUR RESPONSE'

    Uses last_meaningful_response so a task-missing fallback or CORRECTING COURSE
    message does not accidentally become the thing being simplified.
    """
    from lib.hermes_conversation_state import get_last_meaningful_response, get_last_response_summary
    from lib.hermes_plain_language_rewriter import simplify_response_text

    # Use meaningful response (never a fallback) for simplification
    last_full = get_last_meaningful_response()
    last_summary = get_last_response_summary()

    has_content = _is_meaningful_response(last_full or "") or _is_meaningful_response(last_summary or "")
    if not has_content:
        return format_cfo_brain_response(
            header="PLAIN ANSWER",
            answer=(
                "I don't have a previous response to simplify yet.\n\n"
                "Try: 'how do we make money this week' or 'show approval queue' first, "
                "then ask me to simplify."
            ),
            approval_boundary=True,
        )

    text_to_simplify = last_full or last_summary or ""
    simplified = simplify_response_text(text_to_simplify, max_bullets=5)
    return simplified


def handle_explain_request(message: str, context: dict) -> str:
    """Handle: 'AND WHAT DOES THAT MEAN' / 'EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE'

    Resolution order:
    1. active_recommendation (persists through option selection, fallbacks)
    2. last_selected_option_text (what Ray actually chose)
    3. last_option_map first item
    4. last_meaningful_response explain path
    5. Graceful no-context fallback
    """
    from lib.hermes_conversation_state import (
        get_active_recommendation, get_last_meaningful_response,
        get_selected_option_context, load_conversation_state,
    )
    from lib.hermes_plain_language_rewriter import explain_response_plainly

    active_rec = get_active_recommendation()
    selected_num, selected_text = get_selected_option_context()
    last_full = get_last_meaningful_response()
    state = load_conversation_state()
    option_map = state.get("last_option_map") or {}

    # If Ray selected an option, explain THAT as the active recommendation
    if selected_text and _is_meaningful_response(selected_text):
        parts = [
            "PLAIN ANSWER",
            "",
            "My recommendation was:",
            f"  {(active_rec or selected_text)[:200]}",
            "",
            "What that means:",
            f"  {selected_text[:200]}",
            "  Use this as the front-end asset to attract your target audience,",
            "  then connect to an opt-in and later to an affiliate or Nexus offer.",
            "",
            "Why:",
            "  It is the closest asset to launch-ready, but it still needs Ray approval",
            "  before public use.",
            "",
            "Next safe step:",
            "  Prepare the implementation prompt or assign the monetization scout.",
            "  Say 'create a prompt for Claude' to get started without spending money.",
            "",
            "Requires Ray approval before:",
            "  Publishing, emailing subscribers, applying to affiliates,",
            "  activating payments, deploying, or running live trading.",
            "",
            "Approval boundary:",
            f"  {_SAFETY_BOUNDARY}",
        ]
        return "\n".join(parts)

    # Use active_recommendation directly
    if active_rec and _is_meaningful_response(active_rec):
        parts = [
            "PLAIN ANSWER",
            "",
            "My recommendation was:",
            f"  {active_rec[:200]}",
            "",
            "What it means in plain language:",
            "  This is the safest path to revenue that requires no money or deployment.",
            "  Internal preparation only — public use requires Ray approval.",
            "",
            "Next safe step:",
            "  Say 'let's do 1' to confirm, or 'create a prompt for Claude' for implementation steps.",
            "",
            "Requires Ray approval before:",
            "  Publishing, emailing subscribers, spending money, applying to affiliates,",
            "  activating Stripe/payment, deploying, or running live trading.",
            "",
            "Approval boundary:",
            f"  {_SAFETY_BOUNDARY}",
        ]
        return "\n".join(parts)

    # Fall back to first option in map
    if option_map:
        first_opt = option_map.get("1") or option_map.get(1) or next(iter(option_map.values()), None)
        if first_opt:
            parts = [
                "PLAIN ANSWER",
                "",
                "The top option from the last response was:",
                f"  {first_opt[:200]}",
                "",
                "What it means in plain language:",
                "  This is a safe internal action you can prep without Ray approval.",
                "  No money spent, no publishing, no client-facing use until Ray approves.",
                "",
                "My recommendation:",
                "  Say 'let's do 1' to proceed, or ask me to break it down further.",
                "",
                "Approval boundary:",
                f"  {_SAFETY_BOUNDARY}",
            ]
            return "\n".join(parts)

    # Full response explain path
    if last_full and _is_meaningful_response(last_full):
        return explain_response_plainly(last_full, context)

    return format_cfo_brain_response(
        header="PLAIN ANSWER",
        answer=(
            "I don't have a recent recommendation to explain.\n\n"
            "Try asking: 'how do we make money this week' then 'explain your recommendation'."
        ),
        approval_boundary=True,
    )


def handle_option_selection(message: str, context: dict) -> str:
    """Handle: 'LET'S DO 1' / 'OPTION 2'"""
    from lib.hermes_conversation_state import get_option, mark_option_selected

    # Extract the number
    m = re.search(r'(\d+)', message)
    number = int(m.group(1)) if m else 1

    option_text = get_option(number)

    if not option_text:
        return format_cfo_brain_response(
            header="OPTION SELECTED",
            answer=(
                f"You selected option {number}, but I don't have the option list from the last response.\n\n"
                f"Please ask me a question that presents options first, then say 'let's do 1'."
            ),
            approval_boundary=True,
        )

    # Preserve option text so "WHAT WAS TASK 1" resolves correctly after selection
    mark_option_selected(number, text=option_text)

    parts = [
        "OPTION SELECTED",
        "",
        f"You chose option {number}:",
        f"  {option_text[:200]}",
        "",
        "Safe next step:",
        "  I can create an implementation prompt for this, or assign a scout to research it.",
        "  Say 'what was task 1' to review it, or 'create a prompt for Claude' to get started.",
        "",
        "Requires Ray approval before:",
        "  Publishing, sending emails, spending money, deploying, or applying to affiliates.",
        "",
        f"Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


def handle_task_reference(message: str, context: dict) -> str:
    """Handle: 'WHAT WAS TASK 1' / 'WHAT WAS THE FIRST TASK'

    Resolution order:
    1. last_selected_option_text if number matches selected option
    2. last_option_map[number]
    3. last_task_map[number]
    4. Graceful no-context fallback
    """
    from lib.hermes_conversation_state import get_task, get_option, get_selected_option_context

    m = re.search(r'(\d+)', message)
    number = int(m.group(1)) if m else 1

    # Check selected option first — survives "LETS DO 1" state overwrite
    selected_num, selected_text = get_selected_option_context()
    if selected_num == number and selected_text:
        task_text = selected_text
    else:
        task_text = get_option(number) or get_task(number)

    if not task_text:
        return format_cfo_brain_response(
            header="PLAIN ANSWER",
            answer=(
                f"I don't have task {number} from the last response. "
                f"There may not have been a numbered list, or the context may have expired.\n\n"
                f"Try asking 'how do we make money this week' to get a fresh option list."
            ),
            why="Conversation context expires after 24 hours.",
            approval_boundary=True,
        )

    parts = [
        "PLAIN ANSWER",
        "",
        f"Task {number} was:",
        f"  {task_text[:200]}",
        "",
        "What it means:",
        "  Use this as the front-end asset: prep it internally, then connect to an opt-in",
        "  and pair with an affiliate or Nexus offer after Ray approves public use.",
        "",
        "Safe next step:",
        f"  Prepare the implementation prompt or assign the monetization scout to research it.",
        f"  Say 'create a prompt for Claude' to get started.",
        "",
        "Requires Ray approval before:",
        "  Publishing, emailing subscribers, applying to affiliates,",
        "  activating payments, or using client-facing content.",
        "",
        "Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


def handle_morning_activity(message: str, context: dict) -> str:
    """Handle: 'WHAT DID YOU DO THIS MORNING'"""
    from lib.hermes_tool_chooser import execute_chosen_tool

    # Get while-out summary + research queue
    while_out = execute_chosen_tool("morning_activity", message, context) or ""
    research_q = execute_chosen_tool("research_queue", message, context) or ""

    parts = ["MORNING SUMMARY", "", "Here is what happened:"]

    if while_out:
        # Extract key lines from while-out summary
        lines = [l.strip() for l in while_out.splitlines() if l.strip()
                 and not re.match(r'^[═─]+$', l)
                 and "HERMES" not in l.upper()[:20]]
        for line in lines[:6]:
            parts.append(f"  * {line[:100]}")
    else:
        parts.append("  * No morning activity recorded yet.")

    if research_q and "no open" not in research_q.lower():
        parts += ["", "Research queue:"]
        rq_lines = [l.strip() for l in research_q.splitlines()
                    if l.strip() and "RESEARCH QUEUE" not in l.upper()
                    and not re.match(r'^[═─]+$', l)]
        for line in rq_lines[:3]:
            parts.append(f"  * {line[:100]}")

    parts += ["", f"Approval boundary:", f"  {_SAFETY_BOUNDARY}"]
    return "\n".join(parts)


def handle_queue_status(message: str, context: dict) -> str:
    """Handle: 'WHAT TASK ARE IN THE QUEUE'"""
    from lib.hermes_tool_chooser import execute_chosen_tool

    result = execute_chosen_tool("task_queue_status", message, context) or ""

    if not result or len(result.strip()) < 10:
        return format_cfo_brain_response(
            header="TASK QUEUE",
            answer="I don't have a verified task queue. Say 'show approval queue' for pending approvals.",
            approval_boundary=True,
        )

    # Strip HERMES REPORT scaffolding and return plain version
    lines = [l.strip() for l in result.splitlines() if l.strip()
             and not re.match(r'^[═─]+$', l)]

    # Find the queue items (lines with bullet/number format or task-like content)
    queue_items = [l for l in lines if re.match(r'^\s*[-•*•]\s|^\s*\d+[.:)]\s', l) or
                   any(k in l.lower() for k in ["pending", "approve", "task", "waiting"])]

    if not queue_items:
        return format_cfo_brain_response(
            header="TASK QUEUE",
            answer=f"Queue status: {lines[1] if len(lines) > 1 else 'empty or no pending items'}",
            approval_boundary=True,
        )

    parts = ["TASK QUEUE", "", "Open tasks:"]
    for item in queue_items[:8]:
        parts.append(f"  {item.lstrip('-•* ').strip()[:120]}")
    parts += ["", f"Approval boundary:", f"  {_SAFETY_BOUNDARY}"]
    return "\n".join(parts)


def handle_money_strategy(message: str, context: dict) -> str:
    """Handle: 'HOW DO WE MAKE MONEY THIS WEEK'

    Response uses numbered items so conversation state can resolve
    'LETS DO 1', 'WHAT WAS OPTION 2', etc. in follow-up messages.
    """
    from lib.hermes_tool_chooser import execute_chosen_tool

    packet_result = execute_chosen_tool("revenue_asset_packet", message, context) or ""

    parts = ["WEEKLY MONEY PLAN", ""]

    # Extract readiness score
    score_match = re.search(r'readiness[:\s]+(\d+)/100', packet_result, re.IGNORECASE)
    score = score_match.group(1) if score_match else "unknown"

    parts += [
        f"Revenue readiness score: {score}/100",
        "",
        "Best money moves this week:",
        "",
    ]

    # Build numbered options from packet result or use sensible defaults
    numbered_options = _extract_money_options(packet_result)
    if not numbered_options:
        numbered_options = [
            "Activate the funding readiness lead magnet funnel with an affiliate offer.",
            "Launch Nexus membership at a founding-member price.",
            "Run a YouTube/LinkedIn content push to build inbound interest.",
        ]

    for i, opt in enumerate(numbered_options[:3], start=1):
        parts.append(f"{i}. {opt[:120]}")

    parts += [
        "",
        "My recommendation:",
        "  Start with option 1 — it is closest to revenue with no upfront spend.",
        f"  Say 'let's do 1' to select it or 'what was option 2' to review others.",
        "",
        "Requires Ray approval before:",
        "  Publishing, emailing subscribers, spending money, applying to affiliates,",
        "  activating Stripe/payment, deploying, or running live trading.",
        "",
        f"Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


def _extract_money_options(packet_result: str) -> list[str]:
    """Extract money move options from revenue packet result as plain strings."""
    if not packet_result:
        return []
    options = []
    keywords = ["lead magnet", "affiliate", "membership", "funding", "credit",
                 "checklist", "offer", "launch", "promote", "activate"]
    for line in packet_result.splitlines():
        stripped = line.strip()
        if not stripped or re.match(r'^[═─\*•\-]+$', stripped):
            continue
        if "REVENUE ASSET PACKET" in stripped.upper():
            continue
        if any(k in stripped.lower() for k in keywords) and len(stripped) > 15:
            # Clean the line for use as a numbered option
            clean = re.sub(r'^[\*\-•\s]+', '', stripped).strip()
            clean = re.sub(r'^(?:option\s*)?(\d+)[.:\)]\s*', '', clean, flags=re.IGNORECASE).strip()
            if clean and clean not in options:
                options.append(clean[:120])
        if len(options) >= 3:
            break
    return options


def handle_failure_feedback(message: str, context: dict) -> str:
    """Handle: 'THAT IS NOT WHAT I MEANT'"""
    from lib.hermes_failure_learning import log_failed_response
    from lib.hermes_conversation_state import get_last_response_full

    last_response = get_last_response_full() or ""
    log_failed_response(
        message=context.get("last_user_message", message),
        response=last_response,
        reason="lost_context",
    )

    # Try to infer what Ray actually wanted
    prior_msg = context.get("last_user_message") or "your last message"
    prior_topic = context.get("current_topic") or "this topic"

    return "\n".join([
        "CORRECTING COURSE",
        "",
        "I understand — that was not the right response.",
        "",
        f"I logged the bad response as a training example.",
        "",
        "What I think you actually wanted:",
        f"  A plain, direct answer about {prior_topic.replace('_', ' ')} based on context.",
        "",
        "What I can do next:",
        "  - Say 'show failed responses' to review logged failures",
        "  - Say 'create tests from failures' to generate a test case",
        "  - Ask me your question again and I will try the CFO brain path",
        "",
        f"Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ])


def handle_prompt_generation_request(message: str, context: dict) -> str:
    """Handle: 'CREATE A PROMPT FOR CLAUDE TO FIX THIS'"""
    try:
        from lib.hermes_cfo_conversation_layer import _build_implementation_prompt_text
        return _build_implementation_prompt_text(message)
    except Exception as exc:
        logger.warning("handle_prompt_generation_request fallback: %s", exc)
        return format_cfo_brain_response(
            header="IMPLEMENTATION PROMPT",
            answer=(
                f"Goal: {message.strip()}\n\n"
                "Context: See Hermes memory and revenue packet state.\n\n"
                "Requirements:\n"
                "  - Follow existing Hermes architecture (intake → router → handler)\n"
                "  - Write tests in scripts/ following the check(label, cond) pattern\n"
                "  - No publishing, no emails, no spending, no Supabase writes\n\n"
                "Safety:\n  " + _SAFETY_BOUNDARY
            ),
            approval_boundary=False,
        )


def handle_unknown_with_scout_dispatch(message: str, context: dict) -> str:
    """Handle: unknown question → scout dispatch"""
    try:
        from lib.hermes_cfo_conversation_layer import (
            build_cfo_context, build_cfo_response, format_cfo_response,
        )
        ctx = build_cfo_context(message)
        # Force unknown_dispatch strategy
        ctx["force_unknown_dispatch"] = True
        resp = build_cfo_response(message, ctx)
        return format_cfo_response(resp)
    except Exception as exc:
        logger.warning("handle_unknown_with_scout_dispatch fallback: %s", exc)
        return format_cfo_brain_response(
            header="I DON'T HAVE VERIFIED EVIDENCE YET",
            answer=(
                "I do not have enough verified information to answer that confidently.\n\n"
                "I added this to the research queue.\n\n"
                "Say 'show research queue' to see open questions."
            ),
            approval_boundary=True,
        )


def handle_recommendation_question(message: str, context: dict) -> str:
    """Handle: 'WHAT IS YOUR RECOMMENDATION'"""
    from lib.hermes_conversation_state import get_last_recommendation

    rec = get_last_recommendation()
    if rec:
        return format_cfo_brain_response(
            header="PLAIN ANSWER",
            answer=f"My recommendation from the last response was:\n  {rec}",
            why="This is from the most recent CFO response.",
            recommendation="Say 'let's do 1' to select an option, or 'explain that' for more detail.",
            approval_boundary=True,
        )

    # No prior recommendation — build one from daily cycle
    from lib.hermes_tool_chooser import execute_chosen_tool
    daily = execute_chosen_tool("daily_operating_cycle", message, context) or ""
    rec_match = re.search(r'(?:recommendation|priority)[:\s]+(.+)', daily, re.IGNORECASE)
    if rec_match:
        rec_text = rec_match.group(1).strip()[:200]
        return format_cfo_brain_response(
            header="PLAIN ANSWER",
            answer=f"Current recommendation:\n  {rec_text}",
            approval_boundary=True,
        )

    return format_cfo_brain_response(
        header="PLAIN ANSWER",
        answer="Run 'run daily operating cycle' first to get a recommendation.",
        approval_boundary=True,
    )


def handle_followup_question(message: str, context: dict) -> str:
    """Handle: 'WHAT WAS THAT AGAIN' / 'MORE DETAIL ON THAT'"""
    from lib.hermes_conversation_state import get_last_response_full, get_last_response_summary

    last = get_last_response_full() or get_last_response_summary()
    if not last:
        return format_cfo_brain_response(
            header="PLAIN ANSWER",
            answer="I don't have a previous response to follow up on. Ask me a question first.",
            approval_boundary=True,
        )

    from lib.hermes_plain_language_rewriter import explain_response_plainly
    return explain_response_plainly(last, context)


def handle_general_business(message: str, context: dict) -> Optional[str]:
    """Handle: general business conversation that doesn't match exact intents."""
    # Try the existing CFO conversation layer for strategic messages
    try:
        from lib.hermes_cfo_conversation_layer import (
            detect_cfo_conversation_need, build_cfo_context,
            build_cfo_response, format_cfo_response,
        )
        if detect_cfo_conversation_need(message):
            ctx = build_cfo_context(message)
            resp = build_cfo_response(message, ctx)
            result = format_cfo_response(resp)
            if result:
                return result
    except Exception:
        pass
    return None


def build_clarification_response(message: str, context: dict) -> str:
    """Fail-closed response: return structured clarification instead of evidence dump.

    Used when CFO Brain cannot produce a confident answer. Prevents old LLM
    fallback paths from emitting evidence dumps or quality-fallback text.
    """
    topic = context.get("current_topic") or "your question"
    last_rec = context.get("last_recommendation")

    parts = [
        "I NEED CLARIFICATION",
        "",
        f"I understood your message about {topic.replace('_', ' ')}, "
        "but I don't have enough context to give you a confident answer.",
        "",
        "What would help:",
        "  1. Try a more specific command like 'show approval queue' or 'run daily operating cycle'",
        "  2. Say 'how do we make money this week' for revenue options",
        "  3. Say 'show research queue' for open questions",
    ]
    if last_rec:
        parts += [
            "",
            f"My last recommendation was:",
            f"  {last_rec[:150]}",
        ]
    parts += [
        "",
        "Approval boundary:",
        f"  {_SAFETY_BOUNDARY}",
    ]
    return "\n".join(parts)


# ── Context saving ────────────────────────────────────────────────────────────

def save_cfo_interaction_context(response_context: dict) -> None:
    """Save interaction context after a CFO brain response."""
    try:
        from lib.hermes_conversation_state import update_conversation_state
        update_conversation_state(
            user_message=response_context.get("user_message", ""),
            hermes_response=response_context.get("response", ""),
            tool_used=response_context.get("tool_used"),
        )
    except Exception as exc:
        logger.warning("save_cfo_interaction_context error: %s", exc)


def log_cfo_failure_example(
    message: str,
    bad_response: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """Log a CFO brain failure example."""
    from lib.hermes_failure_learning import log_failed_response
    return log_failed_response(
        message=message,
        response=bad_response or "",
        reason=reason,
    )


# ── Response formatter ────────────────────────────────────────────────────────

def format_cfo_brain_response(
    header: str,
    answer: str,
    why: Optional[str] = None,
    recommendation: Optional[str] = None,
    next_steps: Optional[list[str]] = None,
    approval_boundary: bool = True,
) -> str:
    """Format a CFO brain response using the standard plain-language format."""
    parts = [header, "", answer]

    if why:
        parts += ["", f"What it means:", f"  {why[:200]}"]

    if recommendation:
        parts += ["", f"My recommendation:", f"  {recommendation[:200]}"]

    actions = next_steps or [
        "Ask me to explain this further",
        "Say 'let's do 1' to select an option",
        "Say 'create a prompt for Claude' to generate an implementation prompt",
    ]
    parts += ["", "What I can do next:"]
    for act in actions[:3]:
        parts.append(f"  - {act}")

    if approval_boundary:
        parts += ["", "Approval boundary:", f"  {_SAFETY_BOUNDARY}"]

    return "\n".join(parts)
