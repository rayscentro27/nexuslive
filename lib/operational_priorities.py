from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib import hermes_ops_memory


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_select(path: str) -> list[dict[str, Any]]:
    try:
        from scripts.prelaunch_utils import rest_select

        return rest_select(path, timeout=8) or []
    except Exception:
        return []


def get_operational_priorities(limit: int = 8) -> list[dict[str, Any]]:
    rows = _safe_select(
        f"operational_priorities?select=id,title,category,status,priority_score,blocked_reason,updated_at&status=in.(active,blocked)&order=priority_score.desc,updated_at.desc&limit={int(limit)}"
    )
    if rows:
        return rows
    mem = hermes_ops_memory.load_memory(updated_by="operational_priorities_fallback")
    priorities = []
    for idx, title in enumerate(mem.get("active_priorities") or []):
        priorities.append(
            {
                "id": f"mem-{idx+1}",
                "title": str(title),
                "category": "operations",
                "status": "active",
                "priority_score": max(10, 90 - idx * 10),
                "blocked_reason": "",
                "updated_at": mem.get("updated_at"),
            }
        )
    for idx, title in enumerate(mem.get("blocked_priorities") or []):
        priorities.append(
            {
                "id": f"mem-b-{idx+1}",
                "title": str(title),
                "category": "operations",
                "status": "blocked",
                "priority_score": max(10, 80 - idx * 10),
                "blocked_reason": "blocked in operational memory",
                "updated_at": mem.get("updated_at"),
            }
        )
    return priorities[:limit]


def top_focus_summary() -> str:
    rows = get_operational_priorities(limit=4)
    if not rows:
        return "No active priorities are recorded yet."
    lines: list[str] = []
    now = datetime.now(timezone.utc)
    for row in rows[:3]:
        updated = _parse_iso(str(row.get("updated_at") or ""))
        stale = ""
        if updated is not None:
            age_h = int((now - updated).total_seconds() // 3600)
            if age_h >= 72:
                stale = " (stale)"
        blocked = " [blocked]" if str(row.get("status") or "") == "blocked" else ""
        lines.append(f"- {row.get('title')}{blocked}{stale}")
    return "\n".join(lines)
