"""
Email approval and queue worker.

Turns draft `email_variants` into explicitly approved/queued send records without
actually sending email.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

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
        return json.loads(response.read())


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


def _variant(variant_id: str) -> Optional[dict]:
    rows = _sb_get(
        "email_variants"
        "?select=id,campaign_id,variant_label,hook_type,subject_line,preview_text,body_markdown,cta,status,metadata,created_at"
        f"&id=eq.{_quote(variant_id)}&limit=1"
    )
    return rows[0] if rows else None


def _campaign(campaign_id: str) -> Optional[dict]:
    rows = _sb_get(
        "email_campaigns"
        "?select=id,experiment_id,campaign_name,topic,audience,send_channel,send_status,subject_line,preview_text,cta,metadata,created_at"
        f"&id=eq.{_quote(campaign_id)}&limit=1"
    )
    return rows[0] if rows else None


def _queue_row(campaign: dict, variant: dict, queue_status: str, send_channel: str, scheduled_for: Optional[str], approval_note: str) -> dict:
    queue_id = _deterministic_uuid(f"email-send-queue:{campaign['id']}:{variant['id']}")
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": queue_id,
        "campaign_id": campaign["id"],
        "variant_id": variant["id"],
        "send_channel": send_channel,
        "queue_status": queue_status,
        "scheduled_for": scheduled_for,
        "approved_at": now if queue_status in {"approved", "queued", "sent"} else None,
        "sent_at": now if queue_status == "sent" else None,
        "approval_note": approval_note or None,
        "metadata": {
            "campaign_name": campaign.get("campaign_name"),
            "variant_label": variant.get("variant_label"),
            "hook_type": variant.get("hook_type"),
            "subject_line": variant.get("subject_line"),
        },
        "updated_at": now,
    }


def set_variant_queue_status(
    variant_id: str,
    queue_status: str = "approved",
    send_channel: str = "manual_review",
    scheduled_for: Optional[str] = None,
    approval_note: str = "",
) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    variant = _variant(variant_id)
    if not variant:
        raise RuntimeError(f"Variant {variant_id} not found")
    campaign = _campaign(str(variant.get("campaign_id")))
    if not campaign:
        raise RuntimeError(f"Campaign {variant.get('campaign_id')} not found")

    row = _queue_row(campaign, variant, queue_status, send_channel, scheduled_for, approval_note)
    _sb_post("email_send_queue", [row], prefer="resolution=merge-duplicates,return=representation")

    variant_status = "approved" if queue_status == "approved" else queue_status
    campaign_status = "approved" if queue_status == "approved" else queue_status
    now = datetime.now(timezone.utc).isoformat()
    _sb_patch("email_variants", f"id=eq.{_quote(variant_id)}", {"status": variant_status, "updated_at": now})
    _sb_patch("email_campaigns", f"id=eq.{_quote(campaign['id'])}", {"send_status": campaign_status, "updated_at": now})

    return {
        "queue_id": row["id"],
        "campaign_id": campaign["id"],
        "variant_id": variant["id"],
        "queue_status": queue_status,
        "campaign_name": campaign.get("campaign_name"),
        "subject_line": variant.get("subject_line"),
    }


def list_review_candidates(limit: int = 10) -> List[dict]:
    return _sb_get(
        "email_variants"
        "?select=id,campaign_id,variant_label,hook_type,subject_line,preview_text,status,metadata,created_at"
        "&status=in.(draft,approved,queued)"
        "&order=created_at.desc"
        f"&limit={limit}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--limit", type=int, default=10)

    approve_parser = sub.add_parser("approve")
    approve_parser.add_argument("variant_id")
    approve_parser.add_argument("--note", default="")
    approve_parser.add_argument("--channel", default="manual_review")

    queue_parser = sub.add_parser("queue")
    queue_parser.add_argument("variant_id")
    queue_parser.add_argument("--note", default="")
    queue_parser.add_argument("--channel", default="manual_review")
    queue_parser.add_argument("--scheduled-for", default=None)

    args = parser.parse_args()

    if args.command == "list":
        print(json.dumps(list_review_candidates(limit=args.limit), indent=2))
    elif args.command == "approve":
        print(json.dumps(set_variant_queue_status(args.variant_id, "approved", args.channel, None, args.note), indent=2))
    elif args.command == "queue":
        print(json.dumps(set_variant_queue_status(args.variant_id, "queued", args.channel, args.scheduled_for, args.note), indent=2))
