#!/usr/bin/env python3
"""
Trading autonomy status for Nexus operator surfaces.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path("/Users/raymonddavis/nexus-ai")
STATUS_FILE = ROOT / "logs" / "trading_engine_status.json"
TRADING_LOG = ROOT / "logs" / "trading_engine.log"
TRADING_ERR_LOG = ROOT / "logs" / "trading_engine.err.log"
HEALTH_URL = "http://127.0.0.1:5000/health"
DETAIL_URL = "http://127.0.0.1:5000/status"


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def fetch_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}


def process_running() -> bool:
    result = subprocess.run(
        ["pgrep", "-f", "trading-engine/nexus_trading_engine.py"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode == 0 and bool((result.stdout or "").strip())


def tail(path: Path, limit: int = 3) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()[-limit:]


def build_status() -> dict:
    saved = read_json(STATUS_FILE)
    health = fetch_json(HEALTH_URL)
    detail = fetch_json(DETAIL_URL)
    return {
        "process_running": process_running(),
        "health": health,
        "detail": detail,
        "saved_status": saved,
        "recent_log_lines": tail(TRADING_LOG),
        "recent_error_lines": tail(TRADING_ERR_LOG),
    }


def print_brief(status: dict) -> None:
    saved = status["saved_status"]
    health_ok = "error" not in status["health"]
    print("Trading autonomy status")
    print(f"Process: {'running' if status['process_running'] else 'stopped'}")
    print(f"Receiver: {'healthy' if health_ok else 'unhealthy'}")
    print(
        "Mode: "
        f"{'paper' if saved.get('dry_run', True) else 'live'} | "
        f"{'auto' if saved.get('auto_trading') else 'manual'}"
    )
    print(
        "Engine: "
        f"broker={saved.get('broker_type', 'unknown')} "
        f"connected={saved.get('broker_connected', False)} "
        f"signals={saved.get('signals_processed', 0)} "
        f"positions={saved.get('active_positions', 0)}"
    )
    if saved.get("last_result"):
        print(f"Last result: {saved['last_result']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "brief"), default="json")
    args = parser.parse_args()
    status = build_status()
    if args.format == "json":
        print(json.dumps(status, indent=2))
    else:
        print_brief(status)


if __name__ == "__main__":
    main()
