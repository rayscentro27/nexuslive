#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_safety_gate import evaluate_trading_safety


def main() -> int:
    status = evaluate_trading_safety()
    status_file = ROOT / "logs" / "trading_engine_status.json"
    payload = {
        "safety_gate": status,
        "status_file_exists": status_file.exists(),
        "status_file": str(status_file),
    }
    print(json.dumps(payload, indent=2))
    return 0 if status["safe"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
