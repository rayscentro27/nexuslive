"""
hermes_knowledge_gap_logger.py
Log unanswered Telegram questions as knowledge gaps for research and improvement.
Storage: local JSONL / MD — no Supabase writes.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.hermes_language_pack import (
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_EXTERNAL_INFO,
    CATEGORY_SYSTEM_HEALTH, CATEGORY_MONETIZATION, CATEGORY_CONTENT_ASSET,
    CATEGORY_MEMORY_SOURCE, CATEGORY_UNKNOWN,
    GAP_MISSING_PROVIDER, GAP_MISSING_ROUTE, GAP_UNSUPPORTED_EXTERNAL,
    GAP_MISSING_ACTIVE_MEMORY, GAP_UNCLEAR_FOLLOWUP,
)

ROOT = Path(__file__).resolve().parent.parent
GAP_DIR = ROOT / "docs" / "reports" / "knowledge_gaps"
GAP_JSONL = GAP_DIR / "hermes_knowledge_gaps.jsonl"

# Categories that should NOT be logged as gaps (handled gracefully by design)
_NO_LOG_CATEGORIES = {CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_MEMORY_SOURCE}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")[:20]


def _normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def classify_gap_reason(user_message: str) -> str:
    from lib.hermes_language_pack import is_external_info, EXTERNAL_INFO_KEYWORDS
    t = _normalize(user_message)
    if is_external_info(t):
        return GAP_UNSUPPORTED_EXTERNAL
    if any(kw in t for kw in ["what do you recommend", "what should", "next step", "what is next"]):
        return GAP_UNCLEAR_FOLLOWUP
    if any(kw in t for kw in ["opportunity", "revenue", "monetiz", "make money"]):
        return GAP_MISSING_ACTIVE_MEMORY
    return GAP_MISSING_ROUTE


def log_knowledge_gap(
    user_message: str,
    category: str,
    reason: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a gap record to JSONL. Never raises — always returns the record."""
    if category in _NO_LOG_CATEGORIES:
        return {"skipped": True, "category": category}

    gap_id = f"gap_{_now_ts()}_{uuid.uuid4().hex[:6]}"
    record: dict[str, Any] = {
        "gap_id": gap_id,
        "timestamp": _now_iso(),
        "user_message": (user_message or "")[:500],
        "normalized_message": _normalize(user_message)[:300],
        "category": category,
        "reason": reason,
        "context_snapshot": context or {},
        "suggested_handler": _suggest_handler(category, user_message),
        "suggested_research_source": _suggest_research_source(category),
        "status": "open",
        "priority": _gap_priority(category),
        "created_from": "telegram",
        "safe_to_research": category not in {CATEGORY_EXTERNAL_INFO},
        "requires_external_provider": reason == GAP_UNSUPPORTED_EXTERNAL,
    }

    try:
        GAP_DIR.mkdir(parents=True, exist_ok=True)
        with GAP_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Write readable MD summary alongside
        _write_gap_md(record)
    except Exception:
        pass

    return record


def _gap_priority(category: str) -> str:
    return {
        CATEGORY_SYSTEM_HEALTH: "high",
        CATEGORY_MONETIZATION: "high",
        CATEGORY_EXTERNAL_INFO: "medium",
        CATEGORY_CONTENT_ASSET: "medium",
        CATEGORY_UNKNOWN: "low",
    }.get(category, "low")


def _suggest_handler(category: str, message: str) -> str:
    return {
        CATEGORY_SYSTEM_HEALTH: "hermes_command_router.router._run_monitoring_check",
        CATEGORY_MONETIZATION: "hermes_command_router.router._run_business_opportunities",
        CATEGORY_EXTERNAL_INFO: "add_external_provider",
        CATEGORY_CONTENT_ASSET: "telegram_bot.continuity_dict",
        CATEGORY_MEMORY_SOURCE: "hermes_command_router.router._run_memory_sources",
        CATEGORY_UNKNOWN: "hermes_language_pack — add new phrase category",
    }.get(category, "unknown")


def _suggest_research_source(category: str) -> str:
    return {
        CATEGORY_SYSTEM_HEALTH: "supabase_worker_heartbeats",
        CATEGORY_MONETIZATION: "supabase_business_opportunities",
        CATEGORY_EXTERNAL_INFO: "external_api_provider",
        CATEGORY_UNKNOWN: "ray_feedback_review",
    }.get(category, "internal_review")


def _write_gap_md(record: dict[str, Any]) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = GAP_DIR / f"hermes_knowledge_gap_{ts}_{record['gap_id'][-6:]}.md"
    lines = [
        f"# Knowledge Gap: {record['gap_id']}",
        f"**Timestamp:** {record['timestamp']}",
        f"**Category:** {record['category']}",
        f"**Reason:** {record['reason']}",
        f"**Priority:** {record['priority']}",
        f"**Status:** {record['status']}",
        "",
        f"## User Message",
        f"> {record['user_message']}",
        "",
        f"## Suggested Handler",
        f"`{record['suggested_handler']}`",
        "",
        f"## Suggested Research Source",
        f"`{record['suggested_research_source']}`",
        "",
        f"## Notes",
        f"- Safe to research: {record['safe_to_research']}",
        f"- Requires external provider: {record['requires_external_provider']}",
        f"- Created from: {record['created_from']}",
    ]
    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def load_recent_knowledge_gaps(limit: int = 20) -> list[dict[str, Any]]:
    """Return most recent gap records."""
    if not GAP_JSONL.exists():
        return []
    try:
        lines = GAP_JSONL.read_text(encoding="utf-8").strip().splitlines()
        records = []
        for line in lines:
            try:
                records.append(json.loads(line))
            except Exception:
                pass
        # Most recent first
        records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return [r for r in records if not r.get("skipped")][:limit]
    except Exception:
        return []


def format_gap_logged_response(user_message: str, category: str, reason: str) -> str:
    """Return the Telegram-facing message when a gap is logged."""
    if reason == GAP_UNSUPPORTED_EXTERNAL:
        from lib.hermes_language_pack import external_info_topic, format_external_unavailable_response
        topic = external_info_topic(user_message)
        return format_external_unavailable_response(topic)
    return (
        "I could not answer that from active Nexus memory yet. "
        "I logged it as a knowledge gap for review. "
        "You can ask me about: Nexus status, action queue, content drafts, "
        "opportunities, decisions, scouts, or memory sources."
    )


def create_gap_research_task(gap_id: str) -> dict[str, Any]:
    """Create an internal research task for a gap. No Supabase writes."""
    gaps = load_recent_knowledge_gaps(limit=100)
    target = next((g for g in gaps if g.get("gap_id") == gap_id), None)
    if not target:
        return {"ok": False, "reason": "gap_not_found"}
    task = {
        "task_id": f"task_{gap_id}",
        "type": "knowledge_gap_research",
        "gap_id": gap_id,
        "user_message": target.get("user_message", ""),
        "category": target.get("category", ""),
        "reason": target.get("reason", ""),
        "status": "proposed",
        "created_at": _now_iso(),
    }
    try:
        task_path = GAP_DIR / f"task_{gap_id}.json"
        task_path.write_text(json.dumps(task, indent=2), encoding="utf-8")
    except Exception:
        pass
    return {"ok": True, "task": task}


def summarize_knowledge_gaps_for_review() -> str:
    """Return plain-language summary of recent open gaps."""
    gaps = load_recent_knowledge_gaps(limit=10)
    open_gaps = [g for g in gaps if g.get("status") == "open"]
    if not open_gaps:
        return "No open knowledge gaps on record."
    lines = ["Recent unanswered questions:\n"]
    for i, g in enumerate(open_gaps, 1):
        lines.append(
            f"{i}. {g.get('user_message', '?')[:80]}\n"
            f"   Reason: {g.get('reason', '?')}\n"
            f"   Suggested fix: {g.get('suggested_handler', '?')}\n"
        )
    return "\n".join(lines)
