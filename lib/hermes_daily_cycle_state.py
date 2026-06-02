"""
hermes_daily_cycle_state.py
============================
Two concerns in one module:

1. Opportunity cycle resolver (original): finds the latest autonomous intake/decision/review
   cycle and loads consistent data across all Telegram commands (show rejected, show top
   actions, show daily review, etc.).

2. Manual daily operating cycle state (Phase 6B): persists and reads the plan produced by
   build_daily_operating_plan() (hermes_daily_operating_cycle.py) to two local files:
     State file:   docs/reports/operations/hermes_daily_cycle_state.json
     History file: docs/reports/operations/hermes_daily_cycle_history.jsonl

No handler should glob report directories independently — they call this module.

Safety rules (Phase 6B):
  - Do NOT store Supabase keys, tokens, credentials, raw client data, or private payloads
  - Do NOT write action-queue changes unless HERMES_DAILY_CYCLE_WRITE_ACTIONS=true
  - State files are local-only; never transmitted to external services
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
INTAKE_DIR = ROOT / "docs" / "reports" / "intake"
DECISION_DIR = ROOT / "docs" / "reports" / "monetization"
REVIEW_DIR = ROOT / "docs" / "reports" / "review"


def _ts_from_path(p: Path) -> str:
    """Extract timestamp string from filename like foo_20260529_222011.json"""
    stem = p.stem
    parts = stem.rsplit("_", 2)
    if len(parts) >= 3:
        return "_".join(parts[-2:])
    return stem


def find_latest_daily_cycle() -> dict[str, Path | None]:
    """
    Find the most recent completed cycle by locating the latest review artifact
    and matching the decision + intake artifacts with the closest timestamp.

    Returns a dict of keys: review, decision, rejected, intake — each is a Path or None.
    """
    review_files = sorted(REVIEW_DIR.glob("daily_research_review_*.json"), reverse=True) if REVIEW_DIR.exists() else []
    decision_files = sorted(DECISION_DIR.glob("monetization_decision_cycle_*.json"), reverse=True) if DECISION_DIR.exists() else []
    rejected_files = sorted(DECISION_DIR.glob("rejected_opportunities_*.json"), reverse=True) if DECISION_DIR.exists() else []
    intake_files = sorted(INTAKE_DIR.glob("daily_opportunity_intake_*.json"), reverse=True) if INTAKE_DIR.exists() else []

    review_path = review_files[0] if review_files else None
    decision_path = decision_files[0] if decision_files else None
    rejected_path = rejected_files[0] if rejected_files else None
    intake_path = intake_files[0] if intake_files else None

    # If review exists, try to match decision + rejected to same timestamp
    if review_path and decision_files:
        review_ts = _ts_from_path(review_path)
        for f in decision_files:
            if review_ts in f.stem:
                decision_path = f
                break

    if review_path and rejected_files:
        review_ts = _ts_from_path(review_path)
        for f in rejected_files:
            if review_ts in f.stem:
                rejected_path = f
                break

    if review_path and intake_files:
        review_ts = _ts_from_path(review_path)
        for f in intake_files:
            if review_ts in f.stem:
                intake_path = f
                break

    return {
        "review": review_path,
        "decision": decision_path,
        "rejected": rejected_path,
        "intake": intake_path,
    }


def load_daily_cycle_summary() -> dict[str, Any]:
    """
    Load high-level counts from the latest cycle.
    Returns a dict with: total_sources, real_sources, fallback_sources,
    actionable, rejected, high_value, pending_approval, cycle_ts, has_data.
    """
    cycle = find_latest_daily_cycle()
    result: dict[str, Any] = {
        "has_data": False,
        "total_sources": 0,
        "real_sources": 0,
        "fallback_sources": 0,
        "actionable": 0,
        "rejected": 0,
        "high_value": 0,
        "pending_approval": 0,
        "cycle_ts": None,
        "top_opportunity": None,
    }

    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            result["has_data"] = True
            result["cycle_ts"] = data.get("generated_at") or _ts_from_path(cycle["review"])
            # Support both flat fields and intake_stats-nested structure
            stats = data.get("intake_stats") or {}
            result["total_sources"] = (
                data.get("total_sources") or stats.get("total", 0)
            )
            result["actionable"] = (
                data.get("actionable_count") or stats.get("high_potential", 0)
            )
            rejected_list = data.get("rejected", [])
            result["rejected"] = (
                data.get("rejected_count") or len(rejected_list)
            )
            result["high_value"] = (
                data.get("high_value_count") or
                sum(1 for op in data.get("top_opportunities", []) if (op.get("monetization_score") or 0) >= 70)
            )
            result["pending_approval"] = (
                data.get("approval_required_count") or len(data.get("needs_approval", []))
            )
            top_ops = data.get("top_opportunities", [])
            if top_ops:
                result["top_opportunity"] = top_ops[0]
        except Exception:
            pass

    if not result["has_data"] and cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            result["has_data"] = bool(decisions)
            result["total_sources"] = len(decisions)
            result["actionable"] = sum(1 for d in decisions if d.get("status") not in ("reject", "watch"))
            result["rejected"] = sum(1 for d in decisions if d.get("status") == "reject")
            result["high_value"] = sum(1 for d in decisions if (d.get("monetization_score") or 0) >= 70)
            result["pending_approval"] = sum(1 for d in decisions if d.get("requires_ray_approval"))
            actionable = [d for d in decisions if d.get("status") not in ("reject", "watch")]
            if actionable:
                result["top_opportunity"] = actionable[0]
            result["cycle_ts"] = _ts_from_path(cycle["decision"])
        except Exception:
            pass

    return result


def load_rejected_sources(limit: int = 10) -> list[dict]:
    """
    Load rejected sources from the same cycle as the latest review.
    This ensures 'show rejected' and 'show daily review' report the same count.
    """
    cycle = find_latest_daily_cycle()

    # Prefer data embedded in the review artifact
    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            rejected = data.get("rejected", [])
            if isinstance(rejected, list) and rejected:
                return rejected[:limit]
        except Exception:
            pass

    # Fall back to rejected_opportunities_*.json from matched cycle
    if cycle["rejected"]:
        try:
            rejected = json.loads(cycle["rejected"].read_text())
            if isinstance(rejected, list):
                return rejected[:limit]
        except Exception:
            pass

    # Last resort: latest decision cycle, filter by status
    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            return [d for d in decisions if d.get("status") == "reject"][:limit]
        except Exception:
            pass

    return []


def load_top_opportunities(limit: int = 5) -> list[dict]:
    """Load top actionable opportunities from the latest cycle."""
    cycle = find_latest_daily_cycle()

    if cycle["review"]:
        try:
            data = json.loads(cycle["review"].read_text())
            top = data.get("top_opportunities", [])
            if isinstance(top, list) and top:
                return top[:limit]
        except Exception:
            pass

    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            actionable = [d for d in decisions if d.get("status") not in ("reject", "watch")]
            actionable.sort(key=lambda d: d.get("monetization_score", 0), reverse=True)
            return actionable[:limit]
        except Exception:
            pass

    return []


def load_pending_sources(limit: int = 10) -> list[dict]:
    """Load sources that are registered but not yet fully processed."""
    cycle = find_latest_daily_cycle()
    if cycle["intake"]:
        try:
            data = json.loads(cycle["intake"].read_text())
            records = data if isinstance(data, list) else data.get("records", [])
            return [r for r in records if r.get("status") in ("pending", "registered", "queued")][:limit]
        except Exception:
            pass
    return []


def load_scout_assignments(limit: int = 10) -> list[dict]:
    """Load scout assignments from the latest cycle."""
    cycle = find_latest_daily_cycle()
    if cycle["decision"]:
        try:
            data = json.loads(cycle["decision"].read_text())
            decisions = data if isinstance(data, list) else data.get("decisions", [])
            return [d for d in decisions if d.get("assigned_scout")][:limit]
        except Exception:
            pass
    return []


def format_daily_cycle_status_common_language() -> str:
    """
    Plain-English summary for Telegram. Shows what was found, what's actionable,
    and what needs attention. No raw technical output.
    """
    summary = load_daily_cycle_summary()
    if not summary["has_data"]:
        return (
            "No daily intake has run yet.\n"
            "Say: 'Hermes, run daily opportunity intake' to start."
        )

    lines = []
    ts = summary.get("cycle_ts") or "recent"
    lines.append(f"Latest cycle: {ts}")
    lines.append(f"Sources found: {summary['total_sources']} total — "
                 f"{summary['actionable']} actionable, {summary['rejected']} filtered out.")

    if summary["high_value"]:
        lines.append(f"High-value signals: {summary['high_value']} (score 70+).")

    top = summary.get("top_opportunity")
    if top:
        title = (top.get("title") or "")[:65]
        score = top.get("monetization_score", 0)
        lines.append(f"Best opportunity: {title} (score {score}).")

    if summary["pending_approval"]:
        lines.append(f"Needs your approval: {summary['pending_approval']} item(s).")

    lines.append("\nSay 'show top monetization actions' for details, or 'show rejected' to see filtered sources.")
    return "\n".join(lines)


def format_information_sources_common_language() -> str:
    """
    Common-language summary of where Hermes gets its information.
    Does NOT dump raw directory listings. Shows meaningful counts.
    """
    summary = load_daily_cycle_summary()
    lines = [
        "Hermes reads from verified sources only — no invented data.",
        "",
        "Where information comes from:",
        "  • YouTube channels and keyword searches (channel registry + config)",
        "  • GitHub trending tools (weekly research outputs)",
        "  • Keyword-based web research (when free API is available)",
        "  • Social trend fallback tasks (manual research tasks created when APIs unavailable)",
        "  • Monetization category scoring (7-dimension engine)",
        "  • Nexus operating memory (Supabase-backed system events)",
        "  • Knowledge emails (forwarded via Telegram intake)",
        "  • Scout research outputs (artifact registry)",
    ]

    if summary["has_data"]:
        lines.append("")
        lines.append(f"Last cycle: {summary['total_sources']} sources collected and scored.")
        if summary["actionable"]:
            lines.append(f"  {summary['actionable']} marked actionable.")
        if summary["rejected"]:
            lines.append(f"  {summary['rejected']} filtered out (low score or irrelevant).")

    lines.append("")
    lines.append("To see raw artifact paths, say: 'show technical details'.")
    return "\n".join(lines)


# ── Phase 6B: Manual Daily Operating Cycle State ─────────────────────────────
# Persists plan dicts from build_daily_operating_plan() to local JSON/JSONL files.

_OP_STATE_FILE   = ROOT / "docs" / "reports" / "operations" / "hermes_daily_cycle_state.json"
_OP_HISTORY_FILE = ROOT / "docs" / "reports" / "operations" / "hermes_daily_cycle_history.jsonl"

# Env guard: action-queue writes disabled by default
_WRITE_ACTIONS_ENABLED = os.environ.get("HERMES_DAILY_CYCLE_WRITE_ACTIONS", "false").lower() == "true"

# Safe sub-dict fields (prevent raw payload leakage)
_TOP_REVENUE_KEEP = {"action", "asset_name", "asset_path", "asset_type", "next_step", "approval_needed", "why"}
_TOP_ASSET_KEEP   = {"asset_name", "asset_type", "asset_path", "why"}
_TOP_SCOUT_KEEP   = {"scout_name", "task", "expected_output", "source"}
_BLOCKER_KEEP     = {"blocker", "category", "fix"}
_APPROVAL_KEEP    = {"item", "category", "why", "next_if_approved", "risk_if_skipped"}


def _op_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _op_ensure_dir() -> None:
    _OP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def sanitize_daily_cycle_state(plan: dict) -> dict:
    """Strip secrets and raw payloads. Keep only summaries, paths, counts."""
    def _filter(d: dict, keep: set) -> dict:
        return {k: v for k, v in d.items()
                if k in keep and isinstance(v, (str, int, float, bool, type(None)))}

    safe: dict[str, Any] = {}

    for key in ("date", "top_priority", "top_priority_why"):
        val = plan.get(key)
        if isinstance(val, str):
            safe[key] = val

    for cnt_key in ("memory_v2_count", "goals_count", "action_count"):
        val = plan.get(cnt_key)
        if isinstance(val, (int, float)):
            safe[cnt_key] = int(val)

    rev = plan.get("top_revenue")
    if isinstance(rev, dict):
        safe["top_revenue"] = _filter(rev, _TOP_REVENUE_KEEP)

    asset = plan.get("top_asset")
    if isinstance(asset, dict):
        safe["top_asset"] = _filter(asset, _TOP_ASSET_KEEP)

    scout = plan.get("top_scout")
    if isinstance(scout, dict):
        safe["top_scout"] = _filter(scout, _TOP_SCOUT_KEEP)

    blockers = plan.get("blockers")
    if isinstance(blockers, list):
        safe["blockers"] = [_filter(b, _BLOCKER_KEEP) for b in blockers if isinstance(b, dict)]

    approval_items = plan.get("approval_items")
    if isinstance(approval_items, list):
        safe["approval_items"] = [_filter(a, _APPROVAL_KEEP) for a in approval_items if isinstance(a, dict)]

    evidence = plan.get("evidence")
    if isinstance(evidence, list):
        safe["evidence"] = [str(e) for e in evidence if isinstance(e, (str, int))]

    safe_actions = plan.get("safe_next_actions")
    if isinstance(safe_actions, list):
        safe["safe_next_actions"] = [str(a) for a in safe_actions if isinstance(a, str)]

    return safe


def save_daily_cycle_state(plan: dict) -> dict:
    """Sanitize plan and write to state file. Returns the saved state dict."""
    _op_ensure_dir()
    state = sanitize_daily_cycle_state(plan)
    state["created_at"] = _op_now_iso()
    state.setdefault("completed_items", [])

    try:
        _OP_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
        logger.info("daily cycle state saved → %s", _OP_STATE_FILE)
    except Exception as exc:
        logger.warning("save_daily_cycle_state write error: %s", exc)

    append_daily_cycle_history(plan)
    return state


def load_latest_daily_cycle_state() -> dict | None:
    """Return the latest persisted state dict, or None if not found."""
    if not _OP_STATE_FILE.exists():
        return None
    try:
        return json.loads(_OP_STATE_FILE.read_text())
    except Exception as exc:
        logger.warning("load_latest_daily_cycle_state read error: %s", exc)
        return None


def append_daily_cycle_history(plan: dict) -> None:
    """Append a sanitized plan snapshot to the JSONL history file."""
    _op_ensure_dir()
    state = sanitize_daily_cycle_state(plan)
    state["created_at"] = _op_now_iso()
    try:
        with _OP_HISTORY_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(state, default=str) + "\n")
    except Exception as exc:
        logger.warning("append_daily_cycle_history write error: %s", exc)


def summarize_latest_daily_cycle() -> str:
    """Return a 'LAST DAILY PLAN' formatted string from the latest state."""
    state = load_latest_daily_cycle_state()
    if not state:
        return (
            "LAST DAILY PLAN\n\n"
            "No saved daily plan found.\n"
            "Run: 'hermes run daily operating cycle' to generate one."
        )

    lines = ["LAST DAILY PLAN", ""]

    date_str   = state.get("date") or "unknown date"
    created_at = state.get("created_at", "")
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at)
            age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            age_str = f"{age_h:.0f}h ago" if age_h >= 1 else f"{age_h * 60:.0f}m ago"
        except Exception:
            age_str = "unknown age"
        lines.append(f"Plan date: {date_str} (saved {age_str})")
    else:
        lines.append(f"Plan date: {date_str}")
    lines.append("")

    top_priority = state.get("top_priority", "No priority recorded.")
    top_why      = state.get("top_priority_why", "")
    lines += [f"Top priority: {top_priority}", ""]
    if top_why:
        lines += [f"Why: {top_why}", ""]

    rev = state.get("top_revenue") or {}
    if rev.get("action"):
        lines += [f"Money move: {rev['action']}", ""]

    blockers = state.get("blockers") or []
    if blockers:
        lines += [f"Blockers ({len(blockers)}):"]
        for b in blockers[:3]:
            lines.append(f"  - {b.get('blocker', 'Unknown')}")
        lines.append("")

    approval_items = state.get("approval_items") or []
    if approval_items:
        lines += [f"Needs approval ({len(approval_items)}):"]
        for a in approval_items[:3]:
            lines.append(f"  - {a.get('item', 'Unknown item')}")
        lines.append("")

    completed = state.get("completed_items") or []
    if completed:
        lines += [f"Completed this cycle ({len(completed)}):"]
        for c in completed[:3]:
            label = c.get("item") or c.get("blocker") or str(c)
            lines.append(f"  - {label}")
        lines.append("")

    lines += [
        "What you can do:",
        "  - 'show pending items' to see what needs doing",
        "  - 'mark [item] complete' to record progress",
        "  - 'compare since last plan' to see what changed",
        "  - 'hermes run daily operating cycle' to run a fresh plan",
    ]
    return "\n".join(lines)


def compare_current_to_last_cycle(current_plan: dict, last_plan: dict) -> dict:
    """Return a diff dict comparing two plan dicts (current vs previous)."""
    def _len(d: dict, key: str) -> int:
        return len(d.get(key) or [])

    def _str(d: dict, key: str) -> str:
        return str(d.get(key) or "")

    prev = sanitize_daily_cycle_state(last_plan)
    curr = sanitize_daily_cycle_state(current_plan)

    priority_changed = _str(curr, "top_priority") != _str(prev, "top_priority")
    blocker_delta    = _len(curr, "blockers")      - _len(prev, "blockers")
    approval_delta   = _len(curr, "approval_items") - _len(prev, "approval_items")
    evidence_delta   = _len(curr, "evidence")       - _len(prev, "evidence")

    changes: list[str] = []
    if priority_changed:
        changes.append(f"Top priority changed → {curr.get('top_priority', '?')}")
    if blocker_delta > 0:
        changes.append(f"{blocker_delta} new blocker(s) found")
    elif blocker_delta < 0:
        changes.append(f"{abs(blocker_delta)} blocker(s) resolved")
    if approval_delta > 0:
        changes.append(f"{approval_delta} new approval item(s)")
    elif approval_delta < 0:
        changes.append(f"{abs(approval_delta)} approval item(s) cleared")
    if evidence_delta > 0:
        changes.append(f"{evidence_delta} more evidence source(s)")
    if not changes:
        changes.append("No significant changes detected.")

    return {
        "priority_changed": priority_changed,
        "prev_priority":    prev.get("top_priority", ""),
        "curr_priority":    curr.get("top_priority", ""),
        "blocker_delta":    blocker_delta,
        "approval_delta":   approval_delta,
        "evidence_delta":   evidence_delta,
        "changes":          changes,
        "prev_date":        prev.get("date", ""),
        "curr_date":        curr.get("date", ""),
    }


def mark_cycle_item_completed(item_id_or_title: str) -> dict:
    """Move a pending item to completed_items in the state file.

    Searches blockers and approval_items by title substring match.
    Returns dict with keys: success, message, completed_item.
    """
    state = load_latest_daily_cycle_state()
    if not state:
        return {"success": False, "message": "No saved daily plan found.", "completed_item": None}

    search = item_id_or_title.strip().lower()
    matched      = None
    matched_list = None
    matched_idx  = None

    for list_key in ("blockers", "approval_items"):
        for idx, item in enumerate(state.get(list_key) or []):
            label = (item.get("item") or item.get("blocker") or "").lower()
            if search in label:
                matched      = dict(item)
                matched_list = list_key
                matched_idx  = idx
                break
        if matched:
            break

    if matched is None:
        return {
            "success":       False,
            "message":       f"No pending item matched '{item_id_or_title}'.",
            "completed_item": None,
        }

    state[matched_list].pop(matched_idx)
    completed = state.setdefault("completed_items", [])
    matched["completed_at"]  = _op_now_iso()
    matched["_source_list"]  = matched_list
    completed.append(matched)

    _op_ensure_dir()
    try:
        _OP_STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as exc:
        logger.warning("mark_cycle_item_completed write error: %s", exc)
        return {"success": False, "message": f"Write error: {exc}", "completed_item": matched}

    label = matched.get("item") or matched.get("blocker") or item_id_or_title
    return {"success": True, "message": f"Marked complete: {label}", "completed_item": matched}


def list_pending_cycle_items() -> list[dict]:
    """Return pending items (approval_items + blockers) from latest state."""
    state = load_latest_daily_cycle_state()
    if not state:
        return []

    pending: list[dict] = []
    for item in (state.get("approval_items") or []):
        pending.append({
            "type":     "approval",
            "item":     item.get("item", "Unknown"),
            "why":      item.get("why", ""),
            "category": item.get("category", ""),
        })
    for b in (state.get("blockers") or []):
        pending.append({
            "type":     "blocker",
            "item":     b.get("blocker", "Unknown"),
            "why":      b.get("fix", ""),
            "category": b.get("category", ""),
        })
    return pending


def is_cycle_state_stale(max_age_hours: float = 24) -> bool:
    """Return True if the saved state is older than max_age_hours, or missing."""
    state = load_latest_daily_cycle_state()
    if not state:
        return True
    created_at = state.get("created_at")
    if not created_at:
        return True
    try:
        dt = datetime.fromisoformat(created_at)
        age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        return age_hours > max_age_hours
    except Exception:
        return True
