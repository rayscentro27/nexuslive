#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.trading_safety_gate import evaluate_trading_safety


STATUS_FILE = ROOT / "logs" / "trading_engine_status.json"


def fetch_json(url: str) -> dict:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        proc = subprocess.run(["curl", "-sS", url], capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
        raise RuntimeError(f"receiver_fetch_failed: {exc}") from exc


def _status_file_fallback() -> dict:
    if not STATUS_FILE.exists():
        raise RuntimeError("receiver_status_file_missing")
    data = json.loads(STATUS_FILE.read_text())
    port = int(data.get("signal_port") or 5000)
    proc = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    listening = proc.returncode == 0 and "LISTEN" in proc.stdout
    mtime = datetime.fromtimestamp(STATUS_FILE.stat().st_mtime, tz=timezone.utc)
    fresh = datetime.now(timezone.utc) - mtime < timedelta(hours=6)
    safe_mode_active = bool(data.get("paper_only")) and not bool(data.get("live_trading"))
    health = {
        "status": "healthy" if listening and fresh and data.get("receiver_started") else "blocked",
        "status_source": "artifact_fallback",
        "status_file": str(STATUS_FILE),
        "status_file_mtime": mtime.isoformat(),
        "fresh_status_file": fresh,
        "receiver_started": bool(data.get("receiver_started")),
        "configured_port": port,
        "listener_detected": listening,
        "safe_mode_active": safe_mode_active,
        "broker_mode": data.get("broker_type"),
        "live_trading": bool(data.get("live_trading")),
        "signals_received": data.get("signals_processed"),
    }
    status = {
        "status": "healthy" if health["status"] == "healthy" else "blocked",
        "timestamp": data.get("updated_at"),
        "receiver": {"port": port},
        "engine": {
            "broker_mode": data.get("broker_type"),
            "paper_only": data.get("paper_only"),
            "live_trading": data.get("live_trading"),
            "live_trading_enabled": data.get("live_execution_enabled"),
            "auto_trading": data.get("auto_trading"),
            "broker_connected": data.get("broker_connected"),
            "port": port,
            "signals_processed": data.get("signals_processed"),
            "safe_mode_active": safe_mode_active,
            "safety_status": "safe" if safe_mode_active else "blocked",
            "receiver_status": health["status"],
        },
        "last_signal": data.get("last_signal"),
        "artifact_fallback": True,
        "listener_detected": listening,
        "fresh_status_file": fresh,
    }
    if health["status"] != "healthy":
        raise RuntimeError("receiver_artifact_fallback_unhealthy")
    return {"health": health, "status": status}


def main() -> int:
    safety = evaluate_trading_safety()
    fallback_used = False
    try:
        health = fetch_json("http://127.0.0.1:5000/health")
        status = fetch_json("http://127.0.0.1:5000/status")
    except Exception:
        fallback = _status_file_fallback()
        health = fallback["health"]
        status = fallback["status"]
        fallback_used = True
    payload = {
        "safety_gate": safety,
        "health": health,
        "status": status,
        "fallback_used": fallback_used,
    }
    print(json.dumps(payload, indent=2))
    return 0 if safety["safe"] and health.get("status") == "healthy" else 1


if __name__ == "__main__":
    raise SystemExit(main())
