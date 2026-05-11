"""
Sync Gmail inbox replies into email_send_events.

Uses the existing Gmail IMAP credentials already configured for Nexus.
Reply matching prefers the outbound reference marker added by the sender, then
falls back to recipient + normalized subject matching for older sends.
"""

from __future__ import annotations

import email
import imaplib
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
NEXUS_EMAIL = os.getenv("NEXUS_EMAIL", "").strip()
NEXUS_EMAIL_PASSWORD = os.getenv("NEXUS_EMAIL_PASSWORD", "").strip()
IMAP_HOST = "imap.gmail.com"

REFERENCE_RE = re.compile(
    r"NX-EMAIL\s+([0-9a-fA-F-]{36})\s+([0-9a-fA-F-]{36})",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"<([^>]+)>")


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_post(table: str, rows: List[dict], prefer: str = "return=representation") -> List[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(prefer),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = response.read()
        if not payload:
            return []
        return json.loads(payload)


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _decode_header_value(value: str) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload is not None:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    payload = msg.get_payload(decode=True)
    if payload is None:
        return ""
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def _normalize_subject(subject: str) -> str:
    text = (subject or "").strip().lower()
    text = re.sub(r"^\s*((re|fwd?):\s*)+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_email(sender: str) -> str:
    sender = _decode_header_value(sender or "")
    match = EMAIL_RE.search(sender)
    if match:
        return match.group(1).strip().lower()
    return sender.strip().lower()


def _search_replies(days: int, unread_only: bool) -> List[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    criteria = [f'SINCE "{cutoff}"']
    if unread_only:
        criteria.insert(0, "UNSEEN")

    messages: List[dict] = []
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(NEXUS_EMAIL, NEXUS_EMAIL_PASSWORD)
        imap.select("INBOX")
        status, ids = imap.search(None, *criteria)
        if status != "OK":
            return []

        for uid in ids[0].split():
            status, data = imap.fetch(uid, "(RFC822)")
            if status != "OK" or not data or data[0] is None:
                continue
            msg = email.message_from_bytes(data[0][1])
            sender_email = _extract_email(msg.get("From", ""))
            if not sender_email or sender_email == NEXUS_EMAIL.lower():
                continue

            subject = _decode_header_value(msg.get("Subject", ""))
            body = _extract_body(msg)
            messages.append(
                {
                    "uid": uid.decode() if isinstance(uid, bytes) else str(uid),
                    "message_id": _decode_header_value(msg.get("Message-ID", "")).strip(),
                    "from_email": sender_email,
                    "subject": subject,
                    "normalized_subject": _normalize_subject(subject),
                    "date": _decode_header_value(msg.get("Date", "")).strip(),
                    "body": body,
                }
            )

    return messages


def _sent_events(days: int = 30) -> List[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    return _sb_get(
        "email_send_events"
        "?select=id,campaign_id,variant_id,recipient_email,event_type,event_at,metadata"
        "&event_type=eq.sent"
        f"&event_at=gte.{_quote(cutoff)}"
        "&order=event_at.desc"
        "&limit=500"
    )


def _existing_reply_message_ids() -> set[str]:
    rows = _sb_get(
        "email_send_events"
        "?select=metadata"
        "&event_type=eq.replied"
        "&order=event_at.desc"
        "&limit=500"
    )
    seen = set()
    for row in rows:
        metadata = row.get("metadata") or {}
        message_id = str(metadata.get("gmail_message_id") or "").strip()
        if message_id:
            seen.add(message_id)
    return seen


def _reference_match(body: str, subject: str) -> Optional[Tuple[str, str]]:
    for text in (body or "", subject or ""):
        match = REFERENCE_RE.search(text)
        if match:
            return match.group(1), match.group(2)
    return None


def _match_reply(message: dict, sent_rows: List[dict]) -> Optional[dict]:
    explicit = _reference_match(message.get("body", ""), message.get("subject", ""))
    if explicit:
        campaign_id, variant_id = explicit
        for row in sent_rows:
            if str(row.get("campaign_id")) == campaign_id and str(row.get("variant_id")) == variant_id:
                return row

    sender = message.get("from_email", "")
    normalized_subject = message.get("normalized_subject", "")
    candidates = [row for row in sent_rows if str(row.get("recipient_email") or "").strip().lower() == sender]
    for row in candidates:
        metadata = row.get("metadata") or {}
        sent_subject = _normalize_subject(str(metadata.get("subject_line") or ""))
        if sent_subject and sent_subject == normalized_subject:
            return row
    return candidates[0] if len(candidates) == 1 else None


def _reply_event(sent_row: dict, message: dict) -> dict:
    campaign_id = str(sent_row["campaign_id"])
    variant_id = str(sent_row["variant_id"])
    message_id = message.get("message_id") or f"uid:{message.get('uid')}"
    return {
        "id": _deterministic_uuid(f"email-reply-event:{campaign_id}:{variant_id}:{message_id}"),
        "campaign_id": campaign_id,
        "variant_id": variant_id,
        "recipient_email": message.get("from_email"),
        "event_type": "replied",
        "event_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {
            "gmail_message_id": message.get("message_id"),
            "gmail_uid": message.get("uid"),
            "gmail_date": message.get("date"),
            "reply_subject": message.get("subject"),
            "matched_by": "reference_or_subject",
        },
    }


def sync_once(days: int = 14, unread_only: bool = False, dry_run: bool = True) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    if not NEXUS_EMAIL or not NEXUS_EMAIL_PASSWORD:
        raise RuntimeError("NEXUS_EMAIL and NEXUS_EMAIL_PASSWORD are required")

    messages = _search_replies(days=days, unread_only=unread_only)
    sent_rows = _sent_events(days=max(days, 30))
    seen_message_ids = _existing_reply_message_ids()
    matched = []
    inserted = []

    for message in messages:
        message_id = (message.get("message_id") or "").strip()
        if message_id and message_id in seen_message_ids:
            continue
        sent_row = _match_reply(message, sent_rows)
        if not sent_row:
            continue
        matched.append(
            {
                "from_email": message.get("from_email"),
                "subject": message.get("subject"),
                "campaign_id": sent_row.get("campaign_id"),
                "variant_id": sent_row.get("variant_id"),
            }
        )
        event_row = _reply_event(sent_row, message)
        if not dry_run:
            _sb_post("email_send_events", [event_row], prefer="return=minimal")
        inserted.append(event_row["id"])

    return {
        "messages_scanned": len(messages),
        "matches_found": len(matched),
        "matched": matched,
        "reply_events_written": inserted if not dry_run else [],
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--unread-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(sync_once(days=args.days, unread_only=args.unread_only, dry_run=args.dry_run), indent=2))
