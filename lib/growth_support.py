from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from scripts.prelaunch_utils import default_test_mode, supabase_request, table_exists, utc_now_iso


def feature_flag(name: str, default: str = "false") -> bool:
    import os

    return os.getenv(name, default).strip().lower() == "true"


def safe_insert(table: str, body: dict, *, prefer: str = "return=representation") -> dict:
    if not table_exists(table):
        return {"ok": False, "error": f"table_missing:{table}"}
    try:
        rows, _ = supabase_request(table, method="POST", body=body, prefer=prefer)
        return {"ok": True, "rows": rows or []}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def safe_patch(path: str, body: dict) -> dict:
    try:
        rows, _ = supabase_request(path, method="PATCH", body=body, prefer="return=representation")
        return {"ok": True, "rows": rows or []}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def stable_code(prefix: str, seed: str) -> str:
    digest = hashlib.sha256(seed.encode()).hexdigest()[:10]
    return f"{prefix}-{digest}".upper()


def audit_payload(action: str, payload: dict) -> dict:
    return {
        "action": action,
        "draft_mode": True,
        "test_mode_default": default_test_mode(),
        "created_at": utc_now_iso(),
        **payload,
    }
