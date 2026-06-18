"""run_lock.py — simple file-based run lock + idempotency for scheduled jobs.

Prevents duplicate schedulers (e.g. the same trading/demo report job loaded in two
checkouts) from running the same report twice and double-sending. No external deps.

Usage:
    from lib import run_lock
    if not run_lock.acquire("demo_trading_report", min_interval_sec=1800):
        # another run started recently — exit quietly (write a skipped report, no Telegram)
        ...
    try:
        ... do work ...
        run_lock.mark_done("demo_trading_report")
    finally:
        run_lock.release("demo_trading_report")
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCK_DIR = ROOT / "outputs" / "locks"


def _lock_path(name: str) -> Path:
    return LOCK_DIR / f"{name}.lock"


def _state_path(name: str) -> Path:
    return LOCK_DIR / f"{name}_last_run.json"


def acquire(name: str, *, min_interval_sec: int = 1800, stale_sec: int = 3600) -> bool:
    """Return True if this run may proceed. False if another run started within
    min_interval_sec (or a fresh lock is held). Stale locks are reclaimed."""
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock = _lock_path(name)

    # An un-stale lock means another run is in progress.
    if lock.exists():
        try:
            age = time.time() - lock.stat().st_mtime
        except Exception:
            age = stale_sec + 1
        if age < stale_sec:
            return False

    # Idempotency: did a run complete within min_interval_sec?
    try:
        st = json.loads(_state_path(name).read_text())
        if time.time() - st.get("last_done_ts", 0) < min_interval_sec:
            return False
    except Exception:
        pass

    try:
        lock.write_text(json.dumps({"pid": os.getpid(), "ts": time.time()}))
    except Exception:
        return True  # fail open: never block real work on a lock-write error
    return True


def mark_done(name: str) -> None:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    try:
        _state_path(name).write_text(json.dumps({"last_done_ts": time.time()}))
    except Exception:
        pass


def release(name: str) -> None:
    try:
        _lock_path(name).unlink(missing_ok=True)
    except Exception:
        pass
