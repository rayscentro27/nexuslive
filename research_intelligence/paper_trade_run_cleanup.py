"""
Paper trade run cleanup.

Marks obvious duplicate running `paper_trade_runs` rows as `error` so one
canonical run remains per proposal/strategy/symbol combination.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def cleanup_once(limit: int = 100) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    rows = _sb_get(
        "paper_trade_runs"
        "?select=id,proposal_id,signal_id,symbol,strategy_id,status,started_at,trace_id"
        "&status=eq.running"
        "&order=started_at.asc"
        f"&limit={limit}"
    )
    grouped: Dict[str, List[dict]] = {}
    for row in rows:
        key = "|".join(
            [
                str(row.get("proposal_id") or ""),
                str(row.get("signal_id") or ""),
                str(row.get("symbol") or ""),
                str(row.get("strategy_id") or ""),
            ]
        )
        grouped.setdefault(key, []).append(row)

    marked: List[str] = []
    for run_rows in grouped.values():
        if len(run_rows) <= 1:
            continue
        keeper = run_rows[0]["id"]
        for row in run_rows[1:]:
            _sb_patch(
                "paper_trade_runs",
                f"id=eq.{_quote(row['id'])}",
                {
                    "status": "error",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            marked.append(row["id"])
    return {
        "running_considered": len(rows),
        "duplicate_runs_marked_error": marked,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(cleanup_once(limit=args.limit), indent=2))
