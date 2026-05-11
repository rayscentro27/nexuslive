#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from notifications.operator_notifications import send_operator_email, can_send_email


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    old = {k: os.environ.get(k) for k in ["SCHEDULER_EMAIL_ENABLED", "NEXUS_EMAIL", "NEXUS_EMAIL_PASSWORD", "SCHEDULER_EMAIL_TO"]}
    os.environ["SCHEDULER_EMAIL_ENABLED"] = "false"
    os.environ["NEXUS_EMAIL"] = ""
    os.environ["NEXUS_EMAIL_PASSWORD"] = ""
    os.environ["SCHEDULER_EMAIL_TO"] = ""
    ok &= check("email can_send false when unconfigured", can_send_email() is False)
    sent, detail = send_operator_email("Test", "Body")
    ok &= check("send_operator_email fails safely", sent is False and "not configured" in detail.lower())
    for k, v in old.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
