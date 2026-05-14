#!/usr/bin/env python3
"""Operator notifications — HTML email via Resend (primary) or Gmail SMTP (fallback)."""

from __future__ import annotations

import json
import os
import smtplib
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def email_enabled() -> bool:
    return os.getenv("SCHEDULER_EMAIL_ENABLED", "false").lower() == "true"


def email_sender() -> str:
    return os.getenv("NEXUS_EMAIL", "").strip()


def email_password() -> str:
    return os.getenv("NEXUS_EMAIL_PASSWORD", "").strip()


def email_recipient() -> str:
    return os.getenv("SCHEDULER_EMAIL_TO", email_sender()).strip()


def resend_key() -> str:
    return os.getenv("RESEND_API_KEY", "").strip()


def resend_from() -> str:
    return os.getenv("RESEND_FROM_EMAIL", "Nexus <onboarding@goclearonline.cc>").strip()


def can_send_email() -> bool:
    smtp_ok = bool(email_enabled() and email_sender() and email_password() and email_recipient())
    resend_ok = bool(resend_key() and email_recipient())
    return smtp_ok or resend_ok


def _send_via_resend(subject: str, body: str, html_body: str | None = None) -> tuple[bool, str]:
    """Send via Resend API (HTML if provided, plain text otherwise)."""
    key = resend_key()
    to = email_recipient()
    if not key or not to:
        return False, "resend not configured"

    payload: dict = {
        "from": resend_from(),
        "to": [to],
        "subject": subject,
    }
    if html_body:
        payload["html"] = html_body
    else:
        payload["text"] = body

    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
            return True, f"resend:{resp.get('id', 'sent')}"
    except urllib.error.HTTPError as e:
        return False, f"resend_http_{e.code}"
    except Exception as exc:
        return False, f"resend_error:{exc}"


def _send_via_smtp(subject: str, body: str, html_body: str | None = None) -> tuple[bool, str]:
    """Send via Gmail SMTP."""
    sender = email_sender()
    password = email_password()
    to = email_recipient()
    if not (email_enabled() and sender and password and to):
        return False, "smtp not configured"

    if html_body:
        msg: MIMEMultipart | MIMEText = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEText(body)
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(sender, password)
            smtp.send_message(msg)
        return True, "smtp:sent"
    except Exception as exc:
        return False, f"smtp_error:{exc}"


def send_operator_email(
    subject: str,
    body: str,
    html_body: str | None = None,
) -> tuple[bool, str]:
    """Send operator email. Tries Resend first (HTML-capable), falls back to Gmail SMTP."""
    if not can_send_email():
        return False, "email not configured"

    # Try Resend first (supports HTML)
    if resend_key():
        ok, detail = _send_via_resend(subject, body, html_body)
        if ok:
            return True, detail

    # Fall back to Gmail SMTP
    return _send_via_smtp(subject, body, html_body)
