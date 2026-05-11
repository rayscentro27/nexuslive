#!/usr/bin/env python3
"""
Canonical replay history report.

Builds a read-only view of paper-trade run and replay-result history, selecting
one canonical replay path per proposal and surfacing the suppressed duplicates.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import error, request

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

ROOT = Path("/Users/raymonddavis/nexus-ai")
REPORT_FILE = ROOT / "logs" / "canonical_replay_history.json"


def env_first(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


SUPABASE_URL = env_first("SUPABASE_URL")
SUPABASE_READ_KEY = env_first("SUPABASE_ANON_KEY", "SUPABASE_KEY")


def iso_now() -> str:
    return datetime.now().isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str))
    tmp.replace(path)


def sb_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "apikey": SUPABASE_READ_KEY,
        "Authorization": f"Bearer {SUPABASE_READ_KEY}",
    }


def sb_get(query_path: str) -> list[dict[str, Any]]:
    url = f"{SUPABASE_URL}/rest/v1/{query_path}"
    req = request.Request(url, headers=sb_headers())
    with request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read())


def canonicalize(limit: int) -> dict[str, Any]:
    runs = sb_get(
        "paper_trade_runs"
        "?select=id,proposal_id,signal_id,symbol,strategy_id,status,started_at,finished_at,trace_id"
        "&order=started_at.asc"
        f"&limit={limit}"
    )
    results = sb_get(
        "replay_results"
        "?select=id,run_id,proposal_id,replay_outcome,pnl_r,pnl_pct,created_at,trace_id"
        "&order=created_at.asc"
        f"&limit={limit}"
    )

    results_by_run = {row.get("run_id"): row for row in results if row.get("run_id")}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        proposal_id = run.get("proposal_id")
        if not proposal_id:
            continue
        grouped.setdefault(str(proposal_id), []).append(run)

    report_rows: list[dict[str, Any]] = []
    duplicate_run_count = 0
    duplicate_result_count = 0
    for proposal_id, run_rows in grouped.items():
        ordered = sorted(run_rows, key=lambda row: str(row.get("started_at") or ""))
        canonical_run = ordered[0]
        canonical_result = results_by_run.get(canonical_run.get("id"))
        duplicate_runs = ordered[1:]
        duplicate_results = [
            results_by_run.get(row.get("id"))
            for row in duplicate_runs
            if results_by_run.get(row.get("id"))
        ]
        duplicate_run_count += len(duplicate_runs)
        duplicate_result_count += len(duplicate_results)
        report_rows.append(
            {
                "proposal_id": proposal_id,
                "symbol": canonical_run.get("symbol"),
                "strategy_id": canonical_run.get("strategy_id"),
                "canonical_run": canonical_run,
                "canonical_result": canonical_result,
                "duplicate_runs": duplicate_runs,
                "duplicate_results": duplicate_results,
            }
        )

    report = {
        "updated_at": iso_now(),
        "summary": {
            "proposal_groups": len(report_rows),
            "run_count": len(runs),
            "replay_result_count": len(results),
            "duplicate_run_count": duplicate_run_count,
            "duplicate_result_count": duplicate_result_count,
        },
        "groups": report_rows,
    }
    write_json(REPORT_FILE, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--format", choices=["json", "brief"], default="brief")
    args = parser.parse_args()

    try:
        report = canonicalize(args.limit)
    except error.HTTPError as exc:
        body = exc.read().decode(errors="ignore")
        raise SystemExit(f"Supabase read failed [{exc.code}]: {body}")

    if args.format == "json":
        print(json.dumps(report, indent=2))
        return

    summary = report["summary"]
    print("Canonical replay history")
    print(
        f"Proposal groups: {summary['proposal_groups']} | "
        f"runs: {summary['run_count']} | "
        f"replay results: {summary['replay_result_count']}"
    )
    print(
        f"Duplicates suppressed: "
        f"{summary['duplicate_run_count']} runs / {summary['duplicate_result_count']} results"
    )
    for row in report["groups"][:10]:
        print(
            f"{row['symbol']} / {row['strategy_id']} | canonical run={row['canonical_run']['id']} | duplicates={len(row['duplicate_runs'])}"
        )


if __name__ == "__main__":
    main()
