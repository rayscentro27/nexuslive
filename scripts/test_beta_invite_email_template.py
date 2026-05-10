#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts.prelaunch_utils import build_tester_email


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    out = build_tester_email(
        name='Ray',
        login_link='https://nexus.goclearonline.com/signup?token=abc',
        membership_level='admin_test',
        note='beta cohort one',
    )
    subject = out.get('subject') or ''
    body = out.get('body') or ''
    ok &= check('subject correct', subject == 'You’ve Been Invited to Join Nexus Beta')
    ok &= check('signup link present', 'https://nexus.goclearonline.com/signup?token=abc' in body)
    ok &= check('mobile wording present', 'MOBILE ACCESS' in body)
    ok &= check('waived beta language present', 'waived subscription' in body.lower())
    ok &= check('disclaimer present', 'IMPORTANT DISCLAIMER' in body and 'not financial advisors' in body)
    ok &= check('no secret exposure', 'NEXUS_EMAIL_PASSWORD' not in body and 'OPENROUTER_API_KEY' not in body)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
