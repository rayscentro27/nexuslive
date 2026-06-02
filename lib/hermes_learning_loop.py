"""
hermes_learning_loop.py
Phase 5: Hermes Learning Loop — lesson proposals and approved memory writing.

Learning loop contract:
  Ray correction → lesson proposal (local JSONL) → Ray review → Ray approval
  → hermes_memory_v2 insert (memory_type=lesson, status=active, scope=live_answer)

Safety rules:
  - Pending proposals are stored locally only (never written to Supabase)
  - Approved lessons write ONLY to hermes_memory_v2 (no old tables)
  - Hermes never auto-approves a lesson
  - Lessons cannot bypass safety policies, enable live trading/publishing/payments
  - No secrets or credentials in lesson text or payload
  - All lessons require Ray approval before becoming live memory

_SUPABASE_WRITE_ATTEMPTED = False — reader sentinel; write path is separate and guarded.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent

# ── Proposal storage ────────────────────────────────────────────────────────────
LEARNING_DIR      = _ROOT / "docs" / "reports" / "memory" / "learning"
PROPOSALS_FILE    = LEARNING_DIR / "hermes_lesson_proposals.jsonl"

# ── Sentinel ────────────────────────────────────────────────────────────────────
_SUPABASE_WRITE_ATTEMPTED = False  # reader-side sentinel (write path uses separate guard)

# ── Constants ───────────────────────────────────────────────────────────────────
LESSON_TYPE   = "lesson"
STATUS_ACTIVE = "active"
SCOPE_LIVE    = "live_answer"

# ── Safety blocklist ─────────────────────────────────────────────────────────────
# Any lesson containing these patterns is blocked immediately.
_BLOCKED_PATTERNS: list[str] = [
    # Approval bypass
    "bypass ray approval", "skip approval", "without ray approval",
    "approve automatically", "auto approve", "auto-approve",
    "no approval needed", "approval not required",
    # Publishing / client-facing actions
    "publish automatically", "publish without", "send to subscribers",
    "email subscribers", "send email without", "post without approval",
    "deploy without", "go live without",
    # Payments / money
    "charge", "activate stripe", "process payment", "spend money",
    "initiate payment", "submit payment",
    # Live trading
    "execute live trade", "live trading", "live broker", "funded account",
    "real money trade", "submit live order",
    # Secrets
    "api key", "secret key", "private key", "password", "credentials",
    "access token", "service role key", "supabase_service_role",
    "openrouter_api_key", "oanda_api",
    # Stale memory / evidence bypass / hallucination
    "use executive memory", "use stale memory", "ignore evidence",
    "skip evidence", "invent task", "make up status",
    "make up task", "make up approval", "make up commit", "make up count",
    "hallucinate", "fabricate",
    # Safety overrides
    "disable safety", "bypass safety", "override safety",
    "disable evidence", "disable guardrails",
    # Guarantees
    "guarantee funding", "guarantee trading", "guarantee results",
    "medical guarantee", "legal guarantee", "financial guarantee",
]

_CREDENTIAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"eyJ[A-Za-z0-9+/]{20,}", re.I),   # JWT
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.I),      # OpenAI/OpenRouter
    re.compile(r"sbp_[A-Za-z0-9]{20,}", re.I),     # Supabase personal
]

# Triggers that indicate a lesson intent in a message
_LESSON_TRIGGER_PHRASES: list[str] = [
    "record this lesson:", "remember this lesson:", "learn this:",
    "use this lesson next time:", "save this as a lesson:",
    "record lesson:", "add lesson:", "note this lesson:",
    "store this lesson:", "lesson:",
]


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _supabase_env() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return url, key


def _env_available() -> bool:
    url, key = _supabase_env()
    return bool(url and key)


def _load_proposals() -> list[dict]:
    if not PROPOSALS_FILE.exists():
        return []
    proposals = []
    for line in PROPOSALS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                proposals.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return proposals


def _save_proposal(proposal: dict) -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    with PROPOSALS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(proposal, default=str) + "\n")


def _update_proposal(lesson_id: str, updates: dict) -> bool:
    """Rewrite proposals file with updates applied to matching lesson_id."""
    proposals = _load_proposals()
    found = False
    new_lines = []
    for p in proposals:
        if p.get("lesson_id") == lesson_id:
            p.update(updates)
            p["updated_at"] = _now_iso()
            found = True
        new_lines.append(json.dumps(p, default=str))
    if found:
        PROPOSALS_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return found


# ── Safety validation ────────────────────────────────────────────────────────────

def validate_lesson_proposal(proposal: dict) -> tuple[bool, list[str]]:
    """Validate a lesson proposal. Returns (ok, safety_flags).

    ok=False means the lesson is blocked and must not be approved.
    """
    flags: list[str] = []
    text = " ".join([
        proposal.get("title", ""),
        proposal.get("summary", ""),
        proposal.get("lesson_text", ""),
    ]).lower()

    for pattern in _BLOCKED_PATTERNS:
        if pattern.lower() in text:
            flags.append(f"blocked_pattern: {pattern}")

    for regex in _CREDENTIAL_PATTERNS:
        if regex.search(text):
            flags.append("credential_pattern_detected")

    # Block empty lesson text
    if not proposal.get("lesson_text", "").strip():
        flags.append("lesson_text_empty")

    # Block lesson_text that is too short to be meaningful
    if len(proposal.get("lesson_text", "").strip()) < 10:
        flags.append("lesson_text_too_short")

    return len(flags) == 0, flags


# ── Core functions ───────────────────────────────────────────────────────────────

def detect_lesson_intent(message: str) -> bool:
    """Return True if the message is trying to record a lesson."""
    lower = message.lower().strip()
    return any(lower.startswith(t) or t in lower for t in _LESSON_TRIGGER_PHRASES)


def extract_lesson_from_message(message: str, context: dict | None = None) -> str:
    """Extract the lesson text from a trigger message."""
    lower = message.lower()
    for trigger in sorted(_LESSON_TRIGGER_PHRASES, key=len, reverse=True):
        idx = lower.find(trigger)
        if idx != -1:
            return message[idx + len(trigger):].strip()
    # Fallback: return full message stripped of common prefixes
    return message.strip()


def create_lesson_proposal(message: str, context: dict | None = None) -> dict:
    """Create a pending lesson proposal from a message. Does NOT write to Supabase."""
    lesson_text = extract_lesson_from_message(message, context)
    lesson_id   = f"lesson_{uuid.uuid4().hex[:12]}"
    now         = _now_iso()

    # Build a short title from the first sentence of the lesson
    first_sentence = lesson_text.split(".")[0].strip()
    title = first_sentence[:80] if first_sentence else lesson_text[:80]

    source_hash = _hash(message)

    proposal = {
        "lesson_id":            lesson_id,
        "title":                title,
        "summary":              lesson_text[:200],
        "lesson_text":          lesson_text,
        "source_message_hash":  source_hash,
        "source_context":       (context or {}).get("summary", "Telegram message"),
        "proposed_status":      "pending_review",
        "target_memory_type":   LESSON_TYPE,
        "proposed_scope":       SCOPE_LIVE,
        "confidence":           0.85,
        "priority":             5,
        "tags":                 ["ray_lesson", "telegram_taught"],
        "safety_flags":         [],
        "approval_required":    True,
        "created_at":           now,
        "updated_at":           now,
        "approved_at":          None,
        "approved_by":          None,
        "rejected_at":          None,
        "rejected_reason":      None,
        "related_artifact_id":  (context or {}).get("artifact_id"),
        "related_action_id":    (context or {}).get("action_id"),
        "related_decision_id":  (context or {}).get("decision_id"),
        "related_source_id":    (context or {}).get("source_id"),
    }

    ok, flags = validate_lesson_proposal(proposal)
    proposal["safety_flags"] = flags
    if not ok:
        proposal["proposed_status"] = "blocked"

    _save_proposal(proposal)
    return proposal


def list_pending_lessons(limit: int = 10) -> list[dict]:
    """Return pending (not yet approved/rejected) lesson proposals."""
    return [p for p in _load_proposals() if p.get("proposed_status") == "pending_review"][-limit:]


def list_rejected_lessons(limit: int = 10) -> list[dict]:
    """Return rejected lesson proposals."""
    return [p for p in _load_proposals() if p.get("proposed_status") == "rejected"][-limit:]


def list_active_lessons(limit: int = 10) -> list[dict]:
    """Return active lessons from hermes_memory_v2 (read-only)."""
    if not _env_available():
        return []
    try:
        url, key = _supabase_env()
        from supabase import create_client
        client = create_client(url, key)
        resp = (
            client.table("hermes_memory_v2")
            .select("memory_id,title,memory_type,status,scope,priority,confidence,tags,payload,updated_at")
            .eq("memory_type", LESSON_TYPE)
            .eq("status", STATUS_ACTIVE)
            .eq("scope", SCOPE_LIVE)
            .order("priority", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
    except Exception as exc:
        logger.warning("list_active_lessons error: %s", exc)
        return []


def reject_lesson(lesson_id: str, reason: str | None = None) -> dict:
    """Mark a lesson proposal as rejected. Local only."""
    updates = {
        "proposed_status": "rejected",
        "rejected_at":     _now_iso(),
        "rejected_reason": reason or "rejected by Ray",
    }
    found = _update_proposal(lesson_id, updates)
    return {"ok": found, "lesson_id": lesson_id, "status": "rejected" if found else "not_found"}


def deprecate_lesson(memory_id: str, reason: str | None = None) -> dict:
    """Deprecate an active lesson in hermes_memory_v2. Requires credentials."""
    if not _env_available():
        return {"ok": False, "error": "Supabase credentials not available"}
    try:
        url, key = _supabase_env()
        from supabase import create_client
        client = create_client(url, key)
        # Verify the record exists and is a lesson
        check = (
            client.table("hermes_memory_v2")
            .select("memory_id,memory_type,status")
            .eq("memory_id", memory_id)
            .execute()
        )
        rows = check.data or []
        if not rows:
            return {"ok": False, "error": f"memory_id {memory_id!r} not found"}
        row = rows[0]
        if row.get("memory_type") != LESSON_TYPE:
            return {"ok": False, "error": f"memory_id {memory_id!r} is not a lesson record"}
        # Update status to deprecated
        client.table("hermes_memory_v2").update({
            "status":           "deprecated",
            "updated_at":       _now_iso(),
            "deprecated_at":    _now_iso(),
            "deprecated_reason": reason or "deprecated by Ray",
        }).eq("memory_id", memory_id).execute()
        return {"ok": True, "memory_id": memory_id, "status": "deprecated"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def build_lesson_memory_v2_record(proposal: dict) -> dict:
    """Build the hermes_memory_v2 insert payload from an approved proposal."""
    approved_by = proposal.get("approved_by", "Ray Davis")
    approved_at = proposal.get("approved_at") or _now_iso()
    return {
        "memory_id":          proposal["lesson_id"],
        "title":              proposal["title"],
        "summary":            proposal.get("summary", "")[:500],
        "memory_type":        LESSON_TYPE,
        "status":             STATUS_ACTIVE,
        "scope":              SCOPE_LIVE,
        "source":             "operator",
        "confidence":         proposal.get("confidence", 0.85),
        "priority":           proposal.get("priority", 5),
        "tags":               proposal.get("tags", ["ray_lesson"]),
        "migration_status":   "approved",
        "migration_notes":    f"Approved by {approved_by} at {approved_at}",
        "related_artifact_id": proposal.get("related_artifact_id"),
        "related_action_id":   proposal.get("related_action_id"),
        "related_decision_id": proposal.get("related_decision_id"),
        "related_source_id":   proposal.get("related_source_id"),
        "payload": {
            "lesson_text":         proposal.get("lesson_text", ""),
            "source_message_hash": proposal.get("source_message_hash", ""),
            "source_context":      proposal.get("source_context", "Telegram"),
            "approved_by":         approved_by,
            "approved_at":         approved_at,
        },
        "created_at": proposal.get("created_at") or _now_iso(),
        "updated_at": _now_iso(),
    }


def approve_lesson(lesson_id: str) -> dict:
    """Approve a lesson proposal: validate, then write to hermes_memory_v2.

    This is the ONLY code path that writes to hermes_memory_v2 for lessons.
    It does NOT touch any old tables.
    """
    # Find the proposal
    proposals = _load_proposals()
    proposal = next((p for p in proposals if p.get("lesson_id") == lesson_id), None)
    if not proposal:
        return {"ok": False, "error": f"lesson_id {lesson_id!r} not found"}

    if proposal.get("proposed_status") == "blocked":
        flags = proposal.get("safety_flags", [])
        return {
            "ok": False,
            "error": "lesson is blocked by safety validation",
            "safety_flags": flags,
        }

    if proposal.get("proposed_status") == "rejected":
        return {"ok": False, "error": "lesson was already rejected"}

    if proposal.get("proposed_status") == "approved":
        return {
            "ok": True,
            "memory_id": proposal.get("lesson_id"),
            "status": "already_approved",
        }

    # Re-validate before write
    ok, flags = validate_lesson_proposal(proposal)
    if not ok:
        _update_proposal(lesson_id, {"proposed_status": "blocked", "safety_flags": flags})
        return {
            "ok": False,
            "error": "lesson failed safety re-validation",
            "safety_flags": flags,
        }

    if not _env_available():
        return {"ok": False, "error": "Supabase credentials not available"}

    try:
        url, key = _supabase_env()
        from supabase import create_client
        client = create_client(url, key)

        now = _now_iso()
        record = build_lesson_memory_v2_record({
            **proposal,
            "approved_at": now,
            "approved_by": "Ray Davis",
        })

        # Check for duplicate memory_id
        check = (
            client.table("hermes_memory_v2")
            .select("memory_id")
            .eq("memory_id", lesson_id)
            .execute()
        )
        if check.data:
            _update_proposal(lesson_id, {
                "proposed_status": "approved",
                "approved_at": now,
                "approved_by": "Ray Davis",
            })
            return {"ok": True, "memory_id": lesson_id, "status": "already_in_supabase"}

        # Insert into hermes_memory_v2 only
        client.table("hermes_memory_v2").insert(record).execute()

        # Mark proposal as approved locally
        _update_proposal(lesson_id, {
            "proposed_status": "approved",
            "approved_at":     now,
            "approved_by":     "Ray Davis",
        })

        logger.info("lesson approved and written: memory_id=%s", lesson_id)
        return {
            "ok":           True,
            "memory_id":    lesson_id,
            "status":       "approved",
            "memory_type":  LESSON_TYPE,
            "scope":        SCOPE_LIVE,
            "approved_by":  "Ray Davis",
            "approved_at":  now,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def approve_all_pending_lessons(limit: int | None = None) -> dict:
    """Approve all pending lesson proposals (or up to `limit` most recent).

    Re-validates every proposal before writing to hermes_memory_v2.
    ONLY writes to hermes_memory_v2. Never writes to old tables.
    Unsafe lessons are blocked, not skipped silently.

    Returns a summary dict with keys:
      reviewed, approved, blocked, skipped,
      approved_lessons, blocked_lessons, skipped_lessons, error
    """
    pending = list_pending_lessons(limit=limit if limit else 100)

    approved_lessons: list[dict] = []
    blocked_lessons:  list[dict] = []
    skipped_lessons:  list[dict] = []

    for proposal in pending:
        lid   = proposal.get("lesson_id", "?")
        title = proposal.get("title", "?")[:60]

        # Re-validate before any write
        ok, flags = validate_lesson_proposal(proposal)
        if not ok:
            _update_proposal(lid, {
                "proposed_status": "blocked",
                "safety_flags":    flags,
                "updated_at":      _now_iso(),
            })
            blocked_lessons.append({"lesson_id": lid, "title": title, "flags": flags})
            continue

        result = approve_lesson(lid)
        if result.get("ok"):
            status = result.get("status", "approved")
            if status in ("already_approved", "already_in_supabase"):
                skipped_lessons.append({"lesson_id": lid, "title": title})
            else:
                approved_lessons.append({"lesson_id": lid, "title": title})
        else:
            error      = result.get("error", "unknown error")
            safe_flags = result.get("safety_flags", [])
            if "already" in error.lower():
                skipped_lessons.append({"lesson_id": lid, "title": title})
            elif safe_flags:
                blocked_lessons.append({"lesson_id": lid, "title": title, "flags": safe_flags})
            else:
                blocked_lessons.append({"lesson_id": lid, "title": title, "flags": [error[:80]]})

    return {
        "reviewed":         len(pending),
        "approved":         len(approved_lessons),
        "blocked":          len(blocked_lessons),
        "skipped":          len(skipped_lessons),
        "approved_lessons": approved_lessons,
        "blocked_lessons":  blocked_lessons,
        "skipped_lessons":  skipped_lessons,
        "error":            None,
    }


def explain_lesson_source(memory_id: str) -> dict:
    """Return safe traceability info for a lesson. No secrets or payload dump."""
    # Check local proposals first
    for p in _load_proposals():
        if p.get("lesson_id") == memory_id:
            return {
                "memory_id":      memory_id,
                "title":          p.get("title", ""),
                "status":         p.get("proposed_status", "unknown"),
                "source":         "Ray taught this through Telegram",
                "source_hash":    p.get("source_message_hash", ""),
                "source_context": p.get("source_context", ""),
                "created_at":     p.get("created_at", ""),
                "approved_at":    p.get("approved_at"),
                "approved_by":    p.get("approved_by"),
                "related_artifact_id":  p.get("related_artifact_id"),
                "related_action_id":    p.get("related_action_id"),
                "related_decision_id":  p.get("related_decision_id"),
                "proposal_file":  str(PROPOSALS_FILE),
            }

    # Check hermes_memory_v2 if not found locally
    if _env_available():
        try:
            url, key = _supabase_env()
            from supabase import create_client
            client = create_client(url, key)
            resp = (
                client.table("hermes_memory_v2")
                .select("memory_id,title,memory_type,status,scope,payload,updated_at,migration_notes")
                .eq("memory_id", memory_id)
                .eq("memory_type", LESSON_TYPE)
                .execute()
            )
            rows = resp.data or []
            if rows:
                row = rows[0]
                payload = row.get("payload") or {}
                return {
                    "memory_id":    memory_id,
                    "title":        row.get("title", ""),
                    "status":       row.get("status", ""),
                    "source":       "Ray taught this through Telegram",
                    "source_hash":  "",
                    "approved_at":  payload.get("approved_at", ""),
                    "approved_by":  payload.get("approved_by", ""),
                    "location":     "hermes_memory_v2",
                }
        except Exception as exc:
            logger.warning("explain_lesson_source supabase error: %s", exc)

    return {"memory_id": memory_id, "status": "not_found", "source": "not found in proposals or hermes_memory_v2"}


def get_last_lesson_proposal() -> dict | None:
    """Return the most recently created lesson proposal (any status)."""
    proposals = _load_proposals()
    if not proposals:
        return None
    return sorted(proposals, key=lambda p: p.get("created_at", ""), reverse=True)[0]


def generate_gap_lesson_proposals(limit: int = 5) -> list[dict]:
    """Generate lesson proposals for resolved knowledge gaps.

    Returns a list of created proposals (pending_review status).
    Does NOT write to Supabase.
    """
    try:
        from lib.hermes_knowledge_gap_logger import load_recent_knowledge_gaps
        gaps = load_recent_knowledge_gaps(limit=100)
        open_gaps = [g for g in gaps if g.get("status") == "open"]
    except Exception:
        return []

    _GAP_LESSON_TEMPLATES: dict[str, str] = {
        "weather": (
            "When Ray asks for external real-time info like weather, news, or live prices, "
            "I should say the external provider is not connected and offer to create a "
            "research/provider setup task."
        ),
        "news": (
            "When Ray asks for current news or events, I should say I don't have a real-time "
            "news feed connected and offer to log a gap or create a research task."
        ),
        "help": (
            "When Ray types 'help', I should return a plain-language list of what I can "
            "answer — without an evidence dump."
        ),
    }

    created: list[dict] = []
    seen: set[str] = set()

    for gap in open_gaps[:limit]:
        msg_lower = (gap.get("normalized_message") or gap.get("user_message", "")).lower()
        lesson_text = None
        for keyword, template in _GAP_LESSON_TEMPLATES.items():
            if keyword in msg_lower:
                lesson_text = template
                break

        if lesson_text and lesson_text not in seen:
            seen.add(lesson_text)
            proposal = create_lesson_proposal(
                f"learn this: {lesson_text}",
                context={"summary": f"Generated from knowledge gap: {msg_lower[:60]}"},
            )
            created.append(proposal)

    return created
