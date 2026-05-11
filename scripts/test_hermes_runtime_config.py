#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_runtime_config import default_runtime_config, get_telegram_mode, format_telegram_reply


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    d = default_runtime_config()
    ok &= check("default config has personality", "hermes_personality" in d)
    os.environ["HERMES_TELEGRAM_MODE"] = "travel_mode"
    ok &= check("telegram mode resolves", get_telegram_mode() in {"travel_mode", "workstation_mode", "executive_mode", "incident_mode"})
    short = format_telegram_reply("x" * 2000)
    ok &= check("travel mode truncates", len(short) <= 700)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
