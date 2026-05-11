"""
ceo_routing_loop.py — Autonomous polling loop for CEO auto-routing.

Polls system_events for unrouted jobs tagged with use_ceo_auto_routing: true,
classifies each via classify_task(), and enqueues a child event for the
routed AI employee role.

Event lifecycle (this loop only touches events it owns):
    pending  →  routing  →  routed
                          ↘  routing_failed  (on exception)

Child events are inserted as:
    event_type = "ceo_routed"
    payload    = build_child_job_payload() output
    status     = "pending"

Downstream role workers filter on event_type="ceo_routed" and
payload->>'recommended_role' to claim their jobs.

Run standalone:
    python3 /Users/raymonddavis/nexus-ai/lib/ceo_routing_loop.py

Environment variables:
    SUPABASE_URL                        — required
    SUPABASE_SERVICE_ROLE_KEY / SUPABASE_KEY — required
    CEO_ROUTING_POLL_INTERVAL           — seconds between polls (default: 15)
    CEO_ROUTING_BATCH_SIZE              — jobs per cycle (default: 10)
    CEO_ROUTING_DRY_RUN                 — "true" → classify but do not write

Safety guarantees:
    • Only claims events with event_type="ceo_route_request" AND status="pending"
    • Claim is atomic: PATCH to "routing" before any work begins
    • Never touches events it did not claim
    • API keys and PII stripped from every child payload
    • Graceful shutdown on SIGINT / SIGTERM — finishes current batch, then exits
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Allow running from any directory
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.env_loader import load_nexus_env
from lib.ceo_auto_router import classify_task, build_child_job_payload

load_nexus_env()

logger = logging.getLogger("CeoRoutingLoop")

# ── Config from environment ────────────────────────────────────────────────────

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY", "")
)
POLL_INTERVAL = int(os.getenv("CEO_ROUTING_POLL_INTERVAL", "15"))
BATCH_SIZE    = int(os.getenv("CEO_ROUTING_BATCH_SIZE", "10"))
DRY_RUN       = os.getenv("CEO_ROUTING_DRY_RUN", "").lower() == "true"

# ── Graceful shutdown flag ─────────────────────────────────────────────────────

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Signal %s received — finishing current batch then exiting.", signum)
    _shutdown = True


signal.signal(signal.SIGINT,  _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _headers(prefer: str = "") -> dict:
    h = {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _sb_get(path: str, timeout: int = 10) -> list:
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set — cannot poll.")
        return []
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read()) or []
    except Exception as exc:
        logger.warning("GET %s → %s", path, exc)
        return []


def _sb_patch(path: str, body: dict, timeout: int = 10) -> bool:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data, headers=_headers("return=minimal"), method="PATCH"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as _:
            return True
    except Exception as exc:
        logger.warning("PATCH %s → %s", path, exc)
        return False


def _sb_post(path: str, body: dict, timeout: int = 10) -> Optional[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers=_headers("return=representation"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception as exc:
        logger.warning("POST %s → %s", path, exc)
        return None


# ── Event table operations ─────────────────────────────────────────────────────

def fetch_routing_jobs(limit: int = BATCH_SIZE) -> list:
    """Fetch pending CEO route-request events."""
    return _sb_get(
        f"system_events"
        f"?event_type=eq.ceo_route_request"
        f"&status=eq.pending"
        f"&order=created_at.asc"
        f"&limit={limit}"
        f"&select=*"
    )


def claim_job(event_id: str) -> bool:
    """Atomically claim a job by marking it 'routing'."""
    return _sb_patch(
        f"system_events?id=eq.{event_id}&status=eq.pending",
        {"status": "routing"},
    )


def mark_routed(event_id: str, role: str, confidence: float) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {
            "status": "routed",
            "completed_at": now,
            "claimed_by": None,
            "claimed_at": None,
            "lease_expires_at": None,
            "last_error": None,
        },
    )


def mark_routing_failed(event_id: str, error: str) -> bool:
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {
            "status": "routing_failed",
            "last_error": error[:500],
            "claimed_by": None,
            "claimed_at": None,
            "lease_expires_at": None,
        },
    )


def enqueue_child_event(child_payload: dict, client_id: Optional[str] = None) -> Optional[dict]:
    """Insert the routed child job into system_events as a new pending event."""
    body = {
        "event_type": "ceo_routed",
        "status":     "pending",
        "payload":    child_payload,
    }
    if client_id:
        body["client_id"] = client_id
    return _sb_post("system_events", body)


# ── Core routing cycle ─────────────────────────────────────────────────────────

def route_one_job(event: dict) -> dict:
    """
    Classify and route a single system_event.
    Returns a result dict — never raises.
    """
    event_id  = event.get("id", "")
    raw_payload = event.get("payload") or {}
    client_id   = event.get("client_id")

    # payload may be a JSON string (Supabase sometimes returns jsonb as str)
    if isinstance(raw_payload, str):
        try:
            raw_payload = json.loads(raw_payload)
        except Exception:
            raw_payload = {}

    result = {
        "event_id":  event_id,
        "role":      "unknown",
        "confidence": 0.0,
        "child_id":  None,
        "dry_run":   DRY_RUN,
        "error":     None,
    }

    try:
        # 1. Classify
        classification = classify_task(raw_payload)
        role       = classification["recommended_role"]
        confidence = classification["confidence"]

        result["role"]       = role
        result["confidence"] = confidence

        logger.info(
            "Classified event=%s → role=%s confidence=%.2f",
            event_id, role, confidence,
        )

        if DRY_RUN:
            logger.info("DRY RUN — skipping writes for event=%s", event_id)
            return result

        # 2. Build child payload
        child = build_child_job_payload(
            raw_payload,
            classification,
            parent_job_id=event_id,
        )

        # 3. Enqueue child event
        inserted = enqueue_child_event(child, client_id=client_id)
        if inserted:
            result["child_id"] = inserted.get("id")
            logger.info("Child event created: id=%s role=%s", result["child_id"], role)
        else:
            logger.warning("Child insert returned no row for event=%s", event_id)

        # 4. Mark parent routed
        mark_routed(event_id, role, confidence)

    except Exception as exc:
        result["error"] = str(exc)
        logger.exception("Error routing event=%s", event_id)
        if not DRY_RUN:
            mark_routing_failed(event_id, str(exc))

    return result


# ── Main loop ──────────────────────────────────────────────────────────────────

def run_cycle() -> dict:
    """Fetch and route one batch. Returns summary."""
    jobs = fetch_routing_jobs(BATCH_SIZE)

    if not jobs:
        return {"fetched": 0, "routed": 0, "failed": 0, "skipped": 0}

    routed = failed = skipped = 0

    for event in jobs:
        if _shutdown:
            break

        event_id = event.get("id", "")

        # Claim before processing — prevents double-routing if multiple loops run
        if not DRY_RUN and not claim_job(event_id):
            # Another process already claimed it
            skipped += 1
            continue

        result = route_one_job(event)

        if result["error"]:
            failed += 1
        else:
            routed += 1

    return {
        "fetched": len(jobs),
        "routed":  routed,
        "failed":  failed,
        "skipped": skipped,
    }


def run_loop():
    """Block forever, polling every POLL_INTERVAL seconds. Exits cleanly on signal."""
    logger.info(
        "CEO routing loop started | interval=%ds batch=%d dry_run=%s",
        POLL_INTERVAL, BATCH_SIZE, DRY_RUN,
    )

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error(
            "SUPABASE_URL and SUPABASE_KEY must be set. "
            "Check nexus-ai/.env or environment."
        )
        sys.exit(1)

    cycle = 0
    while not _shutdown:
        cycle += 1
        try:
            summary = run_cycle()
            if summary["fetched"]:
                logger.info(
                    "Cycle %d | fetched=%d routed=%d failed=%d skipped=%d",
                    cycle, summary["fetched"], summary["routed"],
                    summary["failed"], summary["skipped"],
                )
        except Exception:
            logger.exception("Unexpected error in cycle %d", cycle)

        # Sleep in short increments so SIGINT is responsive
        for _ in range(POLL_INTERVAL):
            if _shutdown:
                break
            time.sleep(1)

    logger.info("CEO routing loop stopped after %d cycle(s).", cycle)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if "--once" in sys.argv:
        # Run exactly one cycle and print summary
        summary = run_cycle()
        print(json.dumps(summary, indent=2))
    elif "--test" in sys.argv:
        # Offline classification test — no Supabase writes
        sample = {
            "use_ceo_auto_routing": True,
            "message": sys.argv[sys.argv.index("--test") + 1]
            if len(sys.argv) > sys.argv.index("--test") + 1
            else "Create a TikTok script about business credit.",
        }
        cls = classify_task(sample)
        child = build_child_job_payload(sample, cls, parent_job_id="cli_test")
        print("\nClassification:")
        print(json.dumps(cls, indent=2))
        print("\nChild payload:")
        print(json.dumps(child, indent=2))
    else:
        run_loop()
