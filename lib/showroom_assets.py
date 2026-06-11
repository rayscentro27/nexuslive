"""
Showroom reviewable-asset registry (local, safe).

A tiny JSON-backed registry so every visible output (content draft, trading
report, strategy-builder result, etc.) becomes a *reviewable asset* with an id,
status, file/showroom paths, and review/feedback/approval commands.

No network, no secrets, no publishing — local JSON only.
Registry file: logs/showroom_assets.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "logs" / "showroom_assets.json"

# Ray wants revision/feedback, not "declined" — keep the vocabulary constructive.
STATUSES = [
    "new", "needs_review", "approved", "approved_with_notes",
    "revise", "revised", "ready_to_publish_pending_approval", "archived",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def asset_id(asset_type: str, key: str) -> str:
    h = hashlib.sha1(f"{asset_type}:{key}".encode()).hexdigest()[:8]
    return f"asset_{h}"


def load() -> dict:
    if REGISTRY.exists():
        try:
            return json.loads(REGISTRY.read_text())
        except Exception:
            pass
    return {"updated_at": _now(), "assets": {}}


def save(reg: dict) -> None:
    reg["updated_at"] = _now()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(reg, indent=2))


def register(asset_type: str, title: str, file_path: str,
             showroom_path: str = "", key: str | None = None,
             status: str = "needs_review") -> dict:
    """Idempotent: same (type,key) keeps its id + prior status/feedback."""
    reg = load()
    aid = asset_id(asset_type, key or file_path)
    existing = reg["assets"].get(aid, {})
    rec = {
        "asset_id": aid,
        "asset_type": asset_type,
        "title": title,
        "created_at": existing.get("created_at", _now()),
        "updated_at": _now(),
        "file_path": file_path,
        "showroom_path": showroom_path or file_path,
        "status": existing.get("status", status),
        "feedback": existing.get("feedback", []),
        "lesson_memory": existing.get("lesson_memory", "none"),
        "review_command": f"python3 scripts/review_showroom_asset.py --asset-id {aid} --status needs_review",
        "feedback_command": f'python3 scripts/review_showroom_asset.py --asset-id {aid} --status revise --feedback "..."',
        "approval_command": f"python3 scripts/review_showroom_asset.py --asset-id {aid} --status approved",
    }
    reg["assets"][aid] = rec
    save(reg)
    return rec


def set_status(aid: str, status: str, feedback: str | None = None,
               lesson_memory: str | None = None) -> dict | None:
    reg = load()
    rec = reg["assets"].get(aid)
    if not rec:
        return None
    if status not in STATUSES:
        raise ValueError(f"invalid status {status!r}; allowed: {STATUSES}")
    rec["status"] = status
    rec["updated_at"] = _now()
    if feedback:
        rec.setdefault("feedback", []).append({"at": _now(), "status": status, "note": feedback})
    if lesson_memory:
        rec["lesson_memory"] = lesson_memory
    save(reg)
    return rec


def by_status(status: str) -> list[dict]:
    return [a for a in load()["assets"].values() if a.get("status") == status]


def recent(n: int = 20) -> list[dict]:
    return sorted(load()["assets"].values(), key=lambda a: a.get("updated_at", ""), reverse=True)[:n]
