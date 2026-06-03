"""
hermes_cfo_loop_shadow.py
Phase 8B/8C — Hermes Agentic CFO Loop Shadow + Limited Primary Mode.

Shadow mode (8B): every message runs CFO loop in parallel. Live response never changed.
Limited primary mode (8C): allowlisted intents with confidence >= threshold use CFO
response as the live Telegram response.

Environment:
  HERMES_CFO_LOOP_MODE    off | shadow | limited_primary | primary (default: off)
  HERMES_CFO_LOOP_PROVIDER mock | openrouter | deepseek | local (default: mock)

Full primary mode is blocked and falls back to limited_primary.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
SHADOW_TRACE_DIR = _ROOT / "docs" / "reports" / "strategy" / "shadow"
SHADOW_TRACE_FILE = SHADOW_TRACE_DIR / "hermes_cfo_loop_shadow_traces.jsonl"

# ── Valid config values ────────────────────────────────────────────────────────

_VALID_MODES = ("off", "shadow", "limited_primary", "primary")
_VALID_PROVIDERS = ("mock", "openrouter", "deepseek", "local")

# ── Phase 8C: Limited primary config ──────────────────────────────────────────

LIMITED_PRIMARY_CONFIDENCE_THRESHOLD = 0.80

ALLOWLISTED_INTENTS = frozenset({
    "implementation_prompt_request",
    "acknowledgement_check",
    "scout_status",
    "approval_bulk_request",
    "draft_comparison",
    "plain_language_followup",
    "simplify_previous_response",
    "explain_previous_response",
    "summary_of_day",
    "implement_now",
})

HARD_BLOCKED_INTENTS = frozenset({
    "publish_content",
    "send_email",
    "subscriber_email",
    "social_posting",
    "payment_activation",
    "stripe_activation",
    "affiliate_application",
    "production_deploy",
    "live_trading",
    "client_facing_use",
    "paid_tool_signup",
    "external_purchase",
    "database_migration",
})

# ── Live-failure markers ───────────────────────────────────────────────────────

_LIVE_FAILURE_MARKERS = [
    "i wasn't able to generate a quality response",
    "plain-language mode enabled",
    "i don't have task",
    "i don't have the option list",
    "i don't have a previous response",
    "i don't have a recent recommendation",
    "live answer sources:",
    "hermes report",
    "artifact_inventory",
    "i can answer from verified artifacts",
]


# ── Config ─────────────────────────────────────────────────────────────────────

def get_cfo_loop_mode() -> str:
    """Return current CFO loop mode. Full primary falls back to limited_primary."""
    raw = os.getenv("HERMES_CFO_LOOP_MODE", "off").lower().strip()
    if raw not in _VALID_MODES:
        return "off"
    if raw == "primary":
        logger.warning("hermes_cfo_loop: full primary mode is blocked — falling back to limited_primary")
        return "limited_primary"
    return raw


def get_cfo_loop_provider() -> str:
    """Return current provider. Defaults to mock (no network calls)."""
    raw = os.getenv("HERMES_CFO_LOOP_PROVIDER", "mock").lower().strip()
    if raw not in _VALID_PROVIDERS:
        return "mock"
    return raw


def is_shadow_mode_active() -> bool:
    return get_cfo_loop_mode() == "shadow"


def is_limited_primary_mode_active() -> bool:
    return get_cfo_loop_mode() == "limited_primary"


def is_primary_mode_blocked() -> bool:
    """Full primary mode is always blocked."""
    return True


# ── Should-run gate ────────────────────────────────────────────────────────────

_CFO_STATUS_CMDS = (
    "show cfo shadow", "compare cfo shadow", "clear cfo shadow",
    "show cfo loop mode", "show cfo limited", "show cfo primary",
    "rollback cfo",
)


def should_run_cfo_shadow(message: str) -> bool:
    """True only in shadow mode (not limited_primary) when message is meaningful."""
    if get_cfo_loop_mode() != "shadow":
        return False
    if not message or len(message.strip()) < 2:
        return False
    msg_lower = message.strip().lower()
    if any(cmd in msg_lower for cmd in _CFO_STATUS_CMDS):
        return False
    return True


def should_run_cfo_limited_primary(message: str) -> bool:
    """True only in limited_primary mode when message is meaningful."""
    if get_cfo_loop_mode() != "limited_primary":
        return False
    if not message or len(message.strip()) < 2:
        return False
    msg_lower = message.strip().lower()
    if any(cmd in msg_lower for cmd in _CFO_STATUS_CMDS):
        return False
    return True


# ── State seeding ─────────────────────────────────────────────────────────────

def _seed_state_from_current(state) -> None:
    """Load live conversation state into CFO loop prototype state."""
    try:
        from lib.hermes_conversation_state import load_conversation_state
        cs = load_conversation_state()
        state.last_option_map = cs.get("last_option_map") or {}
        state.last_selected_option = cs.get("last_selected_option_number")
        state.last_selected_option_text = cs.get("last_selected_option_text")
        state.active_recommendation = cs.get("active_recommendation")
        state.last_meaningful_response = cs.get("last_meaningful_response")
        state.last_meaningful_response_summary = cs.get("last_meaningful_response_summary")
        state.current_topic = cs.get("current_topic")
        _lr = (cs.get("last_meaningful_response") or "").lower()
        state.last_response_was_approval_queue = "approval queue" in _lr
        state.last_response_was_draft = (
            (cs.get("current_topic") or "").startswith("lead_magnet") or "draft" in _lr
        )
    except Exception:
        pass


# ── Core shadow runner ─────────────────────────────────────────────────────────

def run_cfo_shadow_for_message(
    message: str,
    live_response: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Run the CFO loop in shadow mode. Returns trace dict (already saved). Never raises."""
    start = time.time()
    error: Optional[str] = None
    cfo_result: Optional[dict] = None

    try:
        from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop
        loop = HermesCFOLoop()
        _seed_state_from_current(loop.state)
        cfo_response, trace_info = loop.process(message)
        cfo_result = {"response": cfo_response, "trace": trace_info}
    except Exception as exc:
        error = str(exc)[:300]
        logger.debug("hermes_cfo_shadow error: %s", error)

    duration_ms = int((time.time() - start) * 1000)
    trace = build_shadow_trace(
        message=message,
        live_response=live_response,
        cfo_result=cfo_result,
        error=error,
        duration_ms=duration_ms,
        metadata=metadata,
    )
    save_shadow_trace(trace)
    return trace


def run_cfo_shadow_async(
    message: str,
    live_response: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> None:
    """Fire-and-forget: run CFO shadow in a daemon thread. Never blocks caller."""
    try:
        t = threading.Thread(
            target=run_cfo_shadow_for_message,
            args=(message,),
            kwargs={"live_response": live_response, "metadata": metadata},
            daemon=True,
            name="cfo_shadow",
        )
        t.start()
    except Exception as exc:
        logger.debug("hermes_cfo_shadow_async error: %s", exc)


# ── Phase 8C: Limited primary runner ──────────────────────────────────────────

def run_cfo_limited_primary(
    message: str,
    metadata: Optional[dict] = None,
) -> tuple[Optional[str], bool]:
    """
    Run CFO loop in limited_primary mode.
    Returns (cfo_response, primary_used).
    - Allowlisted intent + confidence >= threshold → (response, True)
    - Otherwise → (None, False); trace still saved
    Never raises.
    """
    start = time.time()
    error: Optional[str] = None
    cfo_result: Optional[dict] = None
    primary_used = False
    fallback_reason: Optional[str] = None

    try:
        from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop
        loop = HermesCFOLoop()
        _seed_state_from_current(loop.state)
        cfo_response, trace_info = loop.process(message)
        cfo_result = {"response": cfo_response, "trace": trace_info}

        intent = trace_info.get("intent")
        confidence = trace_info.get("confidence", 0.0)

        if intent in HARD_BLOCKED_INTENTS:
            fallback_reason = f"intent_{intent}_is_hard_blocked"
        elif intent not in ALLOWLISTED_INTENTS:
            fallback_reason = f"intent_{intent}_not_allowlisted"
        elif confidence < LIMITED_PRIMARY_CONFIDENCE_THRESHOLD:
            fallback_reason = f"confidence_{confidence:.2f}_below_threshold"
        else:
            primary_used = True

    except Exception as exc:
        error = str(exc)[:300]
        fallback_reason = f"error:{error}"
        logger.debug("hermes_cfo_limited_primary error: %s", error)

    duration_ms = int((time.time() - start) * 1000)
    trace = _build_primary_trace(
        message=message,
        cfo_result=cfo_result,
        primary_used=primary_used,
        fallback_reason=fallback_reason,
        error=error,
        duration_ms=duration_ms,
        metadata=metadata,
    )
    save_shadow_trace(trace)

    if primary_used and cfo_result:
        return cfo_result["response"], True
    return None, False


def _build_primary_trace(
    message: str,
    cfo_result: Optional[dict],
    primary_used: bool,
    fallback_reason: Optional[str] = None,
    error: Optional[str] = None,
    duration_ms: int = 0,
    metadata: Optional[dict] = None,
) -> dict:
    msg_lower = (message or "").strip().lower()
    msg_hash = hashlib.md5(msg_lower.encode()).hexdigest()[:12]

    cfo_intent = None
    cfo_tool = None
    cfo_confidence = None
    cfo_response_preview = None
    safety_flags: list = []

    if cfo_result and not error:
        t = cfo_result.get("trace", {})
        cfo_intent = t.get("intent")
        cfo_tool = t.get("tool")
        cfo_confidence = t.get("confidence")
        cfo_resp = cfo_result.get("response", "")
        cfo_response_preview = _sanitize_for_log(cfo_resp[:250]) if cfo_resp else None

        if cfo_resp:
            resp_lower = cfo_resp.lower()
            for r in ("activated payment", "published to", "sent to subscribers",
                      "deployed to production", "ran live trade"):
                if r in resp_lower:
                    safety_flags.append(f"primary_response_mentions: {r}")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_hash": msg_hash,
        "normalized_message": msg_lower[:200],
        "live_response_header": None,
        "live_response_changed": primary_used,
        "cfo_loop_mode": "limited_primary",
        "cfo_provider": get_cfo_loop_provider(),
        "cfo_intent": cfo_intent,
        "cfo_selected_tool": cfo_tool,
        "cfo_confidence": cfo_confidence,
        "cfo_recommendation_summary": None,
        "cfo_response_preview": cfo_response_preview,
        "would_have_fixed_failure": False,
        "evidence_keys_used": [],
        "safety_flags": safety_flags,
        "error": error,
        "duration_ms": duration_ms,
        "primary_used": primary_used,
        "fallback_reason": fallback_reason,
        "mode": "limited_primary",
    }


# ── Trace building (shadow) ────────────────────────────────────────────────────

def build_shadow_trace(
    message: str,
    live_response: Optional[str],
    cfo_result: Optional[dict],
    error: Optional[str] = None,
    duration_ms: int = 0,
    metadata: Optional[dict] = None,
) -> dict:
    msg_lower = (message or "").strip().lower()
    msg_hash = hashlib.md5(msg_lower.encode()).hexdigest()[:12]

    live_header = ""
    if live_response:
        lines = live_response.strip().splitlines()
        live_header = lines[0][:80] if lines else ""

    cfo_intent = None
    cfo_tool = None
    cfo_confidence = None
    cfo_response_preview = None
    would_have_fixed = False
    evidence_keys: list = []
    safety_flags: list = []

    if cfo_result and not error:
        t = cfo_result.get("trace", {})
        cfo_intent = t.get("intent")
        cfo_tool = t.get("tool")
        cfo_confidence = t.get("confidence")
        cfo_resp = cfo_result.get("response", "")
        cfo_response_preview = _sanitize_for_log(cfo_resp[:250]) if cfo_resp else None

        if live_response:
            live_lower = live_response.lower()
            would_have_fixed = any(m in live_lower for m in _LIVE_FAILURE_MARKERS)

        if cfo_resp:
            resp_lower = cfo_resp.lower()
            for r in ("activated payment", "published to", "sent to subscribers",
                      "deployed to production", "ran live trade"):
                if r in resp_lower:
                    safety_flags.append(f"shadow_response_mentions: {r}")

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message_hash": msg_hash,
        "normalized_message": msg_lower[:200],
        "live_response_header": live_header,
        "live_response_changed": False,
        "cfo_loop_mode": get_cfo_loop_mode(),
        "cfo_provider": get_cfo_loop_provider(),
        "cfo_intent": cfo_intent,
        "cfo_selected_tool": cfo_tool,
        "cfo_confidence": cfo_confidence,
        "cfo_recommendation_summary": None,
        "cfo_response_preview": cfo_response_preview,
        "would_have_fixed_failure": would_have_fixed,
        "evidence_keys_used": evidence_keys,
        "safety_flags": safety_flags,
        "error": error,
        "duration_ms": duration_ms,
    }


def _sanitize_for_log(text: str) -> str:
    import re
    for p in (
        r"sk-[A-Za-z0-9]{20,}",
        r"Bearer\s+[A-Za-z0-9\-_\.]{20,}",
        r"SUPABASE_[A-Z_]+=\S+",
        r"[Aa][Pp][Ii]_?[Kk][Ee][Yy]=\S+",
    ):
        text = re.sub(p, "[REDACTED]", text)
    return text


# ── Trace persistence ──────────────────────────────────────────────────────────

def save_shadow_trace(trace: dict) -> None:
    try:
        SHADOW_TRACE_DIR.mkdir(parents=True, exist_ok=True)
        with open(SHADOW_TRACE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace) + "\n")
    except Exception as exc:
        logger.debug("hermes_cfo_shadow save_trace error: %s", exc)


def load_shadow_traces(limit: int = 100) -> list[dict]:
    if not SHADOW_TRACE_FILE.exists():
        return []
    lines = SHADOW_TRACE_FILE.read_text(encoding="utf-8").strip().splitlines()
    parsed = []
    for line in lines[-limit:]:
        try:
            parsed.append(json.loads(line))
        except Exception:
            pass
    return parsed


def clear_shadow_traces() -> int:
    if not SHADOW_TRACE_FILE.exists():
        return 0
    lines = SHADOW_TRACE_FILE.read_text(encoding="utf-8").strip().splitlines()
    count = len([ln for ln in lines if ln.strip()])
    SHADOW_TRACE_FILE.write_text("", encoding="utf-8")
    return count


# ── Formatting ─────────────────────────────────────────────────────────────────

def format_shadow_status() -> str:
    mode = get_cfo_loop_mode()
    provider = get_cfo_loop_provider()
    traces = load_shadow_traces(limit=100)
    n = len(traces)
    last = traces[-1] if traces else None

    last_intent = last["cfo_intent"] if last else "none"
    last_tool = last["cfo_selected_tool"] if last else "none"
    last_error_count = sum(1 for t in traces if t.get("error"))
    fixed_count = sum(1 for t in traces if t.get("would_have_fixed_failure"))

    lines = [
        "CFO LOOP SHADOW STATUS\n",
        f"Mode: {mode}",
        f"Provider: {provider}",
        "Live response changed: NO",
        "",
        f"Recent traces: {n}",
        f"Last intent: {last_intent}",
        f"Last selected tool: {last_tool}",
        f"Would-have-fixed count: {fixed_count}/{n}" if n else "Would-have-fixed count: 0/0",
        f"Errors: {last_error_count}",
        "",
        "Safety:",
        "  Shadow mode does not change Telegram responses.",
        "  No Supabase writes.",
        "  No public/paid/client-facing actions.",
        "",
        "Approval boundary:",
        "  I will not publish, email, spend money, apply to affiliates,",
        "  activate payments, deploy production changes, or run live trading.",
    ]
    return "\n".join(lines)


def format_limited_primary_status() -> str:
    mode = get_cfo_loop_mode()
    provider = get_cfo_loop_provider()
    traces = load_shadow_traces(limit=100)
    primary_count = sum(1 for t in traces if t.get("primary_used"))
    n = len(traces)

    lines = [
        "CFO LOOP LIMITED PRIMARY STATUS\n",
        f"Mode: {mode}",
        f"Provider: {provider}",
        "",
        "Allowlisted intents:",
    ]
    for intent in sorted(ALLOWLISTED_INTENTS):
        lines.append(f"  - {intent}")
    lines.extend([
        "",
        "Full primary: blocked",
        "",
        f"Traces: {n} total, {primary_count} used as primary response",
        "",
        "Safety:",
        "  No publishing, email, payment, affiliate signup, deploy,",
        "  Supabase writes, or live trading.",
        "",
        "Rollback:",
        "  Set HERMES_CFO_LOOP_MODE=shadow and restart.",
        "  Edit: ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist",
        "  Then: launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist",
        "  Then: launchctl load ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist",
    ])
    return "\n".join(lines)


def format_recent_shadow_traces(limit: int = 10) -> str:
    traces = load_shadow_traces(limit=limit)
    if not traces:
        return (
            "CFO SHADOW TRACES\n\n"
            "No traces yet.\n\n"
            "Shadow mode must be active and at least one message sent.\n\n"
            "Approval boundary:\n"
            "  Shadow mode does not change live responses."
        )

    lines = ["CFO SHADOW TRACES\n", f"Recent traces (last {len(traces)}):\n"]
    for i, t in enumerate(traces[-limit:], 1):
        msg = t.get("normalized_message", "")[:60]
        intent = t.get("cfo_intent", "unknown")
        tool = t.get("cfo_selected_tool", "unknown")
        fixed = "yes" if t.get("would_have_fixed_failure") else "no"
        conf = t.get("cfo_confidence")
        conf_str = f"{conf:.0%}" if conf is not None else "n/a"
        err = " [ERROR]" if t.get("error") else ""
        primary = " [PRIMARY]" if t.get("primary_used") else ""
        lines.append(f"  {i}. Message: {msg}")
        lines.append(f"     Intent: {intent}")
        lines.append(f"     Tool: {tool}")
        lines.append(f"     Would have fixed live issue: {fixed}")
        lines.append(f"     Confidence: {conf_str}{err}{primary}")
        lines.append("")

    lines.append("Approval boundary:")
    lines.append("  Shadow mode does not change live responses.")
    return "\n".join(lines)


def compare_live_vs_shadow(
    live_response: Optional[str] = None,
    shadow_response: Optional[str] = None,
) -> str:
    traces = load_shadow_traces(limit=10)

    if not traces:
        return (
            "CFO LIVE VS SHADOW COMPARISON\n\n"
            "No shadow traces available yet.\n\n"
            "Send a message first, then run 'compare cfo shadow'.\n\n"
            "Approval boundary:\n"
            "  Shadow mode does not change live responses."
        )

    last = traces[-1]
    shadow_preview = last.get("cfo_response_preview", "not available")
    live_header = last.get("live_response_header", "not available")
    cfo_intent = last.get("cfo_intent", "unknown")
    cfo_tool = last.get("cfo_selected_tool", "unknown")
    msg = last.get("normalized_message", "")[:80]
    fixed = last.get("would_have_fixed_failure", False)
    primary_used = last.get("primary_used", False)

    if live_response and shadow_response:
        same = live_response.strip()[:100] == shadow_response.strip()[:100]
        diff_note = "Responses are similar." if same else "Shadow response would differ from live response."
    else:
        diff_note = "Live response was: " + (live_header or "unknown")

    lines = [
        "CFO LIVE VS SHADOW COMPARISON\n",
        f"Message: {msg}\n",
        "Live response:",
        f"  {live_header}",
        "",
        "CFO Loop would have:",
        f"  Intent: {cfo_intent}",
        f"  Tool: {cfo_tool}",
        f"  Preview: {(shadow_preview or 'n/a')[:150]}",
        f"  Primary used: {'yes' if primary_used else 'no'}",
        "",
        f"Difference: {diff_note}",
        f"Would have fixed a known live failure: {'yes' if fixed else 'no'}",
        "",
        "Approval boundary:",
        "  Shadow mode does not change live responses.",
    ]
    return "\n".join(lines)


def summarize_shadow_trace(trace: dict) -> str:
    intent = trace.get("cfo_intent", "unknown")
    tool = trace.get("cfo_selected_tool", "unknown")
    conf = trace.get("cfo_confidence")
    msg = trace.get("normalized_message", "")[:60]
    fixed = trace.get("would_have_fixed_failure", False)
    err = trace.get("error")
    parts = [f"msg={msg!r}", f"intent={intent}", f"tool={tool}"]
    if conf is not None:
        parts.append(f"conf={conf:.2f}")
    if fixed:
        parts.append("would_fix=yes")
    if err:
        parts.append(f"error={err[:40]}")
    return " | ".join(parts)


# ── Rollback ───────────────────────────────────────────────────────────────────

def format_rollback_instructions() -> str:
    return (
        "CFO LOOP ROLLED BACK TO SHADOW\n\n"
        "Manual rollback steps:\n\n"
        "  1. Edit the plist:\n"
        "     ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist\n\n"
        "  2. Set HERMES_CFO_LOOP_MODE to: shadow\n\n"
        "  3. Unload the service:\n"
        "     launchctl unload ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist\n\n"
        "  4. Reload the service:\n"
        "     launchctl load ~/Library/LaunchAgents/com.raymonddavis.nexus.telegram.plist\n\n"
        "Approval boundary:\n"
        "  Cannot modify launchctl env from Telegram directly — plist edit required."
    )


# ── Telegram command handler ───────────────────────────────────────────────────

def handle_cfo_shadow_command(normalized: str) -> Optional[str]:
    """
    Handle CFO shadow/primary Telegram commands. Returns response string or None.
    Called before Phase 7C intercept in telegram_bot.py.
    """
    cmd_map = {
        # Phase 8B commands
        "show cfo shadow status": format_shadow_status,
        "cfo shadow status": format_shadow_status,
        "show cfo loop mode": format_shadow_status,
        "cfo loop mode": format_shadow_status,
        "show cfo shadow traces": lambda: format_recent_shadow_traces(10),
        "cfo shadow traces": lambda: format_recent_shadow_traces(10),
        "compare cfo shadow": compare_live_vs_shadow,
        "cfo shadow compare": compare_live_vs_shadow,
        "clear cfo shadow test traces": _handle_clear_traces,
        "clear cfo shadow traces": _handle_clear_traces,
        # Phase 8C commands
        "show cfo limited primary status": format_limited_primary_status,
        "cfo limited primary status": format_limited_primary_status,
        "show cfo primary status": format_limited_primary_status,
        "cfo primary status": format_limited_primary_status,
        "rollback cfo loop to shadow": format_rollback_instructions,
        "rollback cfo to shadow": format_rollback_instructions,
    }
    cleaned = normalized.strip().rstrip(".?!").strip()
    if cleaned in cmd_map:
        try:
            return cmd_map[cleaned]()
        except Exception as exc:
            logger.warning("hermes_cfo_shadow_command error: %s", exc)
            return (
                f"CFO LOOP STATUS\n\nError running command: {str(exc)[:100]}\n\n"
                "Approval boundary:\n  Shadow mode does not change live responses."
            )
    return None


def _handle_clear_traces() -> str:
    count = clear_shadow_traces()
    return (
        f"CFO LOOP SHADOW STATUS\n\n"
        f"Cleared {count} shadow test trace(s).\n\n"
        "Approval boundary:\n"
        "  Shadow mode does not change live responses."
    )
