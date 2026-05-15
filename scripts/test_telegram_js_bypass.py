#!/usr/bin/env python3
"""Fail if tracked JS files use raw Telegram sendMessage without policy guard."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def _tracked_files() -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "*.js", "*.mjs", "*.cjs"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return [ROOT / line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return list(ROOT.rglob("*.js"))


def main() -> int:
    violations: list[str] = []
    endpoint_re = re.compile(r"api\.telegram\.org/.+?/sendMessage")
    guard_markers = (
        "shouldSendTelegramNotification",
        "shouldSendTelegram(",
        "telegram_policy denied=true",
        "TELEGRAM_AUTO_REPORTS_ENABLED",
    )
    for path in _tracked_files():
        rel = str(path.relative_to(ROOT))
        if rel.startswith("tests/") or rel.startswith("scripts/test_"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        raw_send = "sendMessage" in text and bool(endpoint_re.search(text))
        guarded = any(m in text for m in guard_markers)
        if raw_send and not guarded:
            violations.append(rel)

    if violations:
        print("[FAIL] JS Telegram bypass paths found:")
        for rel in violations[:50]:
            print(f" - {rel}")
        return 1

    print("[PASS] No JS raw Telegram bypass paths detected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
