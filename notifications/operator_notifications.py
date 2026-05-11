#!/usr/bin/env python3
"""Lightweight operator notifications for email + brief bot alerts."""

from __future__ import annotations

import os
import smtplib
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


def can_send_email() -> bool:
    return bool(email_enabled() and email_sender() and email_password() and email_recipient())


def send_operator_email(subject: str, body: str) -> tuple[bool, str]:
    """Send an operator email if fully configured."""
    if not can_send_email():
        return False, "email notifications not configured"

    msg = MIMEText(body)
    msg["From"] = email_sender()
    msg["To"] = email_recipient()
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            smtp.login(email_sender(), email_password())
            smtp.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)
