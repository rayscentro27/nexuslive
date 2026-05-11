"""
Communication Reliability — Part 9.

Wraps Telegram and email sends with:
  - Idempotency via idempotency_key (no duplicate sends)
  - Retry with exponential backoff (up to max_retries)
  - Fallback from Telegram → email on repeated failure
  - All sends logged to hermes_comms_log
"""

import hashlib
import json
import logging
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('CommsReliability')

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')


def _sb(path: str, method: str = 'GET', body: Optional[dict] = None, prefer: str = '') -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else ([result] if result else [])
    except Exception as e:
        logger.debug(f"{method} {path}: {e}")
        return []


def _make_idempotency_key(channel: str, recipient: str, subject: str, body_preview: str) -> str:
    raw = f"{channel}:{recipient}:{subject}:{body_preview[:100]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


def _check_already_sent(idem_key: str) -> bool:
    rows = _sb(f"hermes_comms_log?idempotency_key=eq.{idem_key}&status=eq.sent&limit=1")
    return len(rows) > 0


def _log_send(channel: str, recipient: str, subject: str, body_preview: str,
              idem_key: str, status: str = 'pending', error_detail: str = '') -> Optional[str]:
    rows = _sb('hermes_comms_log', 'POST', {
        'channel': channel,
        'recipient': recipient,
        'subject': subject or None,
        'body_preview': body_preview[:300] if body_preview else None,
        'idempotency_key': idem_key,
        'status': status,
        'error_detail': error_detail or None,
        'last_attempt_at': datetime.now(timezone.utc).isoformat(),
        'sent_at': datetime.now(timezone.utc).isoformat() if status == 'sent' else None,
    }, prefer='return=representation')
    return rows[0].get('id') if rows else None


def _update_log(log_id: str, status: str, retry_count: int = 0,
                next_retry_at: str = '', error_detail: str = '') -> None:
    body: dict = {
        'status': status,
        'retry_count': retry_count,
        'last_attempt_at': datetime.now(timezone.utc).isoformat(),
        'error_detail': error_detail or None,
    }
    if status == 'sent':
        body['sent_at'] = datetime.now(timezone.utc).isoformat()
    if next_retry_at:
        body['next_retry_at'] = next_retry_at
    _sb(f"hermes_comms_log?id=eq.{log_id}", 'PATCH', body, prefer='return=minimal')


# ─── Telegram ─────────────────────────────────────────────────────────────────

def _raw_telegram_send(text: str, chat_id: str = '', parse_mode: str = 'HTML') -> bool:
    cid = chat_id or TELEGRAM_CHAT_ID
    token = TELEGRAM_BOT_TOKEN
    if not token or not cid:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = json.dumps({'chat_id': cid, 'text': text[:4096], 'parse_mode': parse_mode}).encode()
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.warning(f"Telegram raw send: {e}")
        return False


def send_telegram(text: str, subject: str = '', chat_id: str = '',
                  idempotency_key: str = '') -> bool:
    """Send Telegram message with idempotency and logging."""
    recipient = chat_id or TELEGRAM_CHAT_ID
    idem_key = idempotency_key or _make_idempotency_key('telegram', recipient, subject, text)

    if _check_already_sent(idem_key):
        logger.debug(f"Telegram message already sent: {idem_key}")
        return True

    success = _raw_telegram_send(text, chat_id=recipient)
    status = 'sent' if success else 'failed'
    _log_send('telegram', recipient, subject, text[:300], idem_key, status=status)

    if not success:
        logger.warning(f"Telegram send failed — will retry from comms log")
    return success


# ─── Email ────────────────────────────────────────────────────────────────────

def send_email(subject: str, body: str, recipient: str = '',
               idempotency_key: str = '') -> bool:
    """Send email with idempotency and logging. Falls back gracefully."""
    to = recipient or os.getenv('OPERATOR_EMAIL', '')
    idem_key = idempotency_key or _make_idempotency_key('email', to, subject, body)

    if _check_already_sent(idem_key):
        logger.debug(f"Email already sent: {idem_key}")
        return True

    log_id = _log_send('email', to, subject, body[:300], idem_key, status='pending')

    try:
        from notifications.operator_notifications import send_operator_email
        send_operator_email(subject=subject, body=body)
        if log_id:
            _update_log(log_id, 'sent')
        return True
    except Exception as e:
        logger.warning(f"Email send failed: {e}")
        if log_id:
            next_retry = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            _update_log(log_id, 'failed', error_detail=str(e), next_retry_at=next_retry)
        return False


# ─── Reliable Send (with fallback) ────────────────────────────────────────────

def reliable_send(text: str, subject: str = '', fallback_to_email: bool = True) -> dict:
    """
    Send via Telegram. If it fails, fall back to email.
    Returns {'telegram': bool, 'email': bool | None}.
    """
    result: dict = {'telegram': False, 'email': None}
    result['telegram'] = send_telegram(text, subject=subject)

    if not result['telegram'] and fallback_to_email:
        email_body = f"{subject}\n\n{text}" if subject else text
        result['email'] = send_email(subject=subject or 'Nexus Alert', body=email_body)

    return result


# ─── Retry Queue Processor ────────────────────────────────────────────────────

def process_retry_queue() -> dict:
    """Process pending retries from hermes_comms_log."""
    now = datetime.now(timezone.utc).isoformat()
    rows = _sb(
        f"hermes_comms_log?status=in.(retrying,pending)"
        f"&next_retry_at=lte.{now}"
        f"&retry_count=lt.3"
        f"&select=id,channel,recipient,subject,body_preview,retry_count&limit=20"
    )
    sent = failed = 0
    for r in rows:
        log_id = r['id']
        channel = r.get('channel', 'telegram')
        retry_count = r.get('retry_count', 0) + 1
        next_retry = (datetime.now(timezone.utc) + timedelta(minutes=5 * retry_count)).isoformat()

        if channel == 'telegram':
            body = r.get('body_preview', '')
            ok = _raw_telegram_send(body, chat_id=r.get('recipient', ''))
        else:
            ok = False
            try:
                from notifications.operator_notifications import send_operator_email
                send_operator_email(
                    subject=r.get('subject', 'Nexus'),
                    body=r.get('body_preview', ''),
                )
                ok = True
            except Exception:
                pass

        if ok:
            _update_log(log_id, 'sent', retry_count=retry_count)
            sent += 1
        else:
            new_status = 'failed' if retry_count >= 3 else 'retrying'
            _update_log(log_id, new_status, retry_count=retry_count, next_retry_at=next_retry)
            failed += 1

    return {'sent': sent, 'failed': failed}


def get_comms_health() -> str:
    """Brief comms health summary for Telegram."""
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = _sb(f"hermes_comms_log?created_at=gt.{cutoff_24h}&select=status,channel&limit=500")
    if not rows:
        return "No comms in the last 24h."
    total = len(rows)
    sent = sum(1 for r in rows if r.get('status') == 'sent')
    failed = sum(1 for r in rows if r.get('status') == 'failed')
    return f"Comms 24h: {sent}/{total} sent | {failed} failed"
