#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib import request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_fallback_logger import latest_jsonl
from lib.trading_safety_gate import seed_safe_trading_env_from_launch_agent


TABLE_MAP = {
    "signals": "nexus_trading_signals",
    "trades": "nexus_paper_trades",
    "strategy_scores": "nexus_strategy_scores",
    "reports": "nexus_trading_reports",
}


def _headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Prefer": "return=minimal",
    }


def _ssl_context():
    cert_file = os.getenv("SSL_CERT_FILE", "")
    if not cert_file:
        try:
            import certifi
            cert_file = certifi.where()
        except Exception:
            cert_file = ""
    if cert_file:
        return ssl.create_default_context(cafile=cert_file)
    return None


def _record_key(kind: str, row: dict[str, Any]) -> str:
    if kind == "trades":
        return str(row.get("trade_id") or f"{row.get('created_at')}::{row.get('strategy_id')}::{row.get('symbol')}")
    if kind == "signals":
        return str(row.get("signal_id") or f"{row.get('created_at')}::{row.get('strategy_id')}::{row.get('symbol')}")
    if kind == "strategy_scores":
        return str(f"{row.get('created_at')}::{row.get('strategy_id')}::{row.get('rank')}")
    return str(f"{row.get('created_at')}::{row.get('report_type')}::{row.get('summary')}")


def _post_rows(table: str, rows: list[dict[str, Any]], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {"table": table, "prepared": len(rows), "inserted": 0, "dry_run": True}
    url = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")
    if not url:
        return {"table": table, "prepared": len(rows), "inserted": 0, "dry_run": False, "error": "SUPABASE_URL missing"}
    body = json.dumps(rows).encode()
    req = request.Request(f"{url}/rest/v1/{table}", data=body, method="POST", headers=_headers())
    with request.urlopen(req, timeout=20, context=_ssl_context()) as resp:
        resp.read()
    return {"table": table, "prepared": len(rows), "inserted": len(rows), "dry_run": False}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    seed_safe_trading_env_from_launch_agent()
    rows = {
        "signals": latest_jsonl("signals", limit=500),
        "trades": latest_jsonl("trades", limit=500),
        "strategy_scores": latest_jsonl("strategy_scores", limit=500),
        "reports": latest_jsonl("reports", limit=500),
    }
    prepared: dict[str, list[dict[str, Any]]] = {}
    duplicate_rows_skipped: dict[str, int] = {}
    for kind, items in rows.items():
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        skipped = 0
        for row in items:
            key = _record_key(kind, row)
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            unique.append(row)
        prepared[kind] = unique
        duplicate_rows_skipped[kind] = skipped
    summary = {"dry_run": not args.apply, "tables": {}, "duplicate_rows_skipped": duplicate_rows_skipped}
    exit_code = 0
    for kind, items in prepared.items():
        try:
            summary["tables"][kind] = _post_rows(TABLE_MAP[kind], items, dry_run=not args.apply)
        except Exception as exc:
            summary["tables"][kind] = {"table": TABLE_MAP[kind], "prepared": len(items), "inserted": 0, "dry_run": not args.apply, "error": str(exc)}
            exit_code = 1
    print(json.dumps(summary, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
