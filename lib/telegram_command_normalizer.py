"""
Telegram command normalizer — standalone, dependency-free.

This is the inbound-message normalizer used by TheChoseone's live command
handler. It is extracted here as a small, importable module for the
self-contained War Room foundation branch (the full `telegram_bot.py` on the
feature branch carries a large platform import tree and a different lineage from
`main`, so only this pure function is ported).

Behaviour is identical to the verified fix: an em/en dash menu suffix is stripped
ONLY when it is a real separator (a space precedes the dash AND the text after it
is not a price/number), so price ranges like "$97–$297" are preserved while
copied menu items ("status — description") are still cleaned.
"""
from __future__ import annotations


def _normalize_telegram_command(text: str) -> str:
    # Strip smart quotes, bullets, em/en dashes + menu suffixes.
    # Ensures copied menu items route same as typed commands.
    t = (text or "").strip()
    # 1. Strip leading bullet/dash/star
    LEAD_STRIP = set([
        "•", "‣", "◦", "–", "—", "-", "*"
    ])
    while t and t[0] in LEAD_STRIP:
        t = t[1:].strip()
    # 2. Strip em/en dash menu suffix ONLY when it is a real separator:
    #    a space immediately precedes the dash AND the text after it is not a
    #    price/number. This cleans copied menu items ("status — description")
    #    while preserving price ranges like "$97–$297" (and "$97 – $297").
    for dash in ["—", "–"]:
        idx = t.find(dash)
        if idx > 0 and t[idx - 1] == " ":
            after = t[idx + 1:].lstrip()
            if after[:1] != "$" and not after[:1].isdigit():
                t = t[:idx].strip()
    # 3. Strip surrounding quote chars (ASCII and Unicode)
    QUOTES = set([chr(0x27), chr(0x22), chr(0x2018), chr(0x2019), chr(0x201c), chr(0x201d), chr(0xab), chr(0xbb)])
    while t and t[0] in QUOTES:
        t = t[1:]
    while t and t[-1] in QUOTES:
        t = t[:-1]
    # 4. Collapse whitespace
    return " ".join(t.split())
