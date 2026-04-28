"""
event_intake.py — Shared helper to submit a CEO route-request event.

Creates a system_events row with event_type='ceo_route_request' so the
ceo_routing_loop picks it up, classifies it, and hands it off to the
appropriate role worker.

Usage:
    from lib.event_intake import submit_ceo_route_request

    result = submit_ceo_route_request(
        message="Create a TikTok script about business credit.",
        source="telegram",
        channel="bot",
    )
    # result: {"event_id": "uuid...", "status": "pending"} or {"error": "..."}
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

logger = logging.getLogger("EventIntake")

_ROOT = Path(__file__).resolve().parent.parent
_ENV_LOADED = False


def _ensure_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from lib.env_loader import load_nexus_env
        load_nexus_env()
    except Exception:
        pass
    _ENV_LOADED = True


def _supabase_post(row: dict, timeout: int = 10) -> Optional[dict]:
    _ensure_env()
    url  = os.getenv("SUPABASE_URL", "").rstrip("/")
    key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")

    if not url or not key:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set — cannot submit event")
        return None

    endpoint = f"{url}/rest/v1/system_events"
    data     = json.dumps(row).encode()
    headers  = {
        "apikey":        key,
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
        "Prefer":        "return=representation",
    }
    req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode()
        except Exception:
            detail = str(exc)
        logger.error("Supabase POST system_events → HTTP %s: %s", exc.code, detail[:300])
        return None
    except Exception as exc:
        logger.error("Supabase POST system_events → %s", exc)
        return None


def submit_ceo_route_request(
    message: str,
    source:    str = "unknown",
    channel:   str = "unknown",
    client_id: Optional[str] = None,
    metadata:  Optional[dict] = None,
) -> dict:
    """
    Insert a ceo_route_request event into system_events.

    Args:
        message:   The task text (required).
        source:    Where this came from — "telegram", "admin_portal", "api", etc.
        channel:   Sub-channel — "bot", "portal", "webhook", etc.
        client_id: Supabase user UUID if known.
        metadata:  Any extra key/value pairs to store in the payload.

    Returns:
        {"event_id": str, "status": "pending"}   on success
        {"error": str}                             on failure
    """
    if not message or not message.strip():
        return {"error": "message is required"}

    payload: dict = {
        "use_ceo_auto_routing": True,
        "message":              message.strip(),
        "source":               source,
        "channel":              channel,
    }
    if metadata:
        payload.update({k: v for k, v in metadata.items() if k not in payload})

    row: dict = {
        "event_type": "ceo_route_request",
        "status":     "pending",
        "payload":    payload,
    }
    if client_id:
        row["client_id"] = client_id

    inserted = _supabase_post(row)
    if not inserted:
        return {"error": "Failed to insert event — check SUPABASE_URL and SUPABASE_KEY"}

    event_id = inserted.get("id", "")
    logger.info(
        "ceo_route_request submitted: event_id=%s source=%s channel=%s",
        event_id, source, channel,
    )
    return {"event_id": event_id, "status": "pending", "source": source}
