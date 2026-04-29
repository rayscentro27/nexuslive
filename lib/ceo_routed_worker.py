"""
ceo_routed_worker.py — Downstream role worker for CEO-routed jobs.

Picks up system_events where event_type='ceo_routed', runs the appropriate
role handler to produce a DRAFT, and writes the draft to workflow_outputs
with status='pending_review'.

NOTHING is published, sent, or executed externally. All output is a draft
that requires human/admin approval before any user-facing action.

Activation (disabled by default):
    ENABLE_CEO_ROUTED_WORKERS=true

Run:
    python3 lib/ceo_routed_worker.py                         # daemon
    python3 lib/ceo_routed_worker.py --once                  # one cycle
    python3 lib/ceo_routed_worker.py --test content_creator  # offline handler test

Environment:
    ENABLE_CEO_ROUTED_WORKERS       "true" to activate (default: disabled)
    CEO_WORKER_POLL_INTERVAL        seconds between polls (default: 20)
    CEO_WORKER_BATCH_SIZE           events per cycle (default: 5)
    CEO_WORKER_MAX_ITERATIONS       hard stop after N cycles, 0 = unlimited (default: 0)
    CEO_ROUTING_DRY_RUN             "true" to classify + draft without writing to Supabase

Event lifecycle (this worker only touches events it explicitly claims):
    pending  →  claimed  →  drafted
                          ↘  draft_failed

Draft outputs land in workflow_outputs with:
    workflow_type  = "ceo_routed_draft"
    status         = "pending_review"   ← human must approve before anything external happens
    readiness_level = "draft"
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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# ── Path setup ─────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.env_loader import load_nexus_env
from lib.prompt_builder import PromptBuilder
from lib.ollama_fallback import run_ollama_fallback

load_nexus_env()

logger = logging.getLogger("CeoRoutedWorker")

# ── Config ─────────────────────────────────────────────────────────────────────

SUPABASE_URL  = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY  = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
POLL_INTERVAL = int(os.getenv("CEO_WORKER_POLL_INTERVAL", "20"))
BATCH_SIZE    = int(os.getenv("CEO_WORKER_BATCH_SIZE", "5"))
MAX_ITER      = int(os.getenv("CEO_WORKER_MAX_ITERATIONS", "0"))   # 0 = unlimited
DRY_RUN       = os.getenv("CEO_ROUTING_DRY_RUN", "").lower() == "true"


def is_enabled() -> bool:
    """Checked at runtime so tests can toggle it via os.environ."""
    return os.getenv("ENABLE_CEO_ROUTED_WORKERS", "").lower() == "true"


# ── Graceful shutdown ──────────────────────────────────────────────────────────

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
        url, data=data, headers=_headers("return=representation"), method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception as exc:
        logger.warning("POST %s → %s", path, exc)
        return None


# ── LLM helper ─────────────────────────────────────────────────────────────────

_LLM_UNAVAILABLE = "[DRAFT PENDING — LLM UNAVAILABLE. Re-run when Ollama is reachable.]"


def _call_llm(prompt: str, llm_fn: Optional[Callable] = None) -> dict:
    """
    Call the LLM. Default: run_ollama_fallback (Netcup, free).
    Accepts an injectable llm_fn for tests.
    Never raises — returns error dict on failure.
    """
    fn = llm_fn or run_ollama_fallback
    try:
        result = fn(prompt)
        if isinstance(result, dict):
            return result
        return {"success": True, "response": str(result), "model": "unknown", "fallback_used": False, "source": "ollama"}
    except Exception as exc:
        logger.warning("LLM call failed: %s", exc)
        return {
            "success":      False,
            "response":     _LLM_UNAVAILABLE,
            "model":        "none",
            "fallback_used": False,
            "source":       "none",
            "error":        str(exc),
        }


# ── Role handlers ──────────────────────────────────────────────────────────────
# Each handler:
#   - Takes task text + the child payload dict
#   - Accepts an injectable llm_fn= for testing (default: run_ollama_fallback)
#   - Returns a structured draft dict
#   - NEVER publishes, sends, or executes anything externally

def _make_draft(role: str, task_type: str, task: str, payload: dict,
                llm_fn: Optional[Callable] = None) -> dict:
    """Shared draft builder: builds prompt → calls LLM → returns draft dict."""
    try:
        prompt = PromptBuilder(role).build(task=task or "No task description provided.")
    except Exception as exc:
        logger.warning("PromptBuilder failed for role=%s: %s", role, exc)
        prompt = f"You are a {role} AI employee.\n\nTASK\n────\n{task}"

    llm_result = _call_llm(prompt, llm_fn=llm_fn)

    return {
        "role":         role,
        "task_type":    task_type,
        "draft_content": llm_result.get("response", _LLM_UNAVAILABLE),
        "model_used":   llm_result.get("model", "unknown"),
        "fallback_used": llm_result.get("fallback_used", False),
        "llm_source":   llm_result.get("source", "unknown"),
        "success":      llm_result.get("success", False),
        "error":        llm_result.get("error"),
        # Safety: no publish/send/post/execute fields — ever
    }


def handle_content_creator(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("content_creator", "short_form_content", task, payload, llm_fn=llm_fn)


def handle_compliance_reviewer(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("compliance_reviewer", "compliance_review", task, payload, llm_fn=llm_fn)


def handle_marketing_strategist(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("marketing_strategist", "marketing_strategy", task, payload, llm_fn=llm_fn)


def handle_credit_analyst(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("credit_analyst", "credit_analysis", task, payload, llm_fn=llm_fn)


def handle_business_formation(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("business_formation", "business_foundation", task, payload, llm_fn=llm_fn)


def handle_funding_strategist(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("funding_strategist", "funding_strategy", task, payload, llm_fn=llm_fn)


def handle_research_analyst(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    return _make_draft("research_analyst", "research", task, payload, llm_fn=llm_fn)


def handle_unknown(task: str, payload: dict, *, llm_fn: Optional[Callable] = None) -> dict:
    """Safe fallback for roles not yet implemented. Produces a generic draft."""
    return _make_draft("default", "unclassified", task, payload, llm_fn=llm_fn)


# ── Handler registry ───────────────────────────────────────────────────────────

_HANDLERS: dict[str, Callable] = {
    "content_creator":    handle_content_creator,
    "compliance_reviewer": handle_compliance_reviewer,
    "marketing_strategist": handle_marketing_strategist,
    "credit_analyst":     handle_credit_analyst,
    "business_formation": handle_business_formation,
    "funding_strategist": handle_funding_strategist,
    "research_analyst":   handle_research_analyst,
}


def get_handler(role: str) -> Callable:
    return _HANDLERS.get(role, handle_unknown)


# ── Draft writer ───────────────────────────────────────────────────────────────

def _deterministic_uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def _create_workflow_run(event_id: str, role: str, parent_job_id: Optional[str]) -> Optional[dict]:
    workflow_id = _deterministic_uuid(f"ceo-routed-draft:{event_id}")
    row = {
        "id": workflow_id,
        "workflow_type": "ceo_routed_draft",
        "status": "completed",
        "trigger_event": event_id,
        "metadata": {
            "source": "ceo_routed_worker",
            "role": role,
            "parent_job_id": parent_job_id,
        },
    }
    return _sb_post("orchestrator_workflow_runs", row)


def write_draft(event_id: str, payload: dict, draft: dict) -> Optional[dict]:
    """
    Write draft to workflow_outputs with status='pending_review'.
    Uses the live workflow_outputs schema:
      workflow_id, workflow_type, summary, status, payload
    Returns the inserted row or None on failure.
    """
    if DRY_RUN:
        logger.info("DRY RUN — skipping workflow_outputs write for event=%s", event_id)
        return None

    role       = draft.get("role", "unknown")
    task_type  = draft.get("task_type", "unclassified")
    content    = draft.get("draft_content", "")
    confidence = payload.get("routing_confidence", 0.0)
    parent_job = payload.get("parent_job_id")

    priority = "high" if confidence >= 0.70 else "medium" if confidence >= 0.45 else "low"
    summary  = content[:200].strip() if content else "Draft pending LLM availability."

    workflow_run = _create_workflow_run(event_id, role, parent_job)
    if not workflow_run:
        logger.warning("Failed to create workflow run for event=%s", event_id)
        return None

    row = {
        "workflow_id": workflow_run["id"],
        "workflow_type": "ceo_routed_draft",
        "summary": summary,
        "status": "pending_review",
        "payload": {
            "subject_type": role,
            "subject_id": event_id,
            "priority": priority,
            "primary_action_key": "review_draft",
            "primary_action_title": f"Review {role.replace('_', ' ').title()} Draft",
            "readiness_level": "draft",
            "source_job_id": event_id,
            "raw_output": {
                "event_id": event_id,
                "role": role,
                "task_type": task_type,
                "draft_content": content,
                "model_used": draft.get("model_used", "unknown"),
                "fallback_used": draft.get("fallback_used", False),
                "llm_source": draft.get("llm_source", "unknown"),
                "routing_confidence": confidence,
                "routing_reason": payload.get("routing_reason", ""),
                "requires_human_review": payload.get("requires_human_review", True),
            },
        },
    }

    return _sb_post("workflow_outputs", row)


# ── Event state machine ────────────────────────────────────────────────────────

def fetch_routed_jobs(limit: int = BATCH_SIZE) -> list:
    return _sb_get(
        f"system_events"
        f"?event_type=eq.ceo_routed"
        f"&status=eq.pending"
        f"&order=created_at.asc"
        f"&limit={limit}"
        f"&select=*"
    )


def claim_event(event_id: str) -> bool:
    """Atomically claim event by PATCH-with-filter. Returns False if already claimed."""
    return _sb_patch(
        f"system_events?id=eq.{event_id}&status=eq.pending",
        {"status": "claimed"},
    )


def mark_drafted(event_id: str, role: str, output_id: Optional[str]) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {
            "status": "drafted",
            "completed_at": now,
            "claimed_by": None,
            "claimed_at": None,
            "lease_expires_at": None,
            "last_error": None,
        },
    )


def mark_draft_failed(event_id: str, error: str) -> bool:
    return _sb_patch(
        f"system_events?id=eq.{event_id}",
        {
            "status": "draft_failed",
            "last_error": error[:500],
            "claimed_by": None,
            "claimed_at": None,
            "lease_expires_at": None,
        },
    )


# ── Core processor ─────────────────────────────────────────────────────────────

def process_one_event(event: dict, llm_fn: Optional[Callable] = None) -> dict:
    """
    Draft one CEO-routed event. Never raises.

    Args:
        event:  system_events row (must have event_type='ceo_routed')
        llm_fn: injectable LLM caller for tests (default: run_ollama_fallback)

    Returns:
        result dict — always includes 'event_id', 'role', 'success', 'error'
    """
    event_id    = event.get("id", "")
    event_type  = event.get("event_type", "")
    raw_payload = event.get("payload") or {}
    client_id   = event.get("client_id")

    result: dict = {
        "event_id": event_id,
        "role":     "unknown",
        "success":  False,
        "skipped":  False,
        "output_id": None,
        "error":    None,
    }

    # Safety: only handle our specific event type
    if event_type != "ceo_routed":
        result["skipped"] = True
        result["error"]   = f"Skipped: event_type='{event_type}' is not 'ceo_routed'"
        logger.debug("Skipping event=%s type=%s", event_id, event_type)
        return result

    if isinstance(raw_payload, str):
        try:
            raw_payload = json.loads(raw_payload)
        except Exception:
            raw_payload = {}

    # Propagate client_id into payload for write_draft
    if client_id and "client_id" not in raw_payload:
        raw_payload = {**raw_payload, "client_id": client_id}

    role = raw_payload.get("recommended_role", "unknown")
    task = raw_payload.get("task_description", "")

    result["role"] = role

    try:
        handler = get_handler(role)
        draft   = handler(task, raw_payload, llm_fn=llm_fn)

        logger.info(
            "Drafted event=%s role=%s model=%s success=%s",
            event_id, role, draft.get("model_used"), draft.get("success"),
        )

        output_row = None
        if not DRY_RUN:
            output_row = write_draft(event_id, raw_payload, draft)
            output_id  = output_row.get("id") if output_row else None
            result["output_id"] = output_id
            mark_drafted(event_id, role, output_id)
        else:
            logger.info("DRY RUN — no Supabase writes for event=%s", event_id)

        result["success"]  = True
        result["draft_ok"] = draft.get("success", False)

    except Exception as exc:
        result["error"] = str(exc)
        logger.exception("Error drafting event=%s", event_id)
        if not DRY_RUN:
            mark_draft_failed(event_id, str(exc))

    return result


# ── Cycle + loop ───────────────────────────────────────────────────────────────

def run_cycle(llm_fn: Optional[Callable] = None) -> dict:
    """Fetch and draft one batch of ceo_routed events. Returns summary dict."""
    if not is_enabled():
        logger.debug("ENABLE_CEO_ROUTED_WORKERS not set — cycle skipped.")
        return {"fetched": 0, "drafted": 0, "failed": 0, "skipped": 0, "disabled": True}

    jobs = fetch_routed_jobs(BATCH_SIZE)

    if not jobs:
        return {"fetched": 0, "drafted": 0, "failed": 0, "skipped": 0, "disabled": False}

    drafted = failed = skipped = 0

    for event in jobs:
        if _shutdown:
            break

        event_id = event.get("id", "")

        # Claim before processing to prevent double-drafting
        if not DRY_RUN and not claim_event(event_id):
            skipped += 1
            continue

        result = process_one_event(event, llm_fn=llm_fn)

        if result.get("skipped"):
            skipped += 1
        elif result.get("success"):
            drafted += 1
        else:
            failed += 1

    return {
        "fetched":  len(jobs),
        "drafted":  drafted,
        "failed":   failed,
        "skipped":  skipped,
        "disabled": False,
    }


def run_loop(llm_fn: Optional[Callable] = None):
    """Block forever, polling every POLL_INTERVAL seconds. Exits cleanly on signal or MAX_ITER."""
    if not is_enabled():
        logger.error(
            "ENABLE_CEO_ROUTED_WORKERS is not set to 'true'. "
            "Worker is disabled by default. Set it to enable."
        )
        sys.exit(0)

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL / SUPABASE_KEY not set.")
        sys.exit(1)

    logger.info(
        "CEO routed worker started | interval=%ds batch=%d max_iter=%s dry_run=%s",
        POLL_INTERVAL, BATCH_SIZE,
        str(MAX_ITER) if MAX_ITER else "unlimited",
        DRY_RUN,
    )

    iteration = 0
    while not _shutdown:
        iteration += 1

        if MAX_ITER and iteration > MAX_ITER:
            logger.info("Max iterations (%d) reached — exiting.", MAX_ITER)
            break

        try:
            summary = run_cycle(llm_fn=llm_fn)
            if summary.get("fetched"):
                logger.info(
                    "Cycle %d | fetched=%d drafted=%d failed=%d skipped=%d",
                    iteration, summary["fetched"], summary["drafted"],
                    summary["failed"], summary["skipped"],
                )
        except Exception:
            logger.exception("Unexpected error in cycle %d", iteration)

        for _ in range(POLL_INTERVAL):
            if _shutdown:
                break
            time.sleep(1)

    logger.info("CEO routed worker stopped after %d cycle(s).", iteration)


# ── CLI ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if "--once" in sys.argv:
        os.environ.setdefault("ENABLE_CEO_ROUTED_WORKERS", "true")
        summary = run_cycle()
        print(json.dumps(summary, indent=2))

    elif "--test" in sys.argv:
        # Offline handler test — no Supabase, no real LLM calls
        idx = sys.argv.index("--test")
        role = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "content_creator"
        task = sys.argv[idx + 2] if len(sys.argv) > idx + 2 else (
            "Create a TikTok script about why entrepreneurs need business credit."
        )

        def _mock_llm(prompt, **_):
            return {
                "success": True,
                "response": f"[MOCK DRAFT for {role}]\n\nTask: {task[:80]}",
                "model": "mock/test",
                "fallback_used": False,
                "source": "mock",
            }

        handler = get_handler(role)
        draft = handler(task, {"recommended_role": role}, llm_fn=_mock_llm)
        print(f"\nHandler test: role={role}")
        print(json.dumps(draft, indent=2))

    else:
        run_loop()
