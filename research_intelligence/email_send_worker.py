"""
Queued email sender for experiment variants.

Consumes `email_send_queue` rows in `queued` status, sends via the existing
operator SMTP helper when configured, and logs `email_send_events`.

By default this supports a dry-run mode so the queue path can be exercised
without actually sending mail.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

from notifications.operator_notifications import (
    SMTP_HOST,
    SMTP_PORT,
    email_password,
    email_recipient,
    email_sender,
)
import smtplib

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


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


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _queued_rows(limit: int) -> List[dict]:
    return _sb_get(
        "email_send_queue"
        "?select=id,campaign_id,variant_id,send_channel,queue_status,scheduled_for,approval_note,metadata,created_at"
        "&queue_status=eq.queued"
        "&order=created_at.asc"
        f"&limit={limit}"
    )


def _variant(variant_id: str) -> Optional[dict]:
    rows = _sb_get(
        "email_variants"
        "?select=id,campaign_id,variant_label,hook_type,subject_line,preview_text,body_markdown,cta,status,metadata"
        f"&id=eq.{_quote(variant_id)}&limit=1"
    )
    return rows[0] if rows else None


def _campaign(campaign_id: str) -> Optional[dict]:
    rows = _sb_get(
        "email_campaigns"
        "?select=id,campaign_name,topic,audience,send_channel,send_status,metadata"
        f"&id=eq.{_quote(campaign_id)}&limit=1"
    )
    return rows[0] if rows else None


def _event_row(campaign_id: str, variant_id: str, event_type: str, metadata: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": _deterministic_uuid(f"email-send-event:{campaign_id}:{variant_id}:{event_type}:{now}"),
        "campaign_id": campaign_id,
        "variant_id": variant_id,
        "recipient_email": os.getenv("SCHEDULER_EMAIL_TO", os.getenv("NEXUS_EMAIL", "")).strip() or None,
        "event_type": event_type,
        "event_at": now,
        "metadata": metadata,
    }


def _render_body(campaign: dict, variant: dict) -> str:
    reply_marker = f"NX-EMAIL {campaign.get('id')} {variant.get('id')}"
    pieces = [
        f"Campaign: {campaign.get('campaign_name')}",
        f"Variant: {variant.get('variant_label')}",
        "",
        variant.get("preview_text") or "",
        "",
        variant.get("body_markdown") or "",
        "",
        variant.get("cta") or "",
        "",
        f"Reference: {reply_marker}",
    ]
    return "\n".join(piece for piece in pieces if piece is not None).strip()


def send_experiment_email(subject: str, body: str, campaign_id: str, variant_id: str) -> tuple[bool, str]:
    if not email_sender() or not email_password() or not email_recipient():
        return False, "email notifications not configured"

    msg = MIMEText(body)
    msg["From"] = email_sender()
    msg["To"] = email_recipient()
    msg["Subject"] = subject
    msg["X-Nexus-Campaign-Id"] = campaign_id
    msg["X-Nexus-Variant-Id"] = variant_id

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(email_sender(), email_password())
            smtp.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)


def send_once(limit: int = 10, dry_run: bool = True) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    rows = _queued_rows(limit)
    processed: List[dict] = []

    for row in rows:
        queue_id = str(row["id"])
        campaign_id = str(row["campaign_id"])
        variant_id = str(row["variant_id"])
        campaign = _campaign(campaign_id)
        variant = _variant(variant_id)
        if not campaign or not variant:
            _sb_patch("email_send_queue", f"id=eq.{_quote(queue_id)}", {"queue_status": "failed", "updated_at": datetime.now(timezone.utc).isoformat()})
            continue

        subject = variant.get("subject_line") or campaign.get("campaign_name") or "Email Experiment"
        body = _render_body(campaign, variant)
        metadata = {
            "queue_id": queue_id,
            "campaign_name": campaign.get("campaign_name"),
            "variant_label": variant.get("variant_label"),
            "dry_run": dry_run,
            "subject_line": subject,
            "reply_marker": f"NX-EMAIL {campaign_id} {variant_id}",
        }

        if dry_run:
            success, detail = True, "dry_run"
        else:
            success, detail = send_experiment_email(subject, body, campaign_id, variant_id)
            metadata["provider_detail"] = detail

        event_type = "sent" if success else "bounced"
        _sb_post("email_send_events", [_event_row(campaign_id, variant_id, event_type, metadata)], prefer="return=minimal")

        now = datetime.now(timezone.utc).isoformat()
        if success:
            _sb_patch("email_send_queue", f"id=eq.{_quote(queue_id)}", {"queue_status": "sent", "sent_at": now, "updated_at": now})
            _sb_patch("email_variants", f"id=eq.{_quote(variant_id)}", {"status": "sent", "updated_at": now})
            _sb_patch("email_campaigns", f"id=eq.{_quote(campaign_id)}", {"send_status": "sent", "updated_at": now})
        else:
            _sb_patch("email_send_queue", f"id=eq.{_quote(queue_id)}", {"queue_status": "failed", "updated_at": now})

        processed.append(
            {
                "queue_id": queue_id,
                "campaign_id": campaign_id,
                "variant_id": variant_id,
                "subject_line": subject,
                "success": success,
                "detail": detail,
                "dry_run": dry_run,
            }
        )

    return {
        "queued_seen": len(rows),
        "processed": processed,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(send_once(limit=args.limit, dry_run=args.dry_run), indent=2))
