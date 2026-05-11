from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import json
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_proposed_record(note: dict[str, Any]) -> dict[str, Any]:
    notebook_name = str(note.get("notebook_name") or "Unknown Notebook").strip()
    topic = str(note.get("topic") or "general").strip()
    summary = str(note.get("summary") or "").strip()
    takeaways = note.get("key_takeaways") if isinstance(note.get("key_takeaways"), list) else []
    actions = note.get("action_items") if isinstance(note.get("action_items"), list) else []
    category = str(note.get("category") or "operations").strip().lower()
    confidence = float(note.get("confidence") or 0.7)
    return {
        "source_type": "notebooklm",
        "notebook_name": notebook_name,
        "topic": topic,
        "summary": summary,
        "key_takeaways": [str(x).strip() for x in takeaways if str(x).strip()],
        "action_items": [str(x).strip() for x in actions if str(x).strip()],
        "category": category,
        "confidence": max(0.0, min(1.0, confidence)),
        "dry_run": True,
        "created_at": _now(),
    }


def summarize_intake_queue(records: list[dict[str, Any]]) -> str:
    if not records:
        return "NotebookLM intake queue is empty (dry-run)."
    lines = [f"NotebookLM dry-run queue: {len(records)} item(s)"]
    for row in records[:5]:
        lines.append(f"- {row.get('notebook_name')} | {row.get('topic')} | {row.get('category')}")
    return "\n".join(lines)


def load_dry_run_queue(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(payload, list):
        out: list[dict[str, Any]] = []
        for row in payload:
            if isinstance(row, dict):
                out.append(build_proposed_record(row))
        return out
    return []
