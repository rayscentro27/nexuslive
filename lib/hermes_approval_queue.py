"""
hermes_approval_queue.py
Phase 6C: Approval Queue Cleanup

Normalizes approval items from all Hermes sources into a single local queue.
Supports approve/reject/stale operations on local state only.

State file:   docs/reports/approvals/hermes_approval_queue_state.json
History file: docs/reports/approvals/hermes_approval_history.jsonl

Safety rules:
  - Do NOT execute approved actions (approve = authorization only)
  - Do NOT publish, email, spend, deploy, trade, or use client-facing content
  - Do NOT write to Supabase (read from hermes_memory_v2 only, no writes)
  - Do NOT modify old Supabase tables
  - Do NOT store secrets, tokens, raw client data
  - High-risk categories cannot be bulk-approved
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_STATE_FILE   = _ROOT / "docs" / "reports" / "approvals" / "hermes_approval_queue_state.json"
_HISTORY_FILE = _ROOT / "docs" / "reports" / "approvals" / "hermes_approval_history.jsonl"

APPROVAL_BOUNDARY = (
    "Approving an item only authorizes the next workflow step. "
    "Hermes will not publish, send emails, spend money, apply to affiliate programs, "
    "deploy production changes, or run live trading without a separate explicit Ray command."
)

HIGH_RISK_CATEGORIES = frozenset({
    "content_publish",
    "subscriber_email",
    "client_facing_content",
    "affiliate_signup",
    "payment_or_stripe",
    "paid_tool",
    "production_deploy",
    "live_trading",
})

ALL_CATEGORIES = frozenset({
    "content_publish", "subscriber_email", "client_facing_content",
    "affiliate_signup", "payment_or_stripe", "paid_tool",
    "production_deploy", "live_trading",
    "lesson_approval", "internal_review", "asset_review",
    "monetization_action", "other",
})

SAFE_INTERNAL_WORK = [
    "draft revisions",
    "research and source scoring",
    "internal scout task assignment",
    "action queue updates",
    "knowledge gap logging",
    "daily plan state updates",
    "content asset improvement review",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir() -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _stable_id(source_id: str) -> str:
    """Generate a deterministic approval_id from a source item id."""
    h = hashlib.md5(source_id.encode(), usedforsecurity=False).hexdigest()[:10]
    return f"apq_{h}"


# ── Input loaders (each fault-tolerant) ──────────────────────────────────────

def _load_action_queue_approvals() -> list[dict]:
    """Load actions with status=needs_ray_approval from action queue JSONL."""
    try:
        from lib.hermes_action_queue import get_pending_approval_actions
        actions = get_pending_approval_actions()
        result = []
        for a in actions:
            d = a.to_dict() if hasattr(a, "to_dict") else dict(a)
            result.append({
                "_source_type": "action_queue",
                "_raw": d,
                "title":              d.get("title") or "Unnamed action",
                "summary":            d.get("description") or d.get("approval_reason") or "",
                "category":           "internal_review",
                "source":             "action_queue",
                "source_path":        "docs/reports/actions/hermes_action_queue.jsonl",
                "related_action_id":  d.get("action_id") or "",
                "related_artifact":   (d.get("artifact_outputs") or [""])[0],
                "evidence_paths":     d.get("artifact_outputs") or [],
                "risk_level":         "medium",
                "approval_required_for": d.get("approval_reason") or "Action requires Ray sign-off.",
                "if_approved":        d.get("next_step") or "Hermes will proceed with the action.",
                "if_rejected":        "Action stays blocked; Hermes will not proceed.",
                "safe_internal_next_step": "Review the action and approve or reject.",
                "created_at":         d.get("created_at") or _now_iso(),
            })
        return result
    except Exception as exc:
        logger.debug("_load_action_queue_approvals error: %s", exc)
        return []


def _load_decision_log_approvals() -> list[dict]:
    """Load pending decisions that require Ray approval."""
    try:
        from lib.hermes_decision_log import load_recent_decisions
        decisions = load_recent_decisions(limit=20)
        result = []
        for d in decisions:
            raw = d.to_dict() if hasattr(d, "to_dict") else dict(d)
            if not raw.get("requires_ray_approval"):
                continue
            if raw.get("result_status") not in ("pending", ""):
                continue
            result.append({
                "_source_type": "decision_log",
                "_raw": raw,
                "title":              raw.get("decision") or raw.get("question_or_trigger") or "Pending decision",
                "summary":            raw.get("question_or_trigger") or "",
                "category":           "internal_review",
                "source":             "decision_log",
                "source_path":        "docs/reports/decisions/hermes_decision_log.jsonl",
                "related_decision_id": raw.get("decision_id") or "",
                "related_artifact":   (raw.get("artifact_paths") or [""])[0],
                "evidence_paths":     raw.get("artifact_paths") or [],
                "risk_level":         raw.get("risk_level") or "medium",
                "approval_required_for": "Decision requires Ray authorization.",
                "if_approved":        raw.get("why_selected") or "Hermes proceeds with chosen option.",
                "if_rejected":        "Decision is cancelled; Hermes will not act on it.",
                "safe_internal_next_step": "Review the decision context and approve or reject.",
                "created_at":         raw.get("timestamp") or _now_iso(),
            })
        return result
    except Exception as exc:
        logger.debug("_load_decision_log_approvals error: %s", exc)
        return []


def _load_daily_cycle_approvals() -> list[dict]:
    """Load approval items from latest daily cycle state."""
    try:
        from lib.hermes_daily_cycle_state import load_latest_daily_cycle_state
        state = load_latest_daily_cycle_state()
        if not state:
            return []
        result = []
        for item in (state.get("approval_items") or []):
            result.append({
                "_source_type": "daily_cycle",
                "_raw": item,
                "title":              item.get("item") or "Daily plan approval item",
                "summary":            item.get("why") or "",
                "category":           _infer_category(item.get("item") or ""),
                "source":             "daily_cycle_state",
                "source_path":        "docs/reports/operations/hermes_daily_cycle_state.json",
                "evidence_paths":     ["docs/reports/operations/hermes_daily_cycle_state.json"],
                "risk_level":         _infer_risk(item.get("item") or ""),
                "approval_required_for": item.get("why") or "Requires Ray authorization.",
                "if_approved":        item.get("next_if_approved") or "Hermes proceeds with the item.",
                "if_rejected":        item.get("risk_if_skipped") or "Item stays pending.",
                "safe_internal_next_step": "Review the item details and approve or reject.",
                "created_at":         state.get("created_at") or _now_iso(),
            })
        return result
    except Exception as exc:
        logger.debug("_load_daily_cycle_approvals error: %s", exc)
        return []


def _load_lesson_approvals() -> list[dict]:
    """Load pending lesson proposals from learning loop."""
    try:
        from lib.hermes_learning_loop import list_pending_lessons
        lessons = list_pending_lessons(limit=5)
        result = []
        for lesson in lessons:
            lid = lesson.get("lesson_id") or lesson.get("id") or ""
            title = lesson.get("title") or lesson.get("lesson_text", "")[:60] or "Pending lesson"
            result.append({
                "_source_type": "learning_loop",
                "_raw": {"lesson_id": lid, "title": title},
                "title":              f"Lesson: {title}",
                "summary":            lesson.get("lesson_text", "")[:120],
                "category":           "lesson_approval",
                "source":             "learning_loop",
                "source_path":        "docs/reports/memory/hermes_lessons.jsonl",
                "related_lesson_id":  lid,
                "evidence_paths":     [],
                "risk_level":         "low",
                "approval_required_for": "Lesson must be approved before it enters memory.",
                "if_approved":        "Lesson is added to Hermes memory (hermes_memory_v2).",
                "if_rejected":        "Lesson is discarded and not added to memory.",
                "safe_internal_next_step": "Review the lesson text and approve or reject.",
                "created_at":         lesson.get("created_at") or _now_iso(),
            })
        return result
    except Exception as exc:
        logger.debug("_load_lesson_approvals error: %s", exc)
        return []


def _infer_category(title: str) -> str:
    lowered = title.lower()
    if any(k in lowered for k in ("publish", "post to", "post content")):
        return "content_publish"
    if any(k in lowered for k in ("email subscriber", "newsletter", "send to subscriber")):
        return "subscriber_email"
    if any(k in lowered for k in ("affiliate", "signup", "apply to program")):
        return "affiliate_signup"
    if any(k in lowered for k in ("payment", "stripe", "charge", "billing")):
        return "payment_or_stripe"
    if any(k in lowered for k in ("deploy", "production", "release")):
        return "production_deploy"
    if any(k in lowered for k in ("trade live", "live trading", "live order")):
        return "live_trading"
    if any(k in lowered for k in ("client", "customer-facing", "client-facing")):
        return "client_facing_content"
    if any(k in lowered for k in ("asset", "content", "draft", "review")):
        return "asset_review"
    if any(k in lowered for k in ("monetize", "revenue", "money")):
        return "monetization_action"
    return "internal_review"


def _infer_risk(title: str) -> str:
    category = _infer_category(title)
    if category in HIGH_RISK_CATEGORIES:
        return "high"
    if category in ("asset_review", "monetization_action"):
        return "medium"
    return "low"


def load_approval_inputs() -> list[dict]:
    """Load all raw approval inputs from all sources. Never crashes."""
    items: list[dict] = []
    for loader in (
        _load_action_queue_approvals,
        _load_decision_log_approvals,
        _load_daily_cycle_approvals,
        _load_lesson_approvals,
    ):
        try:
            items.extend(loader())
        except Exception as exc:
            logger.debug("load_approval_inputs loader error: %s", exc)
    return items


def normalize_approval_item(raw: dict, index: int = 0) -> dict:
    """Normalize a raw approval input into standard approval item dict."""
    source_type = raw.get("_source_type", "unknown")
    # Generate stable approval_id from source IDs
    source_key = (
        raw.get("related_action_id") or
        raw.get("related_decision_id") or
        raw.get("related_lesson_id") or
        raw.get("title") or
        str(uuid.uuid4())
    )
    approval_id = _stable_id(f"{source_type}:{source_key}")

    return {
        "approval_id":            approval_id,
        "index":                  index,
        "title":                  raw.get("title") or "Unnamed approval item",
        "summary":                (raw.get("summary") or "")[:200],
        "category":               raw.get("category") or "internal_review",
        "source":                 raw.get("source") or source_type,
        "source_path":            raw.get("source_path") or "",
        "related_artifact":       raw.get("related_artifact") or "",
        "related_action_id":      raw.get("related_action_id") or "",
        "related_decision_id":    raw.get("related_decision_id") or "",
        "related_lesson_id":      raw.get("related_lesson_id") or "",
        "risk_level":             raw.get("risk_level") or "low",
        "approval_required_for":  raw.get("approval_required_for") or "Requires Ray authorization.",
        "safe_internal_next_step": raw.get("safe_internal_next_step") or "Review and decide.",
        "if_approved":            raw.get("if_approved") or "Hermes proceeds with the authorized step.",
        "if_rejected":            raw.get("if_rejected") or "Item is kept internal; no action taken.",
        "status":                 "pending",
        "created_at":             raw.get("created_at") or _now_iso(),
        "updated_at":             _now_iso(),
        "expires_at":             raw.get("expires_at") or "",
        "evidence_paths":         raw.get("evidence_paths") or [],
        "approval_boundary":      APPROVAL_BOUNDARY,
        "ray_decision":           "",
        "ray_reason":             "",
        "decided_at":             "",
    }


# ── State management ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if not _STATE_FILE.exists():
        return {"created_at": _now_iso(), "items": [], "archived": []}
    try:
        return json.loads(_STATE_FILE.read_text())
    except Exception:
        return {"created_at": _now_iso(), "items": [], "archived": []}


def _save_state(state: dict) -> None:
    _ensure_dir()
    try:
        _STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as exc:
        logger.warning("_save_state error: %s", exc)


def _append_history(entry: dict) -> None:
    _ensure_dir()
    try:
        with _HISTORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
    except Exception as exc:
        logger.warning("_append_history error: %s", exc)


def build_approval_queue() -> list[dict]:
    """Build normalized approval queue from all sources. Merges with existing state.

    Items already approved/rejected/archived retain their status.
    Returns list of normalized items with status='pending' (or kept statuses).
    """
    raw_inputs = load_approval_inputs()
    existing_state = _load_state()
    existing_by_id: dict[str, dict] = {
        item["approval_id"]: item
        for item in existing_state.get("items", [])
        if isinstance(item, dict) and item.get("approval_id")
    }

    items: list[dict] = []
    seen_ids: set[str] = set()

    for idx, raw in enumerate(raw_inputs, start=1):
        item = normalize_approval_item(raw, index=idx)
        aid = item["approval_id"]

        # Skip duplicates
        if aid in seen_ids:
            continue
        seen_ids.add(aid)

        # Preserve existing decision if already acted on
        if aid in existing_by_id:
            existing = existing_by_id[aid]
            if existing.get("status") in ("approved", "rejected", "archived"):
                item["status"]       = existing["status"]
                item["ray_decision"] = existing.get("ray_decision", "")
                item["ray_reason"]   = existing.get("ray_reason", "")
                item["decided_at"]   = existing.get("decided_at", "")
        items.append(item)

    # Re-index all items
    for i, item in enumerate(items, start=1):
        item["index"] = i

    state = {
        "created_at": _now_iso(),
        "items":      items,
        "archived":   existing_state.get("archived", []),
    }
    _save_state(state)
    return items


def list_approval_items(limit: int = 10) -> list[dict]:
    """Return only pending approval items."""
    items = build_approval_queue()
    return [i for i in items if i.get("status") == "pending"][:limit]


def _resolve_ref(ref: str | int) -> dict | None:
    """Find an item by 1-based index or approval_id. Rebuilds queue if needed."""
    state = _load_state()
    items = state.get("items") or []
    if not items:
        items = build_approval_queue()
        state = _load_state()
        items = state.get("items") or []

    ref_str = str(ref).strip()
    # Try index
    if ref_str.isdigit():
        idx = int(ref_str)
        # Only count pending items for index lookup
        pending = [i for i in items if i.get("status") == "pending"]
        if 1 <= idx <= len(pending):
            return pending[idx - 1]
        # Fall back to all items
        if 1 <= idx <= len(items):
            return items[idx - 1]
        return None
    # Try approval_id
    for item in items:
        if item.get("approval_id") == ref_str:
            return item
    return None


def get_approval_item(ref: str | int) -> dict | None:
    return _resolve_ref(ref)


def explain_approval_item(ref: str | int) -> dict:
    """Return detailed explanation dict for an approval item."""
    item = _resolve_ref(ref)
    if not item:
        return {"found": False, "error": f"No approval item found for ref '{ref}'."}
    return {
        "found":     True,
        "item":      item,
        "impact_if_approved": item.get("if_approved", ""),
        "impact_if_rejected": item.get("if_rejected", ""),
        "risk":      item.get("risk_level", "unknown"),
        "category":  item.get("category", ""),
        "evidence":  item.get("evidence_paths") or [],
    }


def approve_approval_item(ref: str | int) -> dict:
    """Mark item approved (local state only). Does NOT execute any action."""
    item = _resolve_ref(ref)
    if not item:
        return {"success": False, "message": f"No approval item found for ref '{ref}'.", "item": None}

    state = _load_state()
    for s_item in state.get("items", []):
        if s_item.get("approval_id") == item["approval_id"]:
            s_item["status"]       = "approved"
            s_item["ray_decision"] = "approved"
            s_item["decided_at"]   = _now_iso()
            s_item["updated_at"]   = _now_iso()
            break

    _save_state(state)
    _append_history({
        "event": "approved",
        "approval_id": item["approval_id"],
        "title": item["title"],
        "timestamp": _now_iso(),
    })
    return {
        "success": True,
        "message": f"Approved: {item['title']}",
        "item":    item,
        "if_approved": item.get("if_approved", ""),
    }


def reject_approval_item(ref: str | int, reason: str | None = None) -> dict:
    """Mark item rejected (local state only). Does NOT cancel any running action."""
    item = _resolve_ref(ref)
    if not item:
        return {"success": False, "message": f"No approval item found for ref '{ref}'.", "item": None}

    state = _load_state()
    for s_item in state.get("items", []):
        if s_item.get("approval_id") == item["approval_id"]:
            s_item["status"]       = "rejected"
            s_item["ray_decision"] = "rejected"
            s_item["ray_reason"]   = reason or ""
            s_item["decided_at"]   = _now_iso()
            s_item["updated_at"]   = _now_iso()
            break

    _save_state(state)
    _append_history({
        "event": "rejected",
        "approval_id": item["approval_id"],
        "title": item["title"],
        "reason": reason or "",
        "timestamp": _now_iso(),
    })
    return {
        "success": True,
        "message": f"Rejected: {item['title']}",
        "reason":  reason or "No reason provided",
        "item":    item,
    }


def simulate_approval_impact(ref: str | int) -> dict:
    item = _resolve_ref(ref)
    if not item:
        return {"found": False, "error": f"No item for ref '{ref}'."}
    return {
        "found":          True,
        "title":          item["title"],
        "category":       item["category"],
        "risk_level":     item["risk_level"],
        "if_approved":    item.get("if_approved", "Hermes proceeds with next step."),
        "next_step":      item.get("safe_internal_next_step", ""),
        "high_risk":      item["category"] in HIGH_RISK_CATEGORIES,
        "approval_boundary": APPROVAL_BOUNDARY,
    }


def simulate_rejection_impact(ref: str | int) -> dict:
    item = _resolve_ref(ref)
    if not item:
        return {"found": False, "error": f"No item for ref '{ref}'."}
    return {
        "found":       True,
        "title":       item["title"],
        "if_rejected": item.get("if_rejected", "Item kept internal; no action taken."),
        "risk_level":  item["risk_level"],
    }


def archive_stale_approval_items(max_age_days: int = 7) -> dict:
    """Mark items older than max_age_days as stale/archived (local only, no deletes)."""
    state = _load_state()
    items = state.get("items") or []
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    archived_count = 0
    newly_stale: list[str] = []

    for item in items:
        if item.get("status") not in ("pending",):
            continue
        created_raw = item.get("created_at") or ""
        try:
            created_dt = datetime.fromisoformat(created_raw)
            if created_dt < cutoff:
                item["status"]     = "stale"
                item["updated_at"] = _now_iso()
                newly_stale.append(item["title"])
                archived_count += 1
        except Exception:
            pass

    _save_state(state)
    return {
        "archived_count": archived_count,
        "stale_titles":   newly_stale,
        "max_age_days":   max_age_days,
    }


# ── Formatters ────────────────────────────────────────────────────────────────

def format_approval_queue() -> str:
    """Format the full approval queue as APPROVAL QUEUE."""
    pending = list_approval_items(limit=10)

    lines = ["APPROVAL QUEUE", ""]
    if not pending:
        lines += [
            "No approval items are waiting right now.",
            "",
            "Safe internal work that does not need approval:",
        ]
        for item in SAFE_INTERNAL_WORK:
            lines.append(f"  - {item}")
        lines += [
            "",
            "Approval boundary:",
            "Publishing, subscriber emails, client-facing content, payments,",
            "paid tools, affiliate signup, production deploys, and live trading",
            "require Ray approval.",
        ]
        return "\n".join(lines)

    lines += [f"Pending approval items ({len(pending)}):", ""]
    for item in pending:
        idx = item.get("index", "?")
        risk = item.get("risk_level", "unknown")
        cat  = item.get("category", "other").replace("_", " ")
        needed = item.get("approval_required_for") or ""
        needed_short = needed[:80]
        ev   = (item.get("evidence_paths") or ["none"])[0]
        lines += [
            f"{idx}. {item['title']}",
            f"   Category: {cat}",
            f"   Risk: {risk}",
            f"   Needed for: {needed_short}",
            f"   Evidence: {ev}",
            "",
        ]

    lines += [
        "Safe internal work that does not need approval:",
    ]
    for item in SAFE_INTERNAL_WORK:
        lines.append(f"  - {item}")
    lines += [
        "",
        "Approval boundary:",
        "Publishing, subscriber emails, client-facing content, payments,",
        "paid tools, affiliate signup, production deploys, and live trading",
        "require Ray approval.",
        "",
        "Commands:",
        "  approve item 1  |  reject item 1  |  show approval item 1",
        "  what happens if I approve item 1?",
    ]
    return "\n".join(lines)


def format_approval_item_detail(ref: str | int) -> str:
    """Format detailed view of one approval item."""
    detail = explain_approval_item(ref)
    if not detail.get("found"):
        return f"APPROVAL ITEM {ref}\n\n{detail.get('error', 'Item not found.')}"

    item = detail["item"]
    idx  = item.get("index", ref)
    lines = [f"APPROVAL ITEM {idx}", ""]
    lines += [f"Title:", f"  {item['title']}", ""]
    lines += [f"Category: {item['category'].replace('_',' ')}"]
    lines += [f"Risk: {item['risk_level']}", ""]

    why = item.get("approval_required_for") or ""
    if why:
        lines += ["Why approval is needed:", f"  {why}", ""]

    if_app = item.get("if_approved") or ""
    lines += ["If approved:", f"  {if_app}", ""]
    if_rej = item.get("if_rejected") or ""
    lines += ["If rejected:", f"  {if_rej}", ""]

    ev = item.get("evidence_paths") or []
    lines += ["Evidence:"]
    if ev:
        for e in ev[:3]:
            lines.append(f"  - {e}")
    else:
        lines.append("  - No specific evidence path on file.")
    lines += [
        "",
        "Approval boundary:",
        "  Approving this item only authorizes the next step.",
        "  Hermes will not publish, send, spend, deploy, or trade",
        "  unless the specific action is separately implemented and allowed.",
    ]
    return "\n".join(lines)


def format_approval_impact(ref: str | int, action: str = "approve") -> str:
    """Format what would happen if an item is approved or rejected."""
    if action == "approve":
        sim = simulate_approval_impact(ref)
        if not sim.get("found"):
            return f"IF APPROVED — ITEM {ref}\n\n{sim.get('error', 'Item not found.')}"
        item = _resolve_ref(ref) or {}
        idx  = item.get("index", ref)
        lines = [f"IF APPROVED — ITEM {idx}", ""]
        lines += [f"Title: {sim['title']}", ""]
        lines += ["Hermes would be allowed to:", f"  - {sim['if_approved']}", ""]
        lines += ["Hermes still would NOT automatically:"]
        for blocked in ("publish content", "send subscriber emails", "spend money",
                        "deploy to production", "run live trading"):
            lines.append(f"  - {blocked}")
        lines += [
            "",
            f"Risk: {sim['risk_level']}",
            "",
            "Approval boundary:",
            "  This approval only authorizes the next workflow step.",
        ]
    else:
        sim = simulate_rejection_impact(ref)
        if not sim.get("found"):
            return f"IF REJECTED — ITEM {ref}\n\n{sim.get('error', 'Item not found.')}"
        item = _resolve_ref(ref) or {}
        idx  = item.get("index", ref)
        lines = [f"IF REJECTED — ITEM {idx}", ""]
        lines += [f"Title: {sim['title']}", ""]
        lines += ["Hermes would:", f"  {sim['if_rejected']}", ""]
        lines += [f"Risk: {sim['risk_level']}"]
    return "\n".join(lines)


def format_approval_result(ref: str | int, result: dict) -> str:
    """Format the result of an approve or reject operation."""
    title = result.get("item", {}) or {}
    title = title.get("title") if isinstance(title, dict) else ""
    title = title or result.get("message", "")

    if not result.get("success"):
        return f"APPROVAL RESULT\n\nFailed: {result.get('message', 'Unknown error.')}"

    decision = result.get("item", {}) or {}
    decision = decision.get("ray_decision") if isinstance(decision, dict) else ""

    if decision == "approved" or "Approved" in result.get("message", ""):
        lines = ["APPROVAL RECORDED", ""]
        lines += [f"Approved: {title}", ""]
        lines += [
            "What this means:",
            "  Ray approved this item for the next workflow step.",
            "",
            "What Hermes will NOT do automatically:",
            "  - publish content",
            "  - email subscribers",
            "  - spend money",
            "  - apply to affiliate programs",
            "  - deploy production changes",
            "  - run live trading",
            "",
        ]
        next_step = (result.get("item") or {}).get("safe_internal_next_step") or ""
        if next_step:
            lines += [f"Next:", f"  {next_step}", ""]
        lines += [
            "Evidence:",
            "  docs/reports/approvals/hermes_approval_queue_state.json",
        ]
    else:
        reason = result.get("reason") or "No reason provided."
        lines = ["APPROVAL REJECTED", ""]
        lines += [f"Rejected: {title}", ""]
        lines += [f"Reason:", f"  {reason}", ""]
        lines += [
            "Next:",
            "  Hermes will keep this item out of the active approval queue",
            "  unless Ray asks to reopen it.",
        ]
    return "\n".join(lines)
