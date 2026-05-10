#!/usr/bin/env python3
from __future__ import annotations

import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_email_knowledge_intake import parse_knowledge_email, parse_gmail_hydrated_message


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8").rstrip("=")


def main() -> int:
    ok = True

    p1 = parse_knowledge_email(
        'Ray Centro <rayscentro@yahoo.com>',
        'Funding Research',
        'CATEGORY: Funding\nHere is a link https://example.com/a and https://youtu.be/abc123',
        message_id='msg-1',
    )
    ok &= check('sender email parsed', p1.sender_email == 'rayscentro@yahoo.com')
    ok &= check('subject parsed', p1.subject == 'Funding Research')
    ok &= check('links extracted', len(p1.urls) >= 2)
    ok &= check('youtube detected', any('youtu.be/' in u for u in p1.youtube_links))
    ok &= check('category explicit parsed', p1.requested_category == 'funding')

    html = '<html><body><a href="https://www.youtube.com/watch?v=xyz">video</a><p>Credit setup steps.</p></body></html>'
    p2 = parse_knowledge_email('tester@example.com', 'Credit Research', html, message_id='msg-2')
    ok &= check('html anchor extracted', any('youtube.com/watch' in u for u in p2.urls))
    ok &= check('html stripped body fallback', 'Credit setup steps.' in p2.notes)

    gmail_message = {
        'id': 'gm-1',
        'snippet': 'snippet fallback',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'Ray Centro <rayscentro@yahoo.com>'},
                {'name': 'Subject', 'value': 'Marketing Research'},
                {'name': 'Message-Id', 'value': '<abc@nexus>'},
            ],
            'parts': [
                {'mimeType': 'text/plain', 'body': {'data': _b64('CATEGORY: Marketing\nhttps://example.org/landing')}},
                {'mimeType': 'text/html', 'body': {'data': _b64('<a href="https://youtu.be/zzz">vid</a>')}},
            ],
        },
    }
    p3 = parse_gmail_hydrated_message(gmail_message)
    ok &= check('gmail sender parsed', p3.sender_email == 'rayscentro@yahoo.com')
    ok &= check('gmail message id parsed', p3.email_message_id == '<abc@nexus>')
    ok &= check('gmail links extracted', len(p3.urls) >= 2)
    ok &= check('gmail category detected', p3.requested_category == 'marketing')

    ok &= check('no secret leakage in notes', 'NEXUS_EMAIL_PASSWORD' not in p3.notes)
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
