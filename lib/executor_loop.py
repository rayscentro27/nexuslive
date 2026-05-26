"""
Executor Loop — Nexus Persistent Worker
==========================================
Runs a continuous polling loop that:
  1. Checks worker quotas — alerts Hermes on misses
  2. Processes queued improvement tasks
  3. Triggers content generation on schedule
  4. Triggers research synthesis
  5. Triggers affiliate audit
  6. Generates daily trading report
  7. Reports to CEO briefing table

SAFE autonomous mode — never publishes, never bills, never deploys.

Usage:
  python3 -m lib.executor_loop               # run indefinitely
  python3 -m lib.executor_loop --once        # run one cycle then exit
  python3 bin/nexus workforce loop           # via CLI
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, date, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CYCLE_INTERVAL_SECONDS = int(os.getenv("EXECUTOR_CYCLE_SECONDS", "300"))   # 5 min default
CONTENT_HOUR           = int(os.getenv("CONTENT_GENERATION_HOUR", "6"))    # 6am daily
RESEARCH_HOUR          = int(os.getenv("RESEARCH_SYNTHESIS_HOUR", "7"))    # 7am daily
BRIEFING_HOUR          = int(os.getenv("CEO_BRIEFING_HOUR", "7"))          # 7am daily
AFFILIATE_HOUR         = int(os.getenv("AFFILIATE_AUDIT_HOUR", "8"))       # 8am daily

_running = True


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[executor {ts}] {msg}", flush=True)


def _now_hour() -> int:
    return datetime.now().hour


def _today() -> str:
    return date.today().isoformat()


def _flag_file(name: str) -> Path:
    """Track whether a daily task has already run today."""
    flag_dir = ROOT / "artifacts" / "executor_flags"
    flag_dir.mkdir(parents=True, exist_ok=True)
    return flag_dir / f"{_today()}_{name}.done"


def _mark_done(name: str) -> None:
    _flag_file(name).write_text(datetime.now().isoformat())


def _already_done(name: str) -> bool:
    return _flag_file(name).exists()


# ─── Quota enforcement ────────────────────────────────────────────────────────

DAILY_QUOTAS = {
    "content_worker":    {"content_pieces": 11},  # 1 YT + 1 newsletter + 3 TikTok + 5 X + 1 LinkedIn = 11
    "research_worker":   {"insights": 5},
    "affiliate_worker":  {"opportunities": 2},
    "improvement_worker":{"audits": 1},
    "ceo_brief_worker":  {"reports": 1},
}


def check_quota_compliance() -> list[dict]:
    """Check today's quota compliance. Return list of missed quotas."""
    try:
        from scripts.prelaunch_utils import rest_select
        today = _today()
        rows = rest_select(
            f"worker_daily_quotas?select=worker_id,quota_type,current_count,target_per_day,met,missed"
            f"&quota_date=eq.{today}&limit=50",
            timeout=8,
        ) or []

        missed = [r for r in rows if r.get("missed") or (int(r.get("current_count", 0)) < int(r.get("target_per_day", 1)))]
        return missed
    except Exception:
        return []


def alert_hermes_quota_miss(worker_id: str, quota_type: str, current: int, target: int) -> None:
    """Log a quota miss as a worker failure event."""
    try:
        import json
        import urllib.request
        url = (os.getenv("SUPABASE_URL") or "").strip()
        key = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", ""))
        if not url or not key:
            return
        payload = {
            "worker_id": worker_id,
            "failure_type": "quota_miss",
            "error_message": f"Quota missed: {quota_type} — {current}/{target} completed",
            "context": {"quota_type": quota_type, "current": current, "target": target},
            "alerted_hermes": True,
            "alerted_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/worker_failure_events",
            data=data,
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8):
            pass
    except Exception:
        pass


# ─── Daily tasks ──────────────────────────────────────────────────────────────

def run_content_pipeline_if_due() -> bool:
    if _already_done("content_pipeline"):
        return False
    if _now_hour() < CONTENT_HOUR:
        return False
    _log("Running daily content pipeline...")
    try:
        from lib.daily_content_engine import run_daily_pipeline
        result = run_daily_pipeline()
        _log(f"Content pipeline: {result['total_outputs']} outputs | errors: {len(result['errors'])}")
        _mark_done("content_pipeline")
        return True
    except Exception as exc:
        _log(f"Content pipeline ERROR: {exc}")
        return False


def run_research_synthesis_if_due() -> bool:
    if _already_done("research_synthesis"):
        return False
    if _now_hour() < RESEARCH_HOUR:
        return False
    _log("Running research synthesis pipeline...")
    try:
        from lib.research_synthesis_pipeline import run_research_pipeline
        result = run_research_pipeline(limit=20)
        _log(f"Research synthesis: {result['processed']} processed | {result['recommendations_created']} recs")
        _mark_done("research_synthesis")
        return True
    except Exception as exc:
        _log(f"Research synthesis ERROR: {exc}")
        return False


def run_ceo_briefing_if_due() -> bool:
    if _already_done("ceo_briefing"):
        return False
    if _now_hour() < BRIEFING_HOUR:
        return False
    _log("Generating CEO morning briefing...")
    try:
        from lib.ceo_morning_briefing import generate_morning_briefing, deliver_briefing
        briefing = generate_morning_briefing()
        log = deliver_briefing(briefing)
        _log(f"CEO briefing: saved={log.get('saved')} | telegram={log.get('telegram')}")
        _mark_done("ceo_briefing")
        return True
    except Exception as exc:
        _log(f"CEO briefing ERROR: {exc}")
        return False


def run_affiliate_audit_if_due() -> bool:
    if _already_done("affiliate_audit"):
        return False
    if _now_hour() < AFFILIATE_HOUR:
        return False
    _log("Running affiliate monetization audit...")
    try:
        from lib.affiliate_engine import run_affiliate_audit
        result = run_affiliate_audit()
        _log(f"Affiliate audit: {result['immediately_applicable']} immediate | {result['recommendations_created']} recs")
        _mark_done("affiliate_audit")
        return True
    except Exception as exc:
        _log(f"Affiliate audit ERROR: {exc}")
        return False


def run_productivity_rollup_if_due() -> bool:
    if _already_done("productivity_rollup"):
        return False
    try:
        from lib.worker_accountability import rollup_worker_productivity
        rollups = rollup_worker_productivity()
        _log(f"Productivity rollup: {len(rollups)} workers")
        _mark_done("productivity_rollup")
        return True
    except Exception as exc:
        _log(f"Productivity rollup ERROR: {exc}")
        return False


def run_improvement_cycle() -> None:
    """Claim and log one improvement task per cycle if idle."""
    try:
        from lib.autonomous_improvement_queue import claim_idle_task, seed_improvement_tasks, queue_status
        qs = queue_status()
        if qs["planned"] == 0:
            seeded = seed_improvement_tasks(limit=2)
            if seeded:
                _log(f"Improvement: seeded {len(seeded)} tasks")
        task = claim_idle_task("improvement_worker")
        if task:
            _log(f"Improvement: claimed '{task.get('normalized_goal','?')[:50]}'")
    except Exception as exc:
        _log(f"Improvement cycle ERROR: {exc}")


# ─── Main loop ────────────────────────────────────────────────────────────────

def run_cycle() -> dict:
    """Execute one full worker cycle. Returns summary."""
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tasks_run": [],
        "quota_misses": [],
    }

    # Daily scheduled tasks (run once per day at scheduled hour)
    if run_ceo_briefing_if_due():
        summary["tasks_run"].append("ceo_briefing")
    if run_content_pipeline_if_due():
        summary["tasks_run"].append("content_pipeline")
    if run_research_synthesis_if_due():
        summary["tasks_run"].append("research_synthesis")
    if run_affiliate_audit_if_due():
        summary["tasks_run"].append("affiliate_audit")
    if run_productivity_rollup_if_due():
        summary["tasks_run"].append("productivity_rollup")

    # Every cycle: improvement queue
    run_improvement_cycle()

    # Quota compliance check
    missed = check_quota_compliance()
    for m in missed:
        wid = m.get("worker_id", "?")
        qt  = m.get("quota_type", "?")
        cur = int(m.get("current_count", 0))
        tgt = int(m.get("target_per_day", 1))
        summary["quota_misses"].append(f"{wid}.{qt}: {cur}/{tgt}")
        if cur < tgt:
            alert_hermes_quota_miss(wid, qt, cur, tgt)

    return summary


def run_loop(once: bool = False) -> None:
    """Main executor loop. Runs until interrupted or once=True."""
    _log("Nexus Executor Loop starting...")
    _log(f"Cycle interval: {CYCLE_INTERVAL_SECONDS}s | Content hour: {CONTENT_HOUR}:00")
    _log("Safe mode: no publish, no billing, no deploy")
    _log("Press Ctrl+C to stop.\n")

    def _shutdown(sig, frame):
        global _running
        _running = False
        _log("Shutting down...")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    cycle = 0
    while _running:
        cycle += 1
        _log(f"=== Cycle {cycle} ===")
        summary = run_cycle()

        if summary["tasks_run"]:
            _log(f"Ran: {', '.join(summary['tasks_run'])}")
        if summary["quota_misses"]:
            _log(f"Quota misses: {', '.join(summary['quota_misses'])}")
        else:
            _log("Quotas: OK")

        if once:
            _log("--once mode: exiting after one cycle.")
            break

        _log(f"Next cycle in {CYCLE_INTERVAL_SECONDS}s...\n")
        for _ in range(CYCLE_INTERVAL_SECONDS):
            if not _running:
                break
            time.sleep(1)

    _log("Executor loop stopped.")


if __name__ == "__main__":
    once = "--once" in sys.argv
    run_loop(once=once)
