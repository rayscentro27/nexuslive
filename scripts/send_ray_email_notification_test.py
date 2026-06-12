#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from notifications.operator_notifications import can_send_email, send_operator_email  # noqa: E402

OUT_JSON = ROOT / "logs" / "ray_email_notification_test_latest.json"
OUT_MD = ROOT / "logs" / "ray_email_notification_test_latest.md"
RAY_EMAIL = "rayscentro@yahoo.com"


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--send", action="store_true")
    parser.add_argument("--recipient", default=RAY_EMAIL)
    args = parser.parse_args()

    load_env()
    if args.recipient.strip().lower() != RAY_EMAIL:
        print("Refused: recipient must be Ray only.")
        return 2

    showroom = ROOT / "reports" / "showroom" / "latest_results_showroom.md"
    subject = "Nexus Ray-only showroom/email path test"
    body = (
        "This is a Ray-only Nexus notification path test.\n\n"
        f"Showroom: {showroom}\n"
        "No public publish, no outreach, no client email.\n"
    )

    os.environ["SCHEDULER_EMAIL_TO"] = RAY_EMAIL
    status = "dry_run"
    detail = "not sent"
    if args.send and can_send_email() and not args.dry_run:
        ok, detail = send_operator_email(subject, body)
        status = "sent" if ok else "failed"
    elif args.send and not can_send_email():
        status = "blocked"
        detail = "email not configured"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recipient_is_ray_only": True,
        "email_configured": can_send_email(),
        "subject": subject,
        "status": status,
        "detail": detail,
        "showroom_path": str(showroom.relative_to(ROOT)),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2))
    OUT_MD.write_text(
        "# Ray Email Notification Test\n\n"
        f"- recipient: {RAY_EMAIL}\n"
        f"- email configured: {'yes' if payload['email_configured'] else 'no'}\n"
        f"- subject: {subject}\n"
        f"- status: {status}\n"
        f"- detail: {detail}\n"
        f"- showroom path: `{payload['showroom_path']}`\n"
    )
    print(OUT_MD.relative_to(ROOT))
    return 0 if status in {"dry_run", "sent"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
