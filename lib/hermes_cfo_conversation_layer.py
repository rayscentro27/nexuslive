"""
hermes_cfo_conversation_layer.py
Phase 7: Hermes CFO Conversation Layer

Purpose: Handle natural Ray messages that are not exact commands.
Hermes should act like a CFO/operator — understand the real concern,
respond in plain language, separate knowns from unknowns, give options,
make a recommendation, assign scouts for unknowns, and generate
implementation prompts when needed.

Safety: Never publishes, emails, spends, deploys, applies to affiliates,
activates Stripe, or runs live trading without explicit Ray approval.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent

# ── Report dirs ──────────────────────────────────────────────────────────────
_RESEARCH_QUEUE_DIR = _ROOT / "docs" / "reports" / "research_queue"
_STRATEGY_DIR       = _ROOT / "docs" / "reports" / "strategy"

SAFETY_BOUNDARY = (
    "I will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, activate Stripe, run live trading, or "
    "use client-facing content without explicit Ray approval."
)

# ── Conversation categories ───────────────────────────────────────────────────
CFO_CATEGORIES = {
    "strategic_concern":       "Strategic concern or worry about the business",
    "product_direction":       "Question about product/platform direction",
    "monetization_strategy":   "Monetization, revenue, pricing, offers",
    "hermes_behavior_feedback":"Feedback about how Hermes behaves or responds",
    "implementation_planning": "Request to plan or implement something",
    "unknown_answer":          "Question Hermes cannot answer confidently",
    "risk_review":             "Risk, compliance, or safety review",
    "launch_decision":         "Decision about launching something",
    "pricing_decision":        "Pricing or offer structure decision",
    "scout_delegation":        "Request to research or investigate something",
    "general_business_question":"General business, operations, or strategy question",
}

# ── Scout mapping ─────────────────────────────────────────────────────────────
_SCOUT_MAP: dict[str, list[str]] = {
    "monetization_strategy":   ["monetization_scout", "affiliate_monetization_scout"],
    "content_strategy":        ["content_intelligence_scout"],
    "funding_credit":          ["credit_repair_research_scout", "funding_opportunity_scout"],
    "technical_system":        ["system_reliability_scout"],
    "trading_research":        ["trading_research_scout"],
    "product_direction":       ["strategy_scout"],
    "customer_research":       ["market_research_scout"],
    "external_real_time_info": ["external_research_scout"],
    "hermes_behavior_feedback": ["hermes_behavior_scout", "system_reliability_scout"],
    "unknown_general":         ["general_research_scout"],
}

# ── Classification keyword maps ───────────────────────────────────────────────
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "hermes_behavior_feedback": [
        "hermes", "command bot", "cfo", "operator", "chatgpt", "conversation",
        "natural", "feel like", "relationship", "talks to me", "respond like",
        "act like", "feels like", "too robotic", "not natural",
    ],
    "monetization_strategy": [
        "monetize", "revenue", "money", "earn", "affiliate", "offer", "pricing",
        "stripe", "subscription", "sell", "income", "make money", "revenue goal",
        "1000 a week", "$1k", "commission",
    ],
    "product_direction": [
        "product", "platform", "feature", "build", "direction", "roadmap",
        "phase", "nexus", "what should we build", "next feature",
    ],
    "implementation_planning": [
        "implement", "build", "create", "fix", "prompt", "claude", "opencode",
        "super prompt", "give me a prompt", "turn this into", "code",
    ],
    "launch_decision": [
        "launch", "ship", "go live", "release", "publish", "deploy",
        "ready to launch", "when should we", "are we ready",
    ],
    "pricing_decision": [
        "price", "pricing", "how much", "charge", "tier", "plan", "cost",
        "what should we charge", "membership fee",
    ],
    "risk_review": [
        "risk", "safe", "danger", "compliance", "legal", "concern",
        "worried about", "could this break", "is this okay",
    ],
    "scout_delegation": [
        "research", "find out", "investigate", "look into", "figure out",
        "can your scouts", "what do you know about", "find the best",
    ],
    "strategic_concern": [
        "worried", "concern", "problem", "issue", "not working", "struggling",
        "behind", "stuck", "challenge", "difficult", "not sure",
    ],
}

# ── Detect if message needs CFO handling ─────────────────────────────────────

_EXACT_COMMAND_SIGNALS = re.compile(
    r"^(show|run|build|create|fix|rescore|improve|generate|approve|reject|"
    r"record|add|remove|apply|update|refresh|check|list|display|get)\s",
    re.IGNORECASE,
)


def detect_cfo_conversation_need(message: str) -> bool:
    """Return True if the message needs CFO conversational handling.

    Returns False for exact command phrases so existing handlers run first.
    """
    if not message or len(message.strip()) < 5:
        return False
    msg = message.strip().lower()
    # Starts with a command verb → let command router handle
    if _EXACT_COMMAND_SIGNALS.match(msg):
        return False
    # Short single-word messages
    if len(msg.split()) <= 2:
        return False
    # Contains question mark or concern language → CFO
    if "?" in msg:
        return True
    # Check for CFO category keywords
    for keywords in _CATEGORY_KEYWORDS.values():
        if any(k in msg for k in keywords):
            return True
    # Longer conversational sentences
    if len(msg.split()) > 8:
        return True
    return False


def classify_cfo_conversation(message: str) -> str:
    """Classify message into a CFO conversation category."""
    msg = message.lower()
    best_cat = "general_business_question"
    best_score = 0
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for k in keywords if k in msg)
        if score > best_score:
            best_score = score
            best_cat = cat
    return best_cat


def build_cfo_context(message: str) -> dict:
    """Build context dict from available Hermes memory and artifacts."""
    context: dict = {
        "category": classify_cfo_conversation(message),
        "memory_v2_active": False,
        "daily_plan_available": False,
        "revenue_packet_score": None,
        "approval_queue_count": 0,
        "open_gaps": 0,
        "last_daily_plan": None,
    }
    # Try to read memory v2 status
    try:
        from lib.hermes_memory_v2 import get_memory_v2_primary_status
        status = get_memory_v2_primary_status()
        context["memory_v2_active"] = status.get("primary_active", False)
    except Exception:
        pass
    # Try to get current revenue packet score
    try:
        from lib.hermes_revenue_asset_packet import load_latest_revenue_asset_packet
        packet = load_latest_revenue_asset_packet()
        if packet:
            context["revenue_packet_score"] = packet.get("readiness_score")
    except Exception:
        pass
    # Try to get approval queue count
    try:
        from lib.hermes_approval_queue import load_approval_queue
        queue = load_approval_queue()
        context["approval_queue_count"] = len([
            i for i in (queue or []) if i.get("status") == "pending"
        ])
    except Exception:
        pass
    return context


def separate_knowns_unknowns(message: str, context: dict) -> dict:
    """Return dict with known facts and unknown items for the message."""
    category = context.get("category", "general_business_question")
    knowns: list[str] = []
    unknowns: list[str] = []

    # Category-specific known/unknown logic
    if category == "hermes_behavior_feedback":
        knowns += [
            "Hermes currently routes messages through an intent classifier before generating responses",
            "Exact commands are matched and handled by dedicated handler functions",
            "When no exact command matches, Hermes falls back to evidence dumps or generic responses",
        ]
        unknowns += [
            "How often Ray sends natural-language messages that fall through to evidence dumps",
            "Which specific response patterns feel most like a command bot vs a CFO",
        ]
    elif category == "monetization_strategy":
        score = context.get("revenue_packet_score")
        if score is not None:
            knowns.append(f"Revenue packet readiness score is {score}/100")
        knowns.append("30-Day Revenue Goal is $1,000/week from business funding education")
        unknowns += [
            "Which affiliate offer converts best for the funding-readiness audience",
            "Optimal pricing for Nexus membership tiers",
        ]
    elif category == "product_direction":
        knowns.append("Nexus platform has Phases 1–7 defined with feature flags and invite system")
        unknowns.append("User feedback on current feature priority")
    else:
        knowns.append("Current platform and memory system state is available")
        unknowns.append("Verified external data for this specific question")

    return {"knowns": knowns, "unknowns": unknowns}


def select_cfo_response_strategy(message: str, context: dict) -> str:
    """Choose response strategy: cfo_response | unknown_dispatch | implementation_prompt."""
    category = context.get("category", "general_business_question")
    msg_lower = message.lower()

    # Implementation prompt requested
    if any(k in msg_lower for k in [
        "give me a prompt", "create the prompt", "have opencode", "turn this into",
        "create a super prompt", "what should i send claude", "create a prompt",
        "implementation prompt",
    ]):
        return "implementation_prompt"

    # No knowns at all → dispatch to scout
    ku = separate_knowns_unknowns(message, context)
    if not ku["knowns"] and ku["unknowns"]:
        return "unknown_dispatch"

    return "cfo_response"


def build_cfo_response(message: str, context: dict) -> dict:
    """Build the full CFO response dict."""
    strategy = select_cfo_response_strategy(message, context)
    category = context.get("category", "general_business_question")
    ku = separate_knowns_unknowns(message, context)

    if strategy == "implementation_prompt":
        return _build_implementation_prompt_response(message, context)

    if strategy == "unknown_dispatch":
        return _build_unknown_dispatch_response(message, context)

    # Standard CFO response
    options = _build_options(message, category)
    recommendation = _build_recommendation(message, category)
    next_steps = _build_next_steps(message, category, context)

    return {
        "strategy": "cfo_response",
        "category": category,
        "real_issue": _frame_real_issue(message, category),
        "knowns": ku["knowns"],
        "unknowns": ku["unknowns"],
        "options": options,
        "recommendation": recommendation,
        "next_steps": next_steps,
        "safety_boundary": SAFETY_BOUNDARY,
        "created_at": _now_iso(),
    }


def _frame_real_issue(message: str, category: str) -> str:
    """Return plain-language framing of the real issue."""
    if category == "hermes_behavior_feedback":
        return (
            "Hermes is behaving like a command dispatcher — it only responds well when given "
            "exact phrases. Ray wants Hermes to respond like a CFO or strategic operator: "
            "understand intent, give options, make recommendations, and delegate unknowns."
        )
    elif category == "monetization_strategy":
        return (
            "The revenue system has content and a readiness score, but no active revenue "
            "flow yet. The core question is: which action turns internal readiness into "
            "actual income this week."
        )
    elif category == "product_direction":
        return (
            "The platform has multiple phases of features, but it's unclear which direction "
            "will move the revenue goal fastest."
        )
    elif category == "launch_decision":
        return (
            "Before launching, we need to confirm the asset is approval-ready, "
            "compliance notes are in place, and Ray has explicitly approved."
        )
    elif category == "risk_review":
        return (
            "A potential risk has been identified that needs review before proceeding."
        )
    else:
        return (
            f"Ray raised a question in the category '{category}' that deserves a "
            "clear, evidence-based response."
        )


def _build_options(message: str, category: str) -> list[str]:
    """Return 2–3 concrete options for the situation."""
    if category == "hermes_behavior_feedback":
        return [
            "Add CFO conversation layer: detect natural messages and respond with structured strategic analysis",
            "Add scout dispatch: when Hermes can't answer, assign a research scout and add to queue",
            "Combine both: CFO layer handles strategy, scouts handle unknowns, exact commands still work",
        ]
    elif category == "monetization_strategy":
        return [
            "Activate the funding readiness lead magnet funnel with an affiliate offer",
            "Launch Nexus membership at a founding-member price for early subscribers",
            "Run a YouTube/LinkedIn content push to build the email list first",
        ]
    elif category == "product_direction":
        return [
            "Focus on the revenue funnel: lead magnet → email list → offer",
            "Focus on Nexus platform features: credit tracking, funding readiness dashboard",
            "Focus on Hermes intelligence: scouts, CFO layer, daily briefings",
        ]
    else:
        return [
            "Research the question and return with verified evidence",
            "Make a provisional decision with current information and revisit when more data is available",
            "Delegate to the appropriate scout and add to research queue",
        ]


def _build_recommendation(message: str, category: str) -> str:
    """Return a single clear recommendation."""
    if category == "hermes_behavior_feedback":
        return (
            "Add the CFO conversation layer now. This gives Hermes strategic response capability "
            "without breaking any existing commands. It runs after exact command handlers, "
            "before evidence dumps."
        )
    elif category == "monetization_strategy":
        return (
            "Start with the lead magnet funnel: the content is ready and scored 100/100. "
            "The next step is Ray approving the asset for public use, then connecting it "
            "to an offer."
        )
    elif category == "product_direction":
        return (
            "Focus on the revenue funnel first. Platform features can be added after "
            "the first $1K/week is running."
        )
    else:
        return (
            "Assign a scout to research this, add the question to the research queue, "
            "and return with verified evidence before making a decision."
        )


def _build_next_steps(message: str, category: str, context: dict) -> list[str]:
    """Return list of safe internal next steps."""
    steps = []
    if category == "hermes_behavior_feedback":
        steps += [
            "Build CFO conversation layer (lib/hermes_cfo_conversation_layer.py)",
            "Add unknown-answer scout dispatch protocol",
            "Add research queue tracking",
            "Wire into router fallback (after exact commands, before evidence dumps)",
        ]
    elif category == "monetization_strategy":
        steps += [
            "Review revenue packet approval queue (say 'show approval queue')",
            "Identify top lead magnet for approval",
            "Research affiliate offer options (assign monetization_scout)",
        ]
    elif category == "implementation_planning":
        steps.append("Generate implementation prompt for Claude/OpenCode")
    else:
        steps += [
            "Add question to research queue",
            "Assign appropriate scout",
            "Return when scout has evidence",
        ]
    steps.append("I can create the OpenCode/Claude prompt for this if you want to implement it.")
    return steps


# ── Implementation prompt builder ────────────────────────────────────────────

def create_implementation_prompt_if_needed(message: str, recommendation: str) -> Optional[str]:
    """Generate an implementation prompt if the message requests one."""
    msg_lower = message.lower()
    if not any(k in msg_lower for k in [
        "give me a prompt", "create the prompt", "have opencode",
        "turn this into", "create a super prompt", "what should i send claude",
        "create a prompt", "implementation prompt",
    ]):
        return None
    return _build_implementation_prompt_text(message, recommendation)


def _build_implementation_prompt_text(message: str, context_note: str = "") -> str:
    return (
        "IMPLEMENTATION PROMPT\n\n"
        f"Goal: {message.strip()}\n\n"
        f"Context: {context_note or 'See Hermes memory and revenue packet state.'}\n\n"
        "Requirements:\n"
        "  - Follow existing Hermes architecture (intake → router → handler)\n"
        "  - Add to _PLAIN_INTENTS and _EVIDENCE_DUMP_BLOCKED_PHRASES\n"
        "  - Write tests in scripts/ following the check(label, cond) pattern\n"
        "  - No publishing, no emails, no spending, no Supabase writes\n\n"
        "Safety:\n"
        f"  {SAFETY_BOUNDARY}\n\n"
        "Tests:\n"
        "  - Intent classification test\n"
        "  - Response header test\n"
        "  - Safety language test\n"
        "  - No evidence dump test\n\n"
        "Final report:\n"
        "  - Files changed\n"
        "  - Tests run and results\n"
        "  - Supabase writes: expected NO\n"
        "  - Old tables changed: expected NO\n"
        "  - Commit hash"
    )


def _build_implementation_prompt_response(message: str, context: dict) -> dict:
    """Build implementation prompt response dict."""
    rec = _build_recommendation(message, context.get("category", "general_business_question"))
    prompt_text = _build_implementation_prompt_text(message, rec)
    return {
        "strategy": "implementation_prompt",
        "category": context.get("category", "general_business_question"),
        "prompt_text": prompt_text,
        "safety_boundary": SAFETY_BOUNDARY,
        "created_at": _now_iso(),
    }


# ── Unknown answer / scout dispatch ─────────────────────────────────────────

def _build_unknown_dispatch_response(message: str, context: dict) -> dict:
    """Build unknown-answer scout dispatch response dict."""
    category = context.get("category", "general_business_question")
    scout = _select_scout(category)
    evidence_needed = _evidence_needed_for(message, category)

    # Persist to research queue
    entry = _add_to_research_queue(message, scout, evidence_needed)

    return {
        "strategy": "unknown_dispatch",
        "category": category,
        "scout": scout,
        "evidence_needed": evidence_needed,
        "research_id": entry.get("research_id", ""),
        "safety_boundary": SAFETY_BOUNDARY,
        "created_at": _now_iso(),
    }


def _select_scout(category: str) -> str:
    """Select the best scout for the category."""
    scout_list = _SCOUT_MAP.get(category, _SCOUT_MAP["unknown_general"])
    return scout_list[0] if scout_list else "general_research_scout"


def _evidence_needed_for(message: str, category: str) -> list[str]:
    """Return list of evidence items needed to answer the question."""
    base = [
        f"Verified answer to: {message.strip()[:120]}",
        f"Sources or artifacts supporting the answer",
        f"Decision Hermes should prepare based on the answer",
    ]
    if category == "monetization_strategy":
        base.append("Best affiliate offer for funding-readiness audience with conversion data")
    elif category == "hermes_behavior_feedback":
        base.append("Examples of Hermes responses that felt like a command bot vs CFO")
    elif category == "product_direction":
        base.append("User feedback or market signal on which features drive revenue")
    return base


def create_scout_tasks_for_unknowns(message: str, unknowns: list[str]) -> list[dict]:
    """Create internal scout task records for unresolved unknowns."""
    tasks = []
    for unk in unknowns:
        category = classify_cfo_conversation(unk)
        scout = _select_scout(category)
        task = {
            "research_question": unk,
            "scout": scout,
            "status": "open",
            "source_message": message[:200],
            "created_at": _now_iso(),
        }
        tasks.append(task)
        _append_scout_assignment(task)
    return tasks


# ── Research queue persistence ────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _research_queue_path() -> Path:
    _RESEARCH_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return _RESEARCH_QUEUE_DIR / "hermes_research_queue.jsonl"


def _scout_assignments_path() -> Path:
    _RESEARCH_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return _RESEARCH_QUEUE_DIR / "hermes_scout_assignments.jsonl"


def _unknown_gaps_path() -> Path:
    _RESEARCH_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    return _RESEARCH_QUEUE_DIR / "hermes_unknown_answer_gaps.jsonl"


def _add_to_research_queue(message: str, scout: str, evidence_needed: list[str]) -> dict:
    """Append question to hermes_research_queue.jsonl."""
    entry = {
        "research_id": f"rq_{_now_ts()}",
        "question": message.strip()[:300],
        "scout": scout,
        "evidence_needed": evidence_needed,
        "status": "open",
        "created_at": _now_iso(),
    }
    try:
        with _research_queue_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as exc:
        logger.warning("_add_to_research_queue error: %s", exc)
    # Also log to unknown gaps
    try:
        with _unknown_gaps_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "gap": message.strip()[:200],
                "status": "open",
                "created_at": _now_iso(),
            }) + "\n")
    except Exception as exc:
        logger.warning("_add_to_unknown_gaps error: %s", exc)
    return entry


def _append_scout_assignment(task: dict) -> None:
    """Append scout assignment to hermes_scout_assignments.jsonl."""
    try:
        with _scout_assignments_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(task) + "\n")
    except Exception as exc:
        logger.warning("_append_scout_assignment error: %s", exc)


def load_research_queue(status: str = "open") -> list[dict]:
    """Load research queue entries, optionally filtered by status."""
    path = _research_queue_path()
    if not path.exists():
        return []
    entries = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if status == "all" or entry.get("status") == status:
                    entries.append(entry)
            except json.JSONDecodeError:
                pass
    except Exception as exc:
        logger.warning("load_research_queue error: %s", exc)
    return entries


def load_scout_assignments() -> list[dict]:
    """Load all scout assignments."""
    path = _scout_assignments_path()
    if not path.exists():
        return []
    assignments = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                assignments.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    except Exception as exc:
        logger.warning("load_scout_assignments error: %s", exc)
    return assignments


# ── Decision saver ────────────────────────────────────────────────────────────

def save_cfo_decision_candidate(response: dict) -> dict:
    """Save CFO response as a decision candidate for Ray approval."""
    try:
        from lib.hermes_revenue_asset_packet import inject_approval_candidates
        candidate = {
            "_source_type": "cfo_decision",
            "title": f"CFO decision: {response.get('category', 'general')[:50]}",
            "summary": response.get("recommendation", response.get("real_issue", ""))[:200],
            "category": "strategic_decision",
            "source": "cfo_conversation_layer",
            "risk_level": "low",
            "approval_required_for": "Strategic decision requires Ray review before action.",
            "if_approved": "Hermes proceeds with recommended next steps.",
            "if_rejected": "Hermes does not take action.",
            "safe_internal_next_step": "Review CFO recommendation and decide.",
            "evidence_paths": [],
            "approval_boundary": SAFETY_BOUNDARY,
            "created_at": _now_iso(),
        }
        result = inject_approval_candidates([candidate])
        return result
    except Exception as exc:
        logger.warning("save_cfo_decision_candidate error: %s", exc)
        return {"added": 0, "error": str(exc)}


# ── Formatters ────────────────────────────────────────────────────────────────

def format_cfo_response(response: dict) -> str:
    """Format a CFO response dict as a readable Telegram message."""
    strategy = response.get("strategy", "cfo_response")

    if strategy == "implementation_prompt":
        return response.get("prompt_text", "IMPLEMENTATION PROMPT\n\nNo prompt generated.")

    if strategy == "unknown_dispatch":
        return _format_unknown_dispatch(response)

    return _format_standard_cfo(response)


def _format_standard_cfo(response: dict) -> str:
    lines = ["RAY, I UNDERSTAND THE CONCERN", ""]

    real_issue = response.get("real_issue", "")
    if real_issue:
        lines += [f"The real issue: {real_issue}", ""]

    knowns = response.get("knowns") or []
    if knowns:
        lines += ["What I know:", ""]
        for k in knowns:
            lines.append(f"  - {k}")
        lines.append("")

    unknowns = response.get("unknowns") or []
    if unknowns:
        lines += ["What I do not know yet:", ""]
        for u in unknowns:
            lines.append(f"  - {u}")
        lines.append("")

    options = response.get("options") or []
    if options:
        lines += ["Options:", ""]
        for i, opt in enumerate(options, 1):
            lines.append(f"  {i}. {opt}")
        lines.append("")

    recommendation = response.get("recommendation", "")
    if recommendation:
        lines += [f"My recommendation: {recommendation}", ""]

    next_steps = response.get("next_steps") or []
    if next_steps:
        lines += ["What I can do next:", ""]
        for step in next_steps:
            lines.append(f"  - {step}")
        lines.append("")

    lines += [
        "Approval boundary:",
        f"  {SAFETY_BOUNDARY}",
    ]

    # Learning loop: offer lesson recording when Ray gives behavior feedback
    if response.get("category") == "hermes_behavior_feedback":
        lines += [
            "",
            "Learning loop:",
            "  I can record this as a lesson so Hermes improves from this conversation.",
            "  Say: record this lesson: [what you want Hermes to do differently]",
            "  I will not auto-approve — Ray must say 'approve lesson' first.",
        ]

    return "\n".join(lines)


def _format_unknown_dispatch(response: dict) -> str:
    lines = [
        "I DON'T HAVE VERIFIED EVIDENCE YET",
        "",
        "Ray, I do not have enough verified information to answer that confidently.",
        "",
        "I am adding this to the research queue.",
        "",
        f"Research question:",
        f"  {response.get('category', 'general')} inquiry",
        "",
        f"Assigned scout: {response.get('scout', 'general_research_scout')}",
        "",
        "What the scout should find:",
        "",
    ]
    for item in (response.get("evidence_needed") or []):
        lines.append(f"  - {item}")
    lines += [
        "",
        "When to check back:",
        "  Ask 'show research queue' or 'what did the scouts find?'",
        "",
        "I will not guess or invent the answer.",
        "",
        f"Research ID: {response.get('research_id', '—')}",
        "",
        "Approval boundary:",
        f"  {SAFETY_BOUNDARY}",
    ]
    return "\n".join(lines)


# ── Research queue / scout formatters ────────────────────────────────────────

def format_research_queue() -> str:
    """Format the current research queue for display."""
    entries = load_research_queue(status="open")
    if not entries:
        return (
            "RESEARCH QUEUE\n\n"
            "No open research questions.\n\n"
            "When Hermes cannot answer a question confidently, it is added here."
        )
    lines = [f"RESEARCH QUEUE", "", f"{len(entries)} open question(s):", ""]
    for e in entries[:10]:
        lines += [
            f"ID:       {e.get('research_id', '?')}",
            f"Question: {e.get('question', '?')[:80]}",
            f"Scout:    {e.get('scout', '?')}",
            f"Status:   {e.get('status', '?')}",
            f"Created:  {e.get('created_at', '?')[:19]}",
            "",
        ]
    if len(entries) > 10:
        lines.append(f"... and {len(entries) - 10} more.")
    lines += [
        "Approval boundary:",
        f"  {SAFETY_BOUNDARY}",
    ]
    return "\n".join(lines)


def format_scout_assignments() -> str:
    """Format current scout assignments for display."""
    assignments = load_scout_assignments()
    if not assignments:
        return (
            "SCOUT ASSIGNMENTS\n\n"
            "No active scout assignments.\n\n"
            "Say 'show research queue' to see open questions."
        )
    lines = [f"SCOUT ASSIGNMENTS", "", f"{len(assignments)} assignment(s):", ""]
    for a in assignments[:10]:
        lines += [
            f"Scout:    {a.get('scout', '?')}",
            f"Question: {a.get('research_question', '?')[:80]}",
            f"Status:   {a.get('status', '?')}",
            f"Created:  {a.get('created_at', '?')[:19]}",
            "",
        ]
    if len(assignments) > 10:
        lines.append(f"... and {len(assignments) - 10} more.")
    lines += [
        "Approval boundary:",
        f"  {SAFETY_BOUNDARY}",
    ]
    return "\n".join(lines)


def format_unresolved_questions() -> str:
    """Format unresolved questions for display."""
    path = _unknown_gaps_path()
    if not path.exists():
        return (
            "UNRESOLVED QUESTIONS\n\n"
            "No unresolved questions on file.\n\n"
            "When Hermes encounters something it cannot answer, "
            "it is logged here."
        )
    entries = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    e = json.loads(line)
                    if e.get("status") == "open":
                        entries.append(e)
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    if not entries:
        return "UNRESOLVED QUESTIONS\n\nNo open unresolved questions."
    lines = [f"UNRESOLVED QUESTIONS", "", f"{len(entries)} open:", ""]
    for e in entries[:10]:
        lines += [
            f"  - {e.get('gap', '?')[:80]}",
            f"    Status: {e.get('status', '?')}  |  {e.get('created_at','')[:19]}",
            "",
        ]
    return "\n".join(lines)
