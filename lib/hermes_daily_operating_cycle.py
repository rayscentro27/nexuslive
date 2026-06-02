"""
hermes_daily_operating_cycle.py
Phase 6A: Hermes Manual Daily Operating Cycle

Produces one daily Nexus operating plan on demand (command-only, no automation).

Evidence priority:
  artifacts > action queue > decisions > source intake > memory v2 > lessons

Safety rules:
  - Do NOT publish, email, sell, deploy, spend money, apply to programs, trade live
  - Do NOT use old Executive Memory
  - Do NOT invent task status
  - Do NOT claim work was completed unless verified in artifacts/decisions
  - Approval boundaries must be explicit in every plan output
  - Only hermes_memory_v2 read (never written here)
  - No old Supabase tables accessed
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent

# ── Approval boundary (immutable) ────────────────────────────────────────────
APPROVAL_BOUNDARY = (
    "I will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, run live trading, or use client-facing "
    "content without Ray approval."
)

SAFE_INTERNAL_WORK = [
    "Review latest source intake",
    "Score monetization opportunities",
    "Prepare draft improvements",
    "Assign internal scout tasks",
    "Update action queue",
    "Log knowledge gaps",
    "Research strategies and sources",
    "Revise content drafts internally",
]

BLOCKED_ACTIONS = [
    "publish content",
    "email clients or subscribers",
    "spend money",
    "apply to affiliate programs",
    "deploy production changes",
    "run live trading",
    "use client-facing content without Ray approval",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── Input loaders (each is fault-tolerant) ───────────────────────────────────

def _load_goals() -> list[dict]:
    try:
        from lib.hermes_goal_registry import top_active_goals
        return [g.__dict__ if hasattr(g, "__dict__") else dict(g) for g in top_active_goals(limit=5)]
    except Exception as exc:
        logger.debug("_load_goals error: %s", exc)
        return []


def _load_memory_v2(limit: int = 20) -> list[dict]:
    try:
        from lib.hermes_memory_v2_reader import load_v2_active_live_answer_memory
        result = load_v2_active_live_answer_memory(limit=limit)
        if result.get("available"):
            return result.get("records", [])
    except Exception as exc:
        logger.debug("_load_memory_v2 error: %s", exc)
    return []


def _load_content_assets() -> list[dict]:
    try:
        from lib.hermes_monetization_today import find_current_content_assets
        assets = find_current_content_assets()
        return [dict(a) for a in assets]
    except Exception as exc:
        logger.debug("_load_content_assets error: %s", exc)
    return []


def _load_action_queue(limit: int = 10) -> list[dict]:
    try:
        from lib.hermes_action_queue import get_unique_open_actions, get_pending_approval_actions
        open_actions = get_unique_open_actions()
        pending = get_pending_approval_actions()
        combined: list[dict] = []
        seen: set[str] = set()
        for a in list(pending) + list(open_actions):
            aid = getattr(a, "action_id", None) or (a.get("action_id") if isinstance(a, dict) else None)
            if aid and aid not in seen:
                seen.add(aid)
                combined.append(a.__dict__ if hasattr(a, "__dict__") else dict(a))
        return combined[:limit]
    except Exception as exc:
        logger.debug("_load_action_queue error: %s", exc)
    return []


def _load_decisions(limit: int = 5) -> list[dict]:
    try:
        from lib.hermes_decision_log import load_recent_decisions
        decisions = load_recent_decisions(limit=limit)
        return [d.__dict__ if hasattr(d, "__dict__") else dict(d) for d in decisions]
    except Exception as exc:
        logger.debug("_load_decisions error: %s", exc)
    return []


def _load_source_intake(limit: int = 5) -> list[dict]:
    try:
        from lib.hermes_telegram_source_intake import get_recent_intakes
        intakes = get_recent_intakes(limit=limit)
        return [i.__dict__ if hasattr(i, "__dict__") else dict(i) for i in intakes]
    except Exception as exc:
        logger.debug("_load_source_intake error: %s", exc)
    return []


def _load_scouts() -> list[dict]:
    try:
        from lib.hermes_tool_scout_registry import get_scouts, get_available_tools
        scouts = get_scouts()
        return [s.__dict__ if hasattr(s, "__dict__") else dict(s) for s in scouts[:5]]
    except Exception as exc:
        logger.debug("_load_scouts error: %s", exc)
    return []


def _load_knowledge_gaps(limit: int = 5) -> list[dict]:
    try:
        from lib.hermes_knowledge_gap_logger import load_recent_knowledge_gaps
        return load_recent_knowledge_gaps(limit=limit)
    except Exception as exc:
        logger.debug("_load_knowledge_gaps error: %s", exc)
    return []


def _load_monetization_plan() -> dict:
    try:
        from lib.hermes_monetization_today import build_today_monetization_plan
        return dict(build_today_monetization_plan())
    except Exception as exc:
        logger.debug("_load_monetization_plan error: %s", exc)
    return {}


# ── Core: load all inputs ─────────────────────────────────────────────────────

def load_daily_operating_inputs() -> dict:
    """Load all inputs for daily operating cycle. Never crashes.

    Evidence priority: artifacts > action_queue > decisions > source_intake > memory_v2 > lessons
    Returns dict with keys: goals, memory_v2, content_assets, action_queue, decisions,
      source_intake, scouts, knowledge_gaps, monetization_plan, loaded_at, _errors
    """
    errors: list[str] = []
    result: dict[str, Any] = {"loaded_at": _now_iso(), "_errors": errors}

    for key, loader in [
        ("goals",             _load_goals),
        ("memory_v2",         _load_memory_v2),
        ("content_assets",    _load_content_assets),
        ("action_queue",      _load_action_queue),
        ("decisions",         _load_decisions),
        ("source_intake",     _load_source_intake),
        ("scouts",            _load_scouts),
        ("knowledge_gaps",    _load_knowledge_gaps),
        ("monetization_plan", _load_monetization_plan),
    ]:
        try:
            result[key] = loader()
        except Exception as exc:
            result[key] = [] if key != "monetization_plan" else {}
            errors.append(f"{key}: {exc!s:.60}")

    return result


# ── Selectors ─────────────────────────────────────────────────────────────────

def select_top_revenue_action(inputs: dict) -> dict:
    """Select the highest-value revenue action from current assets and goals."""
    plan = inputs.get("monetization_plan") or {}
    assets = inputs.get("content_assets") or []
    goals = inputs.get("goals") or []

    top_asset_path = plan.get("top_asset_path") or (assets[0].get("path") if assets else None)
    top_asset_type = plan.get("top_asset_type") or (assets[0].get("type", "content draft") if assets else "content draft")
    top_asset_name = plan.get("top_asset_name") or (
        Path(top_asset_path).name if top_asset_path else "no content asset found"
    )

    # Select action from top-priority goal
    top_goal_title = goals[0].get("title") if goals else "Build Nexus revenue engine"

    return {
        "action":           f"Advance {top_asset_type}: {top_asset_name}",
        "asset_path":       str(top_asset_path) if top_asset_path else "",
        "asset_type":       top_asset_type,
        "asset_name":       top_asset_name,
        "goal_context":     top_goal_title,
        "why":              plan.get("summary") or f"Highest-value content asset ready for next step toward {top_goal_title}.",
        "next_step":        "Review asset quality and prepare for approval — do not publish without Ray sign-off.",
        "approval_needed":  "Ray approval required before publishing, sending, or selling.",
        "evidence":         str(top_asset_path) if top_asset_path else "No verified content asset found.",
    }


def select_top_asset_to_review(inputs: dict) -> dict:
    """Select the top content asset needing Ray's review."""
    assets = inputs.get("content_assets") or []
    if not assets:
        return {
            "asset_path": "",
            "asset_type": "",
            "asset_name": "No content assets found.",
            "why": "No draft or content files detected in content directories.",
        }
    top = assets[0]
    path = top.get("path", "")
    return {
        "asset_path": str(path),
        "asset_type": top.get("type", "draft"),
        "asset_name": Path(path).name if path else "unknown",
        "why":        f"Highest-scored {top.get('type', 'content')} asset ready for review.",
    }


def select_top_scout_assignment(inputs: dict) -> dict:
    """Select the next best internal scout task."""
    scouts = inputs.get("scouts") or []
    action_queue = inputs.get("action_queue") or []
    goals = inputs.get("goals") or []

    # Find scout assigned in action queue
    for action in action_queue:
        assigned_scout = action.get("assigned_scout") or action.get("assigned_to", "")
        if assigned_scout and action.get("status") not in ("completed_with_artifact", "failed"):
            return {
                "scout_name":      assigned_scout,
                "task":            action.get("title", "Resume assigned task"),
                "expected_output": action.get("next_step") or "Produce a research summary or draft artifact.",
                "source":          "action_queue",
            }

    # Fall back to first available scout + top goal
    if scouts:
        scout = scouts[0]
        goal_ctx = goals[0].get("title") if goals else "Nexus revenue growth"
        scout_name = scout.get("name") or scout.get("tool_id", "Research Scout")
        return {
            "scout_name":      scout_name,
            "task":            f"Research and summarize opportunities for: {goal_ctx}",
            "expected_output": "Research summary artifact stored locally.",
            "source":          "scout_registry",
        }

    return {
        "scout_name":      "Internal research",
        "task":            "Review source intake and score monetization opportunities.",
        "expected_output": "Updated opportunity scores and action queue entries.",
        "source":          "fallback",
    }


def find_current_blockers(inputs: dict) -> list[dict]:
    """Find current operational blockers. Never invents stale provider issues."""
    blockers: list[dict] = []
    action_queue = inputs.get("action_queue") or []
    knowledge_gaps = inputs.get("knowledge_gaps") or []
    decisions = inputs.get("decisions") or []

    # Blocked actions
    for action in action_queue:
        if action.get("status") == "blocked":
            title = action.get("title", "Unknown task")
            blockers.append({
                "blocker":   f"Action blocked: {title}",
                "category":  "operational",
                "fix":       action.get("next_step") or "Review action queue and identify what is missing.",
            })

    # Approval-pending actions
    for action in action_queue:
        if action.get("status") == "needs_ray_approval" or action.get("requires_ray_approval"):
            title = action.get("title", "Unknown task")
            blockers.append({
                "blocker":   f"Waiting for Ray approval: {title}",
                "category":  "approval",
                "fix":       action.get("approval_reason") or "Provide approval or rejection in Telegram.",
            })

    # Open knowledge gaps as soft blockers
    open_gaps = [g for g in knowledge_gaps if g.get("status") == "open"]
    if open_gaps:
        topics = ", ".join(g.get("category", "unknown") for g in open_gaps[:3])
        blockers.append({
            "blocker":  f"Open knowledge gaps: {topics}",
            "category": "knowledge",
            "fix":      "Send sources or links via Telegram to close gaps.",
        })

    # Recent failed decisions
    for d in decisions[:3]:
        if d.get("result_status") == "failed":
            question = d.get("question_or_trigger", "unknown")[:60]
            blockers.append({
                "blocker":  f"Recent failed decision: {question}",
                "category": "decision",
                "fix":      "Review decision log and provide guidance.",
            })

    return blockers


def find_items_needing_ray_approval(inputs: dict) -> list[dict]:
    """Find all items that need Ray's explicit approval."""
    items: list[dict] = []
    action_queue = inputs.get("action_queue") or []
    decisions = inputs.get("decisions") or []

    # Actions awaiting approval
    for action in action_queue:
        if action.get("status") == "needs_ray_approval" or (
            action.get("requires_ray_approval") and action.get("status") not in
            ("completed_with_artifact", "failed", "cancelled")
        ):
            title = action.get("title", "Unnamed action")
            reason = action.get("approval_reason") or "Requires Ray sign-off before proceeding."
            items.append({
                "item":              title,
                "category":         "action_queue",
                "why":              reason,
                "next_if_approved": action.get("next_step") or "Hermes will execute the approved action.",
                "risk_if_skipped":  "Task remains blocked; no progress until approved.",
            })

    # Decisions that required approval
    for d in decisions[:5]:
        if d.get("requires_ray_approval") and d.get("result_status") == "pending":
            q = d.get("question_or_trigger", "")[:80]
            dec = d.get("decision", "")[:80]
            items.append({
                "item":              f"Decision: {dec}",
                "category":         "decision_log",
                "why":              f"Triggered by: {q}",
                "next_if_approved": "Hermes proceeds with chosen option.",
                "risk_if_skipped":  "Decision stays unresolved; no action taken.",
            })

    return items


# ── Plan builder ──────────────────────────────────────────────────────────────

def build_daily_operating_plan(inputs: dict | None = None) -> dict:
    """Build the complete daily operating plan dict.

    Uses: goals, memory_v2 (context only), content_assets, action_queue,
    decisions, source_intake, scouts, knowledge_gaps, monetization_plan.

    Evidence priority: artifacts > action_queue > decisions > source_intake > memory_v2 > lessons
    """
    if inputs is None:
        inputs = load_daily_operating_inputs()

    top_revenue     = select_top_revenue_action(inputs)
    top_asset       = select_top_asset_to_review(inputs)
    top_scout       = select_top_scout_assignment(inputs)
    blockers        = find_current_blockers(inputs)
    approval_items  = find_items_needing_ray_approval(inputs)
    goals           = inputs.get("goals") or []
    memory_v2       = inputs.get("memory_v2") or []
    action_queue    = inputs.get("action_queue") or []
    source_intake   = inputs.get("source_intake") or []

    # Top priority: first unblocked, non-approval-pending action OR top revenue
    top_priority = "Advance top content asset toward Ray review"
    top_priority_why = top_revenue.get("why") or "Highest-value asset ready for next step."

    if action_queue:
        for a in action_queue:
            if a.get("status") not in ("blocked", "needs_ray_approval", "completed_with_artifact", "failed"):
                top_priority = a.get("title") or top_priority
                top_priority_why = a.get("description") or a.get("next_step") or top_priority_why
                break

    # Evidence citations
    evidence: list[str] = []
    if goals:
        evidence.append(f"goal: {goals[0].get('title', 'active goal')}")
    if top_asset.get("asset_path"):
        evidence.append(f"artifact: {top_asset['asset_path']}")
    if action_queue:
        evidence.append("action_queue: hermes_action_queue.jsonl")
    if inputs.get("decisions"):
        evidence.append("decisions: hermes_decision_log.jsonl")
    if source_intake:
        evidence.append(f"source_intake: {len(source_intake)} recent record(s)")
    if memory_v2:
        evidence.append(f"memory_v2: {len(memory_v2)} active lesson(s)")

    # Internal actions Hermes can do now (safe only)
    safe_next_actions = [
        "Review and score latest source intake records",
        "Update internal action queue with current status",
        "Research top content asset improvement opportunities",
        "Log any new knowledge gaps found during review",
    ]

    plan = {
        "date":              _today_str(),
        "loaded_at":         inputs.get("loaded_at", _now_iso()),
        "top_priority":      top_priority,
        "top_priority_why":  top_priority_why,
        "top_revenue":       top_revenue,
        "top_asset":         top_asset,
        "top_scout":         top_scout,
        "blockers":          blockers,
        "approval_items":    approval_items,
        "safe_next_actions": safe_next_actions,
        "evidence":          evidence,
        "memory_v2_count":   len(memory_v2),
        "goals_count":       len(goals),
        "action_count":      len(action_queue),
        "approval_boundary": APPROVAL_BOUNDARY,
    }

    try:
        from lib.hermes_daily_cycle_state import save_daily_cycle_state
        save_daily_cycle_state(plan)
    except Exception as exc:
        logger.debug("save_daily_cycle_state skipped: %s", exc)

    return plan


# ── Formatters ────────────────────────────────────────────────────────────────

def format_daily_operating_plan(plan: dict | None = None) -> str:
    """Format the daily operating plan as TODAY'S NEXUS PLAN."""
    if plan is None:
        plan = build_daily_operating_plan()

    today        = plan.get("date", _today_str())
    top_priority = plan.get("top_priority", "Review content assets")
    top_why      = plan.get("top_priority_why", "")
    top_revenue  = plan.get("top_revenue") or {}
    top_asset    = plan.get("top_asset") or {}
    top_scout    = plan.get("top_scout") or {}
    blockers     = plan.get("blockers") or []
    approvals    = plan.get("approval_items") or []
    safe_actions = plan.get("safe_next_actions") or []
    evidence     = plan.get("evidence") or []
    boundary     = plan.get("approval_boundary", APPROVAL_BOUNDARY)

    lines = [f"TODAY'S NEXUS PLAN — {today}", ""]
    lines += [f"Top priority:", f"{top_priority}", ""]
    if top_why:
        lines += [f"Why: {top_why}", ""]

    # 1. Money move
    lines += ["1. Money move", ""]
    rev_action = top_revenue.get("action") or "No verified revenue asset found."
    rev_next   = top_revenue.get("next_step") or "Review asset quality before submission."
    rev_asset  = top_revenue.get("asset_name") or ""
    lines.append(f"   {rev_action}")
    if rev_asset and rev_asset != rev_action:
        lines.append(f"   Asset: {rev_asset}")
    lines += [f"   Next: {rev_next}", ""]

    # 2. Asset to review
    lines += ["2. Asset to review", ""]
    asset_name = top_asset.get("asset_name") or "No content assets found."
    asset_type = top_asset.get("asset_type") or ""
    asset_why  = top_asset.get("why") or ""
    desc = f"   {asset_name}"
    if asset_type:
        desc += f" ({asset_type})"
    lines.append(desc)
    if asset_why:
        lines.append(f"   {asset_why}")
    lines.append("")

    # 3. Scout assignment
    lines += ["3. Scout assignment", ""]
    scout_name = top_scout.get("scout_name") or "Internal research"
    scout_task = top_scout.get("task") or "Review source intake"
    scout_out  = top_scout.get("expected_output") or "Research summary"
    lines += [f"   {scout_name}: {scout_task}", f"   Expected: {scout_out}", ""]

    # 4. Blockers
    lines += ["4. Blockers", ""]
    if blockers:
        for b in blockers[:3]:
            lines.append(f"   - {b.get('blocker', 'Unknown blocker')}")
            fix = b.get("fix")
            if fix:
                lines.append(f"     Fix: {fix}")
    else:
        lines.append("   No critical blockers found.")
    lines.append("")

    # 5. Needs Ray approval
    lines += ["5. Needs Ray approval", ""]
    if approvals:
        for item in approvals[:3]:
            lines += [
                f"   - {item.get('item', 'Unknown item')}",
                f"     Why: {item.get('why', '')}",
            ]
    else:
        lines.append("   Nothing waiting for Ray approval right now.")
    lines.append("")

    # 6. What Hermes can do next internally
    lines += ["6. What Hermes can do next internally", ""]
    for act in safe_actions[:4]:
        lines.append(f"   - {act}")
    lines.append("")

    lines += ["Approval boundary:", boundary, ""]

    # Evidence
    if evidence:
        lines += ["Evidence:"]
        for e in evidence:
            lines.append(f"- {e}")

    return "\n".join(lines)


def format_approval_needed_summary(plan: dict | None = None) -> str:
    """Format the approval summary as APPROVAL NEEDED."""
    if plan is None:
        plan = build_daily_operating_plan()

    approvals = plan.get("approval_items") or []
    lines = ["APPROVAL NEEDED", ""]

    if approvals:
        lines += ["Items requiring Ray approval:", ""]
        for i, item in enumerate(approvals, 1):
            lines += [
                f"{i}. {item.get('item', 'Unknown item')}",
                f"   Why approval is needed:",
                f"   {item.get('why', 'Requires sign-off before proceeding.')}",
                f"   Next if approved:",
                f"   {item.get('next_if_approved', 'Hermes will proceed.')}",
                f"   Risk if rejected/skipped:",
                f"   {item.get('risk_if_skipped', 'Task remains blocked.')}",
                "",
            ]
    else:
        lines += ["No items currently waiting for Ray approval.", ""]

    lines += [
        "Safe internal work that does not need approval:",
        "",
        "- draft revisions",
        "- research and source scoring",
        "- internal scout task assignment",
        "- action queue updates",
        "- knowledge gap logging",
        "",
        "Approval boundary:",
        "Publishing, client-facing content, payments, paid tools, live trading, "
        "production deployment, affiliate signup, and subscriber emails require Ray approval.",
    ]

    return "\n".join(lines)


def format_continue_while_out_plan() -> str:
    """Format the continue-while-out response."""
    lines = [
        "CONTINUE WHILE YOU ARE OUT",
        "",
        "I can safely continue internal work only.",
        "",
        "I will:",
        "",
    ]
    for i, item in enumerate(SAFE_INTERNAL_WORK, 1):
        lines.append(f"{i}. {item}")

    lines += [
        "",
        "I will not:",
        "",
    ]
    for item in BLOCKED_ACTIONS:
        lines.append(f"- {item}")

    lines += [
        "",
        "Next check-in:",
        'Ask "what did you do while I was out?" or "show action queue."',
    ]
    return "\n".join(lines)


def format_top_revenue_move(plan: dict | None = None) -> str:
    """Format the top revenue move as TODAY'S TOP MONEY MOVE."""
    if plan is None:
        plan = build_daily_operating_plan()

    top_revenue = plan.get("top_revenue") or {}
    today = plan.get("date", _today_str())

    action       = top_revenue.get("action") or "No verified revenue asset ready."
    why          = top_revenue.get("why") or "Based on current content assets."
    asset_path   = top_revenue.get("asset_path") or ""
    asset_name   = top_revenue.get("asset_name") or "No asset found."
    asset_type   = top_revenue.get("asset_type") or "content draft"
    next_step    = top_revenue.get("next_step") or "Review asset, then request Ray approval before publishing."
    approval_req = top_revenue.get("approval_needed") or "Ray approval required before publishing or selling."
    evidence     = top_revenue.get("evidence") or "No verified content asset found."

    lines = [f"TODAY'S TOP MONEY MOVE — {today}", ""]
    lines += [f"Best move: {action}", ""]
    lines += [f"Why this is first: {why}", ""]
    lines += ["Asset involved:", f"  {asset_name} ({asset_type})"]
    if asset_path:
        lines.append(f"  Path: {asset_path}")
    lines += [
        "",
        f"Next internal step: {next_step}",
        "",
        f"Approval needed before:",
        f"  {approval_req}",
        "",
        "Evidence:",
        f"  {evidence}",
    ]
    return "\n".join(lines)


def format_blockers_summary(plan: dict | None = None) -> str:
    """Format the blockers report as TODAY'S BLOCKERS."""
    if plan is None:
        plan = build_daily_operating_plan()

    blockers = plan.get("blockers") or []
    today    = plan.get("date", _today_str())

    critical   = [b for b in blockers if b.get("category") in ("operational", "decision")]
    operational = [b for b in blockers if b.get("category") in ("approval", "knowledge")]

    lines = [f"TODAY'S BLOCKERS — {today}", ""]
    lines += ["Critical blockers:", ""]
    if critical:
        for b in critical:
            lines.append(f"- {b.get('blocker', 'Unknown')}")
            fix = b.get("fix")
            if fix:
                lines.append(f"  Fix: {fix}")
    else:
        lines.append("- No critical blockers found.")

    lines += ["", "Operational blockers:", ""]
    if operational:
        for b in operational:
            lines.append(f"- {b.get('blocker', 'Unknown')}")
            fix = b.get("fix")
            if fix:
                lines.append(f"  Fix: {fix}")
    else:
        lines.append("- No operational blockers found.")

    all_fixes = list({b.get("fix") for b in blockers if b.get("fix")})
    if all_fixes:
        lines += ["", f"Recommended fix: {all_fixes[0]}"]
    elif not blockers:
        lines += ["", "Recommended fix: Continue with current action queue — no blockers detected."]

    return "\n".join(lines)
