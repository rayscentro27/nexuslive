from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"

FILE_MAP = {
    "signals": "nexus_trading_signals",
    "trades": "nexus_paper_trades",
    "strategy_scores": "nexus_strategy_scores",
    "reports": "nexus_trading_reports",
    "market_scan": "nexus_market_scan_results",
}


def today_stamp() -> str:
    return datetime.now().strftime("%Y%m%d")


def jsonl_path(kind: str, *, date_stamp: str | None = None) -> Path:
    prefix = FILE_MAP[kind]
    return LOG_DIR / f"{prefix}_{date_stamp or today_stamp()}.jsonl"


def append_jsonl(kind: str, payload: Any, *, date_stamp: str | None = None) -> Path:
    path = jsonl_path(kind, date_stamp=date_stamp)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")
    return path


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            continue
    if limit is not None:
        return rows[-limit:]
    return rows


def latest_jsonl(kind: str, *, limit: int | None = None) -> list[dict[str, Any]]:
    return read_jsonl(jsonl_path(kind), limit=limit)
