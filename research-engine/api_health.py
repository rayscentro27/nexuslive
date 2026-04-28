"""
API Health — shared rate-limit tracking for all research-engine workers.

Workers call mark_rate_limited() when they hit a 429/413 and
is_available() before picking a provider so they skip known-bad ones.
State is persisted to Supabase worker_resource_status.
"""
import os, json, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# In-process cache so we don't hit Supabase on every single call
_cache: dict[str, dict] = {}


def _headers() -> dict:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Prefer":        "return=minimal",
    }


def mark_rate_limited(worker: str, resource: str,
                      retry_seconds: int = 60, detail: str = "") -> None:
    """Record that `resource` is rate-limited for `retry_seconds`."""
    retry_after = (datetime.now(timezone.utc) + timedelta(seconds=retry_seconds)).isoformat()
    row = {
        "worker_name":  worker,
        "resource":     resource,
        "status":       "rate_limited",
        "retry_after":  retry_after,
        "error_detail": detail[:300],
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }
    _cache[resource] = {"status": "rate_limited", "retry_after": retry_after}

    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        body = json.dumps(row).encode()
        req  = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/worker_resource_status"
            f"?worker_name=eq.{urllib.parse.quote(worker)}&resource=eq.{urllib.parse.quote(resource)}",
            data=body,
            headers=_headers(),
            method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 404 or r.status < 200:
                # row doesn't exist yet — insert
                _insert_row(row)
    except Exception:
        try:
            _insert_row(row)
        except Exception:
            pass


def mark_ok(worker: str, resource: str) -> None:
    """Clear a rate-limit flag once the worker has recovered."""
    _cache.pop(resource, None)
    if not SUPABASE_URL or not SUPABASE_KEY:
        return
    try:
        body = json.dumps({
            "status":      "ok",
            "retry_after": None,
            "updated_at":  datetime.now(timezone.utc).isoformat(),
        }).encode()
        req  = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/worker_resource_status"
            f"?worker_name=eq.{urllib.parse.quote(worker)}&resource=eq.{urllib.parse.quote(resource)}",
            data=body, headers=_headers(), method="PATCH",
        )
        with urllib.request.urlopen(req, timeout=5) as _:
            pass
    except Exception:
        pass


def is_available(resource: str) -> bool:
    """Return True if the resource is not currently rate-limited."""
    # Check in-process cache first
    cached = _cache.get(resource)
    if cached and cached.get("status") == "rate_limited":
        retry = cached.get("retry_after", "")
        if retry and retry > datetime.now(timezone.utc).isoformat():
            return False
        else:
            _cache.pop(resource, None)
            return True

    if not SUPABASE_URL or not SUPABASE_KEY:
        return True
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/worker_resource_status"
            f"?resource=eq.{urllib.parse.quote(resource)}&status=eq.rate_limited"
            f"&retry_after=gt.{datetime.now(timezone.utc).isoformat()}"
            f"&select=resource&limit=1",
            headers={
                "apikey":        SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            rows = json.loads(r.read())
            if rows:
                # Populate cache so we don't re-query
                _cache[resource] = {"status": "rate_limited", "retry_after": "9999"}
                return False
    except Exception:
        pass
    return True


def _insert_row(row: dict) -> None:
    body = json.dumps(row).encode()
    req  = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/worker_resource_status",
        data=body,
        headers={**_headers(), "Prefer": "return=minimal,resolution=merge-duplicates"},
    )
    with urllib.request.urlopen(req, timeout=5) as _:
        pass


import urllib.parse
