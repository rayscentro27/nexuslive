"""
hermes_gate.py — Central gate for ALL outbound Hermes Telegram messages.

Every Telegram send in the system MUST call hermes_gate.send() instead of
calling the Telegram API directly. The gate enforces:

  1. Global rate limit  — max 5 messages per hour (hard cap)
  2. Per-event cooldown — configurable per event_type
  3. Deduplication      — hash(event_type + key_data) suppresses identical events
  4. Signal filter      — empty / "nothing to report" messages are silently dropped
  5. Logging           — every suppression is logged with reason

Silence is correct behavior. Hermes only speaks when it matters.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('HermesGate')


_HARD_DENY_EVENT_TOKENS = {
    'trading',
    'signal',
    'research',
    'youtube',
    'ingest',
    'scheduled_summary',
    'weekly_summary',
    'daily_summary',
    'worker_summary',
    'model_error_report',
    'research_brief',
    'trading_alert',
    'opportunity_brief',
    'trading_summary',
    'youtube_summary',
    'ingestion_summary',
    'automatic_status',
    'cron_report',
    'scheduler_report',
    'retry_error_report',
    'background_report',
    'opportunity',
    'grant',
    'topic_brief',
    'run_summary',
    'queue_summary',
    'auto_digest',
}

_ALLOW_EVENT_TYPES = {
    'conversational_reply',
    'critical_alert',
    'explicit_operator_requested_digest',
    'coding_agent_completion_ack',
}


def _auto_reports_enabled() -> bool:
    if os.getenv('TELEGRAM_MANUAL_ONLY', 'true').lower() in {'1', 'true', 'yes', 'on'}:
        return False
    return os.getenv('TELEGRAM_AUTO_REPORTS_ENABLED', 'false').lower() in {'1', 'true', 'yes', 'on'}


def _telegram_enabled() -> bool:
    return os.getenv('TELEGRAM_ENABLED', 'true').lower() in {'1', 'true', 'yes', 'on'}


# ── Config ─────────────────────────────────────────────────────────────────────

GLOBAL_RATE_LIMIT    = int(os.getenv('HERMES_RATE_LIMIT_PER_HOUR', '5'))
SUPABASE_URL         = os.getenv('SUPABASE_URL', '')

# Use service role for gate state persistence
_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY', '')

# Per-event-type cooldown in hours (overridable via env)
COOLDOWN_HOURS: dict[str, float] = {
    'critical':        float(os.getenv('GATE_COOLDOWN_CRITICAL', '1')),
    'warning':         float(os.getenv('GATE_COOLDOWN_WARNING',  '4')),
    'summary':         float(os.getenv('GATE_COOLDOWN_SUMMARY',  '24')),
    'recovery':        float(os.getenv('GATE_COOLDOWN_RECOVERY', '1')),
    'default':         float(os.getenv('GATE_COOLDOWN_DEFAULT',  '4')),
}

# Phrases that mean "nothing happened" — always suppressed
_EMPTY_PATTERNS = [
    'no report', 'nothing to report', 'no update', 'nothing found',
    'no issues', 'all clear', 'no alerts', 'all checks passed',
    'no activity', 'no changes', 'no new', 'nothing new',
    '0 email', '0 email(s)', 'done — 0', 'processed: 0',
    'no action required',
]

# Content patterns that must never reach Telegram automatically.
# These are auto-report artifacts that should only go to email/file.
_FORBIDDEN_CONTENT_PATTERNS = [
    '🏛️ nexus research',
    '🏛️ nexus intelligence brief',
    '🏛️ nexus research run complete',
    'key findings:',
    'sources:',
    'research artifacts saved',
    'intelligence brief',
    'nexus research run complete',
]


def _contains_forbidden_content(text: str) -> bool:
    """Return True if message contains auto-report patterns forbidden in Telegram."""
    lowered = text.lower().strip()
    return any(p in lowered for p in _FORBIDDEN_CONTENT_PATTERNS)

# ── Supabase helpers ───────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        'apikey':        _KEY,
        'Authorization': f'Bearer {_KEY}',
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
    }


def _sb_get(path: str) -> list:
    if not SUPABASE_URL or not _KEY:
        return []
    try:
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers={**_headers(), 'Prefer': ''},
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else []
    except Exception as e:
        logger.debug(f"_sb_get {path}: {e}")
        return []


def _sb_post(path: str, body: dict) -> bool:
    if not SUPABASE_URL or not _KEY:
        return False
    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f"{SUPABASE_URL}/rest/v1/{path}",
            data=data, headers=_headers(), method='POST',
        )
        with urllib.request.urlopen(req, timeout=8) as _:
            return True
    except Exception as e:
        logger.debug(f"_sb_post {path}: {e}")
        return False


# ── Gate checks ────────────────────────────────────────────────────────────────

def _is_empty(text: str) -> bool:
    """Return True if the message contains no actionable content."""
    lowered = text.lower().strip()
    return any(p in lowered for p in _EMPTY_PATTERNS)


def _event_hash(event_type: str, text: str) -> str:
    """Stable hash for deduplication — same event + same text = same hash."""
    normalized = text.strip().lower()[:300]
    return hashlib.sha256(f"{event_type}::{normalized}".encode()).hexdigest()[:16]


def _critical_event_hash(event_type: str) -> str:
    """Stable hash for critical dedup when auto reports are disabled."""
    return hashlib.sha256(f"critical::{event_type}".encode()).hexdigest()[:16]


def _rate_limit_ok() -> bool:
    """Return True if we're under the hourly cap."""
    if not SUPABASE_URL:
        return True  # no DB → allow (fail open)
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    rows = _sb_get(
        f"hermes_aggregates?event_source=eq.hermes_gate"
        f"&created_at=gt.{cutoff}&select=id&limit={GLOBAL_RATE_LIMIT + 1}"
    )
    return len(rows) < GLOBAL_RATE_LIMIT


def _cooldown_ok(event_type: str, event_hash: str, severity: str = 'default') -> bool:
    """Return True if enough time has passed since this event last fired."""
    if not SUPABASE_URL:
        return True
    hours = COOLDOWN_HOURS.get(severity, COOLDOWN_HOURS['default'])
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows = _sb_get(
        f"hermes_aggregates?event_source=eq.hermes_gate"
        f"&event_type=eq.{event_type}"
        f"&classification=eq.{event_hash}"
        f"&created_at=gt.{cutoff}&select=id&limit=1"
    )
    return len(rows) == 0


def _record_send(event_type: str, event_hash: str, summary: str) -> None:
    """Write a gate record so future calls can enforce cooldowns."""
    _sb_post('hermes_aggregates', {
        'event_source':      'hermes_gate',
        'event_type':        event_type,
        'classification':    event_hash,
        'aggregated_summary': summary[:500],
        'alert_sent':         True,
    })


def record_digest_item(digest_type: str, summary: str, payload: dict | None = None) -> bool:
    """Store routine events for later digest aggregation (no Telegram send)."""
    if not digest_type or not summary:
        return False
    return _sb_post('hermes_aggregates', {
        'event_source': 'digest_collector',
        'event_type': digest_type,
        'classification': 'digest_item',
        'aggregated_summary': summary[:500],
        'alert_sent': False,
    })


# ── Telegram send ──────────────────────────────────────────────────────────────

def _telegram_send(text: str, bot_token: str, chat_id: str, parse_mode: str = 'HTML') -> bool:
    """Raw Telegram API call."""
    url  = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = json.dumps({
        'chat_id':    chat_id,
        'text':       text[:4096],
        'parse_mode': parse_mode,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except urllib.error.HTTPError as e:
        try:
            details = e.read().decode('utf-8', errors='ignore').lower()
        except Exception:
            details = ''
        if e.code == 400 and "can't parse entities" in details:
            fallback = json.dumps({
                'chat_id': chat_id,
                'text': text[:4096],
            }).encode()
            retry_req = urllib.request.Request(url, data=fallback, headers={'Content-Type': 'application/json'})
            try:
                with urllib.request.urlopen(retry_req, timeout=10) as _:
                    logger.warning('Telegram HTML parse failed; resent message without parse_mode')
                    return True
            except Exception as retry_err:
                logger.warning(f'Telegram fallback send failed: {retry_err}')
                return False
        logger.warning(f'Telegram send failed: HTTP {e.code}')
        return False
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")
        return False


def telegram_policy_allows_send(
    *,
    event_type: str,
    source: str = 'unknown',
    user_requested: bool = False,
    is_command: bool = False,
    is_approval: bool = False,
    is_completion: bool = False,
) -> tuple[bool, str]:
    event_lower = (event_type or '').strip().lower()
    alias_map = {
        'direct_chat_reply': 'conversational_reply',
        'command_reply': 'conversational_reply',
        'approval_request': 'conversational_reply',
        'approval_result': 'conversational_reply',
        'user_requested_completion_notice': 'coding_agent_completion_ack',
        'user_requested_email_report_confirmation': 'explicit_operator_requested_digest',
    }
    event_lower = alias_map.get(event_lower, event_lower)

    if not event_lower:
        return False, 'missing_event_type'

    if any(token in event_lower for token in _HARD_DENY_EVENT_TOKENS):
        return False, 'scheduled_or_background_summary'

    if source in {'scheduler', 'worker', 'background', 'cron'}:
        return False, 'scheduled_or_background_summary'

    if event_lower == 'critical_alert':
        return True, 'allowed_critical'

    if event_lower == 'explicit_operator_requested_digest' and user_requested:
        return True, 'allowed_operator_digest'

    if event_lower == 'coding_agent_completion_ack' and user_requested:
        return True, 'allowed_coding_ack'

    if event_lower == 'conversational_reply':
        return True, 'allowed_conversational'

    if event_lower in _ALLOW_EVENT_TYPES:
        return True, 'allowed_explicit_type'

    return False, 'not_allowlisted'


# ── Public API ─────────────────────────────────────────────────────────────────

def send(
    text: str,
    event_type: str = 'general',
    severity: str   = 'default',
    bot_token: str  = '',
    chat_id: str    = '',
    force: bool     = False,
) -> bool:
    """
    Gated Telegram send. Returns True if message was sent, False if suppressed.

    Args:
        text:       Message body (HTML OK)
        event_type: Logical category (e.g. 'NO_REVENUE', 'worker_alert')
        severity:   'critical' | 'warning' | 'summary' | 'recovery' | 'default'
        bot_token:  Telegram bot token (falls back to TELEGRAM_BOT_TOKEN env)
        chat_id:    Telegram chat ID (falls back to TELEGRAM_CHAT_ID env)
        force:      Skip all gate checks (use only for user-requested commands)
    """
    token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat  = chat_id  or os.getenv('TELEGRAM_CHAT_ID', '')

    if not _telegram_enabled():
        logger.info("Gate: TELEGRAM_ENABLED=false — suppressed")
        return False

    if not token or not chat:
        logger.debug("Gate: no bot token/chat_id configured — suppressed")
        return False

    if not force:
        allowed, reason = telegram_policy_allows_send(event_type=event_type, source='gate')
        if not allowed:
            logger.info(f"telegram_policy denied=true message_type={event_type} source=gate reason={reason}")
            return False

        # Conversational mode: suppress all automated non-critical outbound reports.
        if not _auto_reports_enabled() and severity != 'critical':
            logger.info("Telegram auto-report suppressed; conversational mode still enabled")
            return False

        # 1a. Forbidden content check — auto-report artifacts never go to Telegram
        if _contains_forbidden_content(text):
            logger.info(f"Gate suppressed [{event_type}]: forbidden_content_pattern — save to email/file instead")
            return False

        # 1b. Empty signal check
        if _is_empty(text):
            logger.info(f"Gate suppressed [{event_type}]: no actionable content")
            return False

        # 2. Global rate limit
        if not _rate_limit_ok():
            logger.warning(f"Gate: RATE LIMIT HIT — suppressing [{event_type}]")
            return False

        # 3. Per-event cooldown + dedup
        if not _auto_reports_enabled() and severity == 'critical':
            h = _critical_event_hash(event_type)
        else:
            h = _event_hash(event_type, text)
        if not _cooldown_ok(event_type, h, severity):
            logger.info(f"Gate suppressed [{event_type}] hash={h}: cooldown active")
            return False

    # Send
    ok = _telegram_send(text, token, chat)
    if ok:
        if not _auto_reports_enabled() and severity == 'critical':
            h = _critical_event_hash(event_type)
        else:
            h = _event_hash(event_type, text)
        _record_send(event_type, h, text[:200])
        logger.info(f"Gate SENT [{event_type}] severity={severity}")
    return ok


def send_critical(text: str, event_type: str, **kwargs) -> bool:
    return send(text, event_type=event_type, severity='critical', **kwargs)


def send_warning(text: str, event_type: str, **kwargs) -> bool:
    return send(text, event_type=event_type, severity='warning', **kwargs)


def send_summary(text: str, event_type: str, **kwargs) -> bool:
    return send(text, event_type=event_type, severity='summary', **kwargs)


def send_recovery(text: str, event_type: str, **kwargs) -> bool:
    return send(text, event_type=event_type, severity='recovery', **kwargs)


def send_on_demand(text: str, event_type: str = 'on_demand', **kwargs) -> bool:
    """User-requested send — skips all gate checks except token validation."""
    return send(text, event_type=event_type, force=True, **kwargs)


def send_direct_response(
    text: str,
    event_type: str = 'direct_response',
    bot_token: str  = '',
    chat_id: str    = '',
    parse_mode: str = 'HTML',
) -> bool:
    """
    Reply directly to a user command.

    Distinction from automated alerts:
      - Bypasses global rate limit (user asked, so we must answer)
      - Bypasses per-event cooldown (user asked again, so we answer again)
      - Deduplicates ONLY within 60 seconds (prevents double-send on bot restarts)
      - Never filtered for "empty signal" (user asked a question, we answer it)

    Use this for all replies to /commands and user messages.
    Use send() for automated system alerts.
    """
    token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat  = chat_id  or os.getenv('TELEGRAM_CHAT_ID', '')

    if not _telegram_enabled():
        logger.info("send_direct_response: TELEGRAM_ENABLED=false")
        return False

    if not token or not chat:
        logger.debug("send_direct_response: no bot token/chat_id configured")
        return False

    allowed, reason = telegram_policy_allows_send(
        event_type=event_type,
        source='direct',
        user_requested=True,
        is_command=event_type == 'command_reply',
        is_approval='approval' in event_type,
        is_completion='completion' in event_type,
    )
    if not allowed:
        logger.info(f"telegram_policy denied=true message_type={event_type} source=direct reason={reason}")
        return False

    # Belt-and-suspenders: never send forbidden auto-report content even in direct replies
    if _contains_forbidden_content(text):
        logger.info(f"send_direct_response suppressed [{event_type}]: forbidden_content_pattern")
        return False

    # 60-second dedup window — prevents exact-duplicate double-sends only
    h = _event_hash(event_type, text)
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    rows = _sb_get(
        f"hermes_aggregates?event_source=eq.hermes_gate_direct"
        f"&event_type=eq.{event_type}"
        f"&classification=eq.{h}"
        f"&created_at=gt.{cutoff}&select=id&limit=1"
    )
    if rows:
        logger.info(f"send_direct_response dedup [{event_type}] hash={h}: exact duplicate within 60s")
        return False

    ok = _telegram_send(text, token, chat, parse_mode=parse_mode)
    if ok:
        _sb_post('hermes_aggregates', {
            'event_source':       'hermes_gate_direct',
            'event_type':         event_type,
            'classification':     h,
            'aggregated_summary': text[:500],
            'alert_sent':         True,
        })
        logger.info(f"send_direct_response SENT [{event_type}]")
    return ok
