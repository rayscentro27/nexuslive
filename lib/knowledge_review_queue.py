from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import uuid


ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "reports" / "knowledge_intake" / "knowledge_review_queue.json"

VALID_STATUS = {"proposed", "reviewed", "approved", "rejected", "stored", "failed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)]
    except Exception:
        return []
    return []


def _write(rows: list[dict[str, Any]]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def list_records(status: str = "") -> list[dict[str, Any]]:
    rows = _read()
    if status and status in VALID_STATUS:
        return [r for r in rows if str(r.get("status") or "") == status]
    return rows


def add_proposed_record(record: dict[str, Any], source: str = "manual") -> dict[str, Any]:
    rows = _read()
    out = dict(record or {})
    out.setdefault("id", f"kr_{uuid.uuid4().hex[:12]}")
    out["status"] = "proposed"
    out["dry_run"] = True
    out["created_at"] = _now()
    out["updated_at"] = _now()
    out["review"] = {
        "reviewed_by": "",
        "reviewed_at": "",
        "notes": "",
        "source": source,
    }
    rows.append(out)
    _write(rows)
    return out


def update_status(record_id: str, status: str, reviewed_by: str, notes: str = "") -> dict[str, Any] | None:
    if status not in VALID_STATUS:
        raise ValueError("invalid status")
    rows = _read()
    for row in rows:
        if str(row.get("id") or "") != str(record_id):
            continue
        row["status"] = status
        row["updated_at"] = _now()
        review = row.get("review") if isinstance(row.get("review"), dict) else {}
        review["reviewed_by"] = (reviewed_by or "ray").strip() or "ray"
        review["reviewed_at"] = _now()
        review["notes"] = (notes or "").strip()
        row["review"] = review
        _write(rows)
        return row
    return None
