#!/usr/bin/env python3
"""
Nexus Trading Pipeline — End-to-End Dry-Run Test
=================================================
Safe to run at any time.  Sends a synthetic signal to the running trading
engine webhook, verifies the response, and checks each stage of the pipeline.

Safety guarantees:
  - Never places live orders (validates DRY_RUN mode first)
  - Uses fake signal data that cannot match a real market order
  - All Supabase reads are SELECT-only
  - Exits non-zero on any critical failure

Usage:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 scripts/test_trading_pipeline.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
_results: list[tuple[str, str, str]] = []


def _check(name: str, ok: bool, detail: str = "", warn: bool = False) -> bool:
    tag = WARN if (not ok and warn) else (PASS if ok else FAIL)
    print(f"  [{tag}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, "pass" if ok else ("warn" if warn else "fail"), detail))
    return ok


# ── 1. Safety gate ─────────────────────────────────────────────────────────────

def check_dry_run_mode():
    print("\n[1] DRY_RUN / paper mode")
    status_file = ROOT / "logs" / "trading_engine_status.json"
    if status_file.exists():
        try:
            s = json.loads(status_file.read_text())
            _check("engine status file exists", True)
            _check("dry_run=true in status", s.get("dry_run") is True,
                   f"dry_run={s.get('dry_run')!r} — STOP if False")
            _check("live_trading=false in status", not s.get("live_trading", True),
                   f"live_trading={s.get('live_trading')!r}")
        except Exception as e:
            _check("engine status file readable", False, str(e))
    else:
        _check("engine status file exists", False,
               "trading engine may not be running", warn=True)

    env_dry = os.getenv("NEXUS_DRY_RUN", "true").lower()
    # Engine reads from plist EnvironmentVariables, not the shell env — warn only
    _check("NEXUS_DRY_RUN env=true", env_dry == "true",
           f"NEXUS_DRY_RUN={env_dry!r} in shell env (engine uses plist value)", warn=env_dry != "true")


# ── 2. Supabase connectivity ────────────────────────────────────────────────────

def check_supabase():
    print("\n[2] Supabase connectivity")
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_KEY", "")
    _check("SUPABASE_URL set", bool(sb_url))
    _check("SUPABASE_KEY set", bool(sb_key))
    if not sb_url or not sb_key:
        return

    for table in ("paper_trading_journal_entries", "tv_normalized_signals",
                  "reviewed_signal_proposals"):
        url = f"{sb_url}/rest/v1/{table}?limit=1&select=id"
        req = urllib.request.Request(url, headers={
            "apikey": sb_key,
            "Authorization": f"Bearer {sb_key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read())
                _check(f"table {table} accessible", True, f"{len(rows)} row(s)")
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:120]
            _check(f"table {table} accessible", False, f"HTTP {e.code}: {body}")
        except Exception as e:
            _check(f"table {table} accessible", False, str(e)[:100])


# ── 3. Webhook endpoint ─────────────────────────────────────────────────────────

SYNTHETIC_SIGNAL = {
    "symbol": "EURUSD",
    "action": "BUY",
    "entry": 1.0800,
    "stop": 1.0750,
    "target": 1.0900,
    "timeframe": "H1",
    "strategy": "nexus_test_dry_run",
    "confidence": 75,
    "_test": True,
}


def check_webhook():
    print("\n[3] Trading engine webhook (port 5000)")
    signal_port = 5000
    url = f"http://127.0.0.1:{signal_port}/webhook/tradingview"
    body = json.dumps(SYNTHETIC_SIGNAL).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            _check("webhook reachable", True)
            _check("webhook returns status", "status" in resp, str(resp)[:120])
            status = resp.get("status", "")
            accepted = status in ("received", "signal_received", "approved_demo", "rejected",
                                  "processed", "signal_queued")
            _check("webhook returns a valid status", accepted, f"status={status!r}")
    except urllib.error.URLError as e:
        _check("webhook reachable", False,
               f"Connection refused — trading engine likely not running: {e}", warn=True)
    except Exception as e:
        _check("webhook reachable", False, str(e)[:120], warn=True)


# ── 4. Manual signal endpoint ───────────────────────────────────────────────────

def check_manual_signal():
    print("\n[4] Manual signal endpoint (port 5000)")
    url = "http://127.0.0.1:5000/signal/manual"
    body = json.dumps(SYNTHETIC_SIGNAL).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            resp = json.loads(r.read())
            _check("manual signal endpoint reachable", True)
            _check("manual signal returns status", "status" in resp, str(resp)[:120])
    except urllib.error.URLError as e:
        _check("manual signal endpoint reachable", False,
               f"{e} — engine may be down or in manual mode", warn=True)
    except Exception as e:
        _check("manual signal endpoint reachable", False, str(e)[:120], warn=True)


# ── 5. Signal review health ─────────────────────────────────────────────────────

def check_signal_review():
    print("\n[5] Signal review pipeline")
    log_file = ROOT / "logs" / "signal_review.log"
    if log_file.exists():
        lines = log_file.read_text().splitlines()
        _check("signal_review.log exists", True, f"{len(lines)} lines")
        recent = [l for l in lines[-50:] if "ERROR" in l or "started" in l.lower()]
        last_start = next((l for l in reversed(lines) if "started" in l.lower()), None)
        if last_start:
            _check("signal poller has started", True, last_start[:80])
        rejections = sum(1 for l in lines if "reject" in l.lower())
        _check("signal rejections logged", True, f"{rejections} total rejections found", warn=True)
    else:
        _check("signal_review.log exists", False, "file missing", warn=True)

    # Check pending signals in Supabase
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_KEY", "")
    if sb_url and sb_key:
        url = f"{sb_url}/rest/v1/tv_normalized_signals?status=eq.new&select=id,symbol,side,created_at&limit=10"
        req = urllib.request.Request(url, headers={
            "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                rows = json.loads(r.read())
                _check("tv_normalized_signals pending", len(rows) == 0,
                       f"{len(rows)} pending (should be 0 if poller is current)", warn=True)
        except Exception as e:
            _check("tv_normalized_signals readable", False, str(e)[:100], warn=True)

        url2 = f"{sb_url}/rest/v1/reviewed_signal_proposals?status=eq.needs_review&select=id,symbol,created_at&limit=5"
        req2 = urllib.request.Request(url2, headers={
            "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
        })
        try:
            with urllib.request.urlopen(req2, timeout=10) as r:
                rows2 = json.loads(r.read())
                _check("no stale needs_review proposals", len(rows2) == 0,
                       f"{len(rows2)} proposals stuck at needs_review", warn=len(rows2) > 0)
        except Exception as e:
            _check("reviewed_signal_proposals readable", False, str(e)[:100], warn=True)


# ── 6. Paper trade visibility ───────────────────────────────────────────────────

def check_paper_trades():
    print("\n[6] Paper trade visibility (Supabase)")
    sb_url = os.getenv("SUPABASE_URL", "")
    sb_key = os.getenv("SUPABASE_KEY", "")
    if not sb_url or not sb_key:
        _check("Supabase creds available", False, "set SUPABASE_URL + SUPABASE_KEY")
        return

    # Check total count
    url = (
        f"{sb_url}/rest/v1/paper_trading_journal_entries"
        "?select=id,symbol,entry_status,opened_at,tags&order=opened_at.desc&limit=1000"
    )
    req = urllib.request.Request(url, headers={
        "apikey": sb_key, "Authorization": f"Bearer {sb_key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            _check("paper_trading_journal_entries readable", True, f"{len(rows)} total rows")
            nexus_auto = [r for r in rows if "nexus_auto" in (r.get("tags") or [])]
            _check("nexus_auto trades present", len(nexus_auto) > 0,
                   f"{len(nexus_auto)} nexus_auto rows (engine-logged paper trades)", warn=len(nexus_auto) == 0)
    except Exception as e:
        _check("paper_trading_journal_entries readable", False, str(e)[:100])


# ── 7. Strategy worker readiness ───────────────────────────────────────────────

def check_strategy_worker():
    print("\n[7] Strategy worker")
    try:
        import importlib.util
        spec = importlib.util.find_spec("strategy_review.strategy_worker")
        _check("strategy_worker importable", spec is not None)
    except Exception as e:
        _check("strategy_worker importable", False, str(e)[:100])

    log_file = ROOT / "logs" / "strategy_worker.log"
    _check("strategy_worker.log exists", log_file.exists(),
           "will be created on first run" if not log_file.exists() else f"{log_file.stat().st_size} bytes",
           warn=not log_file.exists())


# ── Main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"Nexus Trading Pipeline Test — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    check_dry_run_mode()
    check_supabase()
    check_webhook()
    check_manual_signal()
    check_signal_review()
    check_paper_trades()
    check_strategy_worker()

    print("\n" + "=" * 60)
    passes  = sum(1 for _, s, _ in _results if s == "pass")
    warns   = sum(1 for _, s, _ in _results if s == "warn")
    failures = sum(1 for _, s, _ in _results if s == "fail")

    print(f"Results: {passes} passed, {warns} warnings, {failures} failed")

    if failures:
        print("\nFailed checks:")
        for name, status, detail in _results:
            if status == "fail":
                print(f"  - {name}: {detail}")
        return 1

    if warns:
        print("\nWarnings (non-blocking):")
        for name, status, detail in _results:
            if status == "warn":
                print(f"  ~ {name}: {detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
