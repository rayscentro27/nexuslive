"""
Nexus allowlist guard — the single HARD gate for any external send during
continuous operations. Email + Instagram DM are restricted to Ray-owned/test
identities ONLY. Everything is logged. Nothing public, no cold third-party
outreach, no payments, no live trading.

Flags (defaults here; .env may override but allowlists are enforced regardless):
  EMAIL_TEST_MODE=true · EMAIL_SEND_TO_UNLISTED=false
  IG_DM_TEST_MODE=true  · IG_SEND_TO_UNLISTED=false
  COLD_OUTREACH_TEST_MODE=true · COLD_OUTREACH_EXTERNAL_ENABLED=false
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "proof_automation" / "send_log.json"

# HARD allowlists — enforced in code regardless of env.
EMAIL_ALLOWED = {"rayscentro@yahoo.com", "goclearonline@gmail.com"}
IG_ALLOWED = {"raydavis7677"}

SMTP_HOST, SMTP_PORT = "smtp.gmail.com", 587


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(entry: dict) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    data = {"updated_at": _now(), "events": []}
    if LOG.exists():
        try:
            data = json.loads(LOG.read_text())
        except Exception:
            pass
    entry["at"] = _now()
    data["events"] = (data.get("events", []) + [entry])[-500:]
    data["updated_at"] = _now()
    LOG.write_text(json.dumps(data, indent=2))


def email_allowed(addr: str) -> bool:
    return (addr or "").strip().lower() in EMAIL_ALLOWED


def ig_allowed(handle: str) -> bool:
    return (handle or "").strip().lstrip("@").lower() in IG_ALLOWED


def send_allowlisted_email(to: str, subject: str, body: str, template: str = "",
                           project: str = "", actually_send: bool = True) -> dict:
    """Send a TEST email ONLY to an allowlisted Ray address. Hard-blocks anything else."""
    to_norm = (to or "").strip().lower()
    if not email_allowed(to_norm):
        ev = {"channel": "email", "status": "blocked", "reason": "recipient not allowlisted",
              "recipient": to_norm, "template": template, "project": project}
        _log(ev)
        return ev
    subject = f"[NEXUS TEST] {subject}"
    body = body + "\n\n--\nThis is a Nexus TEST-MODE email sent only to Ray's allowlisted address. " \
                  "Educational test; no guarantees; nothing published. No third-party recipients."
    sender = os.getenv("NEXUS_EMAIL", "").strip()
    pw = os.getenv("NEXUS_EMAIL_PASSWORD", "").strip()
    if not actually_send:
        ev = {"channel": "email", "status": "drafted", "recipient": to_norm, "subject": subject,
              "template": template, "project": project}
        _log(ev); return ev
    if not sender or not pw:
        ev = {"channel": "email", "status": "blocked", "reason": "SMTP not configured (NEXUS_EMAIL/PASSWORD)",
              "recipient": to_norm, "template": template, "project": project}
        _log(ev); return ev
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_norm
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(sender, pw)
            s.sendmail(sender, [to_norm], msg.as_string())
        ev = {"channel": "email", "status": "sent", "recipient": to_norm, "subject": subject,
              "template": template, "project": project, "transport": "gmail_smtp"}
    except Exception as e:
        ev = {"channel": "email", "status": "failed", "reason": str(e)[:120], "recipient": to_norm,
              "template": template, "project": project}
    _log(ev)
    return ev


def queue_or_send_ig_dm(handle: str, message: str) -> dict:
    """IG DM is queue/draft-only by default. Real send requires Meta permissions +
    an inbound message within the 24h window — not available here, so we QUEUE and report."""
    h = (handle or "").lstrip("@").lower()
    if not ig_allowed(h):
        ev = {"channel": "instagram", "status": "blocked", "reason": "handle not allowlisted", "handle": h}
        _log(ev); return ev
    # Meta IG messaging requires a Page-linked IG business account + recipient-initiated
    # conversation (24h window). We cannot initiate an outbound DM safely → queue only.
    ev = {"channel": "instagram", "status": "queued",
          "reason": "outbound-initiated IG DM not permitted by Meta without an inbound message in the 24h window; draft queued for manual send",
          "handle": h, "message": message,
          "queue_path": "logs/proof_automation/ig_dm_queue.json"}
    q = ROOT / "logs" / "proof_automation" / "ig_dm_queue.json"
    q.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if q.exists():
        try:
            items = json.loads(q.read_text())
        except Exception:
            items = []
    items.append({"handle": h, "message": message, "status": "queued", "at": _now()})
    q.write_text(json.dumps(items, indent=2))
    _log(ev)
    return ev


def send_log() -> list[dict]:
    if LOG.exists():
        try:
            return json.loads(LOG.read_text()).get("events", [])
        except Exception:
            return []
    return []
