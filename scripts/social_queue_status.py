#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import social_queue  # noqa: E402


def main() -> int:
    paths = social_queue.write_status_reports()
    summary = social_queue.summarize()
    print(json.dumps({"paths": paths, **summary}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
