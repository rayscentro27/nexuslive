#!/usr/bin/env python3
from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_email_knowledge_intake import parse_knowledge_email, ingest_email_to_transcript_queue


STATE_FILE = ROOT / ".email_pipeline_state.json"
IMAP_HOST = "imap.gmail.com"


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for raw in env.read_text().splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_processed_ids() -> set[str]:
    if not STATE_FILE.exists():
        return set()
    try:
        obj = json.loads(STATE_FILE.read_text())
        return set(obj.get("processed_message_ids") or [])
    except Exception:
        return set()


def save_processed_ids(ids: set[str]) -> None:
    STATE_FILE.write_text(json.dumps({"processed_message_ids": sorted(ids)[-500:]}, indent=2))


def extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", errors="replace") if payload else ""


def fetch_candidates(subject_filter: str = "") -> list[dict]:
    account = os.getenv("NEXUS_EMAIL", "goclearonline@gmail.com")
    password = os.getenv("NEXUS_EMAIL_PASSWORD", "")
    if not password:
        raise RuntimeError("NEXUS_EMAIL_PASSWORD missing")

    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(account, password)
        imap.select("INBOX")
        criteria = '(UNSEEN SUBJECT "youtube")'
        if subject_filter:
            criteria = f'(SINCE "01-May-2026" SUBJECT "{subject_filter}")'
        _, id_list = imap.search(None, criteria)
        uids = [u for u in id_list[0].split() if u]

        rows = []
        for uid in uids:
            _, data = imap.fetch(uid, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            rows.append(
                {
                    "uid": uid,
                    "message_id": (msg.get("Message-ID") or "").strip(),
                    "subject": msg.get("Subject", ""),
                    "sender": msg.get("From", ""),
                    "body": extract_body(msg),
                }
            )
        return rows


def mark_seen(uid: bytes) -> None:
    account = os.getenv("NEXUS_EMAIL", "goclearonline@gmail.com")
    password = os.getenv("NEXUS_EMAIL_PASSWORD", "")
    with imaplib.IMAP4_SSL(IMAP_HOST) as imap:
        imap.login(account, password)
        imap.select("INBOX")
        imap.store(uid, "+FLAGS", "\\Seen")


def should_process(subject: str) -> bool:
    s = (subject or "").lower()
    return any(k in s for k in ["youtube", "website", "strategy", "research email", "trading"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Process knowledge ingestion emails once")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no Supabase writes")
    parser.add_argument("--apply", action="store_true", help="Apply Supabase writes")
    parser.add_argument("--subject-filter", default="", help="Optional subject substring filter")
    args = parser.parse_args()

    load_env()
    apply = bool(args.apply) and not bool(args.dry_run)

    processed_ids = load_processed_ids()
    msgs = fetch_candidates(args.subject_filter)
    summary = {
        "mode": "apply" if apply else "dry-run",
        "candidates": len(msgs),
        "processed": 0,
        "skipped": 0,
        "marked_seen": 0,
        "transcript_rows_inserted": 0,
        "knowledge_rows_inserted": 0,
        "details": [],
    }

    for m in msgs:
        msg_id = m.get("message_id") or ""
        if msg_id and msg_id in processed_ids:
            summary["skipped"] += 1
            continue
        if args.subject_filter and args.subject_filter.lower() not in (m.get("subject", "").lower()):
            summary["skipped"] += 1
            continue
        if not should_process(m.get("subject", "")):
            summary["skipped"] += 1
            continue

        parsed = parse_knowledge_email(
            sender=m.get("sender", ""),
            subject=m.get("subject", ""),
            body=m.get("body", ""),
            message_id=msg_id,
        )
        result = ingest_email_to_transcript_queue(parsed, apply=apply)
        summary["details"].append(result)
        if result.get("ok"):
            summary["processed"] += 1
            summary["transcript_rows_inserted"] += int(result.get("transcript_rows_inserted") or 0)
            summary["knowledge_rows_inserted"] += int(result.get("knowledge_rows_inserted") or 0)
            if apply and ((result.get("transcript_rows_inserted") or 0) > 0 or (result.get("knowledge_rows_inserted") or 0) > 0):
                mark_seen(m["uid"])
                summary["marked_seen"] += 1
                if msg_id:
                    processed_ids.add(msg_id)
        else:
            summary["skipped"] += 1

    if apply:
        save_processed_ids(processed_ids)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
