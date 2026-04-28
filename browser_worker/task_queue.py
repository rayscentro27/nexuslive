"""
Task queue backed by Supabase browser_tasks table.
"""
import os
import json
import urllib.request
from datetime import datetime, timezone
from typing import Optional

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _req(method: str, path: str, body: Optional[dict] = None) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()) or []
    except Exception:
        return []


def claim_next_task() -> Optional[dict]:
    """Atomically claim the oldest pending task. Returns task dict or None."""
    rows = _req("GET", "browser_tasks?status=eq.pending&order=created_at.asc&limit=1&select=*")
    if not rows:
        return None
    task = rows[0]
    _req("PATCH", f"browser_tasks?id=eq.{task['id']}", {
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
    })
    return task


def complete_task(task_id: int, result: str, error: Optional[str] = None,
                  screenshot_url: Optional[str] = None):
    _req("PATCH", f"browser_tasks?id=eq.{task_id}", {
        "status": "error" if error else "done",
        "result": result,
        "error": error,
        "screenshot_url": screenshot_url,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    })


def enqueue_task(task_type: str, payload: Optional[dict] = None,
                 requested_by: str = "system") -> Optional[dict]:
    rows = _req("POST", "browser_tasks", {
        "task_type": task_type,
        "payload": payload or {},
        "status": "pending",
        "requested_by": requested_by,
    })
    return rows[0] if rows else None


def get_recent_tasks(limit: int = 20) -> list:
    return _req("GET", f"browser_tasks?order=created_at.desc&limit={limit}&select=*")
