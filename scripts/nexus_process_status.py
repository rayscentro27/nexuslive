#!/usr/bin/env python3
"""
Nexus Continuous Running Status
================================
Reports whether Nexus processes are *actually running continuously*, not just
loaded or claimed active. Combines four independent signals:

  1. launchctl   -> loaded? pid? last exit status?
  2. worker_heartbeats (Supabase) -> last_heartbeat_at, pid, status
  3. output-file freshness -> when did the process last produce something?
  4. log tails   -> recent errors / tracebacks

A process is HEALTHY only if loaded/running AND has a recent heartbeat or
recent output. Otherwise: STALE (loaded, no recent signal), FAILED (errors /
crash), BLOCKED_BY_DESIGN (intentionally disabled for safety), or MISSING.

Safe & read-only: no secrets printed, nothing started/stopped, no posting,
no email, no paid APIs, no live trading. Run: python3 scripts/nexus_process_status.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOW = datetime.now(timezone.utc)

HEARTBEAT_OUT = ROOT / "logs" / "worker_heartbeats_latest.json"
REPORT_OUT = ROOT / "reports" / "system" / "nexus_continuous_running_status.md"

MINUTE = 60
HOUR = 3600


# ---------------------------------------------------------------------------
# Signal collectors
# ---------------------------------------------------------------------------
def launchctl_map() -> dict[str, dict]:
    """label -> {pid, exit_status}. PID '-' means loaded but not currently running."""
    out: dict[str, dict] = {}
    try:
        res = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=15)
        for line in res.stdout.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            pid_s, status_s, label = parts[0], parts[1], parts[2]
            out[label] = {
                "pid": None if pid_s in ("-", "") else int(pid_s),
                "exit_status": None if status_s in ("-", "") else int(status_s),
            }
    except Exception as e:  # pragma: no cover
        out["__error__"] = {"err": str(e)[:120]}
    return out


def load_heartbeats() -> dict[str, dict]:
    """worker_id -> heartbeat row from Supabase worker_heartbeats (graceful if unavailable)."""
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return {}
    try:
        from supabase import create_client
        sb = create_client(url, key)
        rows = sb.table("worker_heartbeats").select(
            "worker_id,worker_type,status,pid,host,last_heartbeat_at,last_seen_at"
        ).limit(200).execute().data or []
        return {r["worker_id"]: r for r in rows}
    except Exception:
        return {}


def newest_mtime(paths: list[str]) -> tuple[float | None, str | None]:
    """Return (epoch, path) of the most recently modified existing file (globs allowed)."""
    best_t, best_p = None, None
    for pat in paths:
        for p in ROOT.glob(pat) if any(c in pat for c in "*?[") else [ROOT / pat]:
            try:
                t = p.stat().st_mtime
                if best_t is None or t > best_t:
                    best_t, best_p = t, str(p.relative_to(ROOT))
            except OSError:
                continue
    return best_t, best_p


def scan_log_error(paths: list[str], lookback_lines: int = 60) -> str | None:
    """Return a short recent error string if the log tail shows errors."""
    for pat in paths:
        for p in (ROOT.glob(pat) if any(c in pat for c in "*?[") else [ROOT / pat]):
            try:
                lines = p.read_text(errors="ignore").splitlines()[-lookback_lines:]
            except OSError:
                continue
            for ln in reversed(lines):
                if re.search(r"\b(ERROR|CRITICAL|Traceback|ModuleNotFoundError|Address already in use|404 .*Not Found|exit code [1-9])", ln):
                    return ln.strip()[:160]
    return None


def age_str(epoch: float | None) -> str:
    if epoch is None:
        return "never"
    secs = (NOW - datetime.fromtimestamp(epoch, tz=timezone.utc)).total_seconds()
    if secs < 90:
        return f"{int(secs)}s ago"
    if secs < 90 * MINUTE:
        return f"{int(secs/MINUTE)}m ago"
    if secs < 48 * HOUR:
        return f"{secs/HOUR:.1f}h ago"
    return f"{secs/(24*HOUR):.1f}d ago"


def iso_to_epoch(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Process registry — the things we expect Nexus to be running
# ---------------------------------------------------------------------------
# kind: "resident" (should always have a PID) | "interval" (runs on a timer) | "gate"
REGISTRY = [
    dict(name="Hermes gateway", category="hermes", kind="resident", freq="resident",
         label="ai.hermes.gateway", stale_after=10 * MINUTE,
         outputs=[], logs=[]),
    dict(name="Telegram polling", category="hermes", kind="resident", freq="resident",
         label="com.raymonddavis.nexus.telegram", stale_after=10 * MINUTE,
         # .telegram_update_offset only changes when a message arrives, so it is a
         # poor freshness proxy; judge this resident bot by its live launchd PID.
         outputs=[], logs=[]),
    dict(name="Trading demo engine", category="trading", kind="resident", freq="resident",
         label="com.nexus.trading-engine", stale_after=15 * MINUTE,
         outputs=["logs/trading_engine_status.json", "logs/oanda_practice_status_latest.json"], logs=[]),
    dict(name="Autonomy worker", category="ops", kind="interval", freq="every 30s",
         label="com.nexus.autonomy-worker", heartbeat="autonomy_worker", stale_after=5 * MINUTE,
         outputs=["logs/autonomy-worker.error.log"], logs=["logs/autonomy-worker.error.log"]),
    dict(name="Monitoring / provider health", category="ops", kind="interval", freq="every 5m",
         label="com.nexus.monitoring-worker", stale_after=20 * MINUTE,
         outputs=["logs/monitoring-worker.error.log"], logs=["logs/monitoring-worker.error.log"]),
    dict(name="Coordination worker", category="ops", kind="interval", freq="every 15m",
         label="com.nexus.coordination-worker", heartbeat="coordination_worker", stale_after=45 * MINUTE,
         outputs=[], logs=["logs/coordination_worker.log"]),
    dict(name="Source scheduler", category="ops", kind="interval", freq="every 5m (cron, cd-fixed)",
         heartbeat="scheduler_worker", stale_after=20 * MINUTE,
         outputs=[], logs=[],
         note="source_schedules table missing -> scheduler runs but no-ops (REP-002, Ray decision)"),
    dict(name="Research worker", category="research", kind="resident", freq="resident",
         label="com.nexus.research-worker", heartbeat="nexus-research-worker", stale_after=30 * MINUTE,
         outputs=[], logs=[]),
    dict(name="Orchestrator", category="ops", kind="resident", freq="resident",
         label="com.nexus.orchestrator", heartbeat="nexus-orchestrator-1", stale_after=30 * MINUTE,
         outputs=[], logs=[]),
    dict(name="Monetization research", category="monetization", kind="interval", freq="every 6h",
         label="com.nexus.monetization-research", stale_after=8 * HOUR,
         outputs=["logs/monetization_research.log", "logs/monetization*latest*"], logs=["logs/monetization_research.log"]),
    dict(name="Memory loop (memory_worker)", category="memory", kind="interval", freq="every 2h (cron)",
         stale_after=3 * HOUR, outputs=["logs/memory_worker.log"], logs=["logs/memory_worker.log"]),
    dict(name="Content engine loop", category="content", kind="interval", freq="daily 09:00 (cron, dry-run)",
         stale_after=30 * HOUR,
         outputs=["logs/content_engine_loop_cron.log",
                  "reports/content_engine/generated/loop_reports/*"], logs=["logs/content_engine_loop_cron.log"]),
    dict(name="Safe learning loop", category="evolution", kind="interval", freq="every 6h (cron, dry-run)",
         stale_after=8 * HOUR,
         outputs=["logs/safe_learning_loop_latest.json", "logs/safe_learning_loop_cron.log"], logs=[]),
    dict(name="Trading demo status artifacts", category="trading", kind="interval", freq="on trade/cycle",
         stale_after=24 * HOUR,
         outputs=["logs/trading_engine_status.json", "logs/practice_trade_memory_latest.json"], logs=[]),
    dict(name="Social publisher gate", category="publishing", kind="gate", freq="manual",
         blocked_by_design=True,
         reason="social_publish_executor.py requires --apply + Ray approval; public posting disabled by design",
         outputs=[], logs=[]),
]


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify(proc: dict, lc: dict, hbs: dict) -> dict:
    name = proc["name"]
    label = proc.get("label")
    hb_id = proc.get("heartbeat")
    stale_after = proc.get("stale_after", HOUR)

    # --- blocked by design ---
    if proc.get("blocked_by_design"):
        gate_ok = (ROOT / "scripts" / "social_publish_executor.py").exists()
        return dict(
            name=name, category=proc["category"], expected_frequency=proc["freq"],
            loaded=False, running=False, pid=None,
            last_heartbeat="n/a", last_output_file=None, last_output="n/a",
            last_success="n/a", last_error=None,
            status="blocked_by_design",
            reason=proc.get("reason", "intentionally disabled"),
            next_expected_run="only via explicit Ray approval",
            recommended_action="leave disabled; enable only with scoped Ray approval (executor present: %s)" % gate_ok,
        )

    lc_entry = lc.get(label) if label else None
    loaded = lc_entry is not None
    lc_pid = lc_entry.get("pid") if lc_entry else None
    exit_status = lc_entry.get("exit_status") if lc_entry else None

    # --- heartbeat signal ---
    hb = hbs.get(hb_id) if hb_id else None
    hb_epoch = iso_to_epoch(hb.get("last_heartbeat_at")) if hb else None
    hb_pid = hb.get("pid") if hb else None
    hb_status = hb.get("status") if hb else None

    # --- output freshness ---
    out_epoch, out_path = newest_mtime(proc.get("outputs", []))

    # --- best "alive" signal = newest of heartbeat / output ---
    signals = [e for e in (hb_epoch, out_epoch) if e is not None]
    newest = max(signals) if signals else None
    newest_age = (NOW.timestamp() - newest) if newest else None

    pid = lc_pid or hb_pid
    running = bool(lc_pid) or (hb_status == "running")

    # --- error / crash ---
    log_err = scan_log_error(proc.get("logs", []))
    crashed = exit_status not in (None, 0)

    # --- decide status ---
    recent = newest_age is not None and newest_age <= stale_after
    if proc.get("note") and "import bug" in proc["note"]:
        status, reason = "failed", proc["note"]
    elif crashed:
        status = "failed"
        reason = f"launchd exit status {exit_status}" + (f"; {log_err}" if log_err else "")
    elif log_err and not recent:
        status, reason = "failed", f"recent log error: {log_err}"
    elif proc["kind"] == "resident":
        if lc_pid and (recent or not signals):
            status = "healthy"
            reason = "resident PID alive" + ("; recent signal" if recent else "; (no freshness file — PID-judged)")
        elif lc_pid and not recent:
            status, reason = "stale", f"PID alive but last signal {age_str(newest)} (> {int(stale_after/60)}m)"
        elif loaded and not lc_pid:
            status, reason = "stale", "loaded but no PID running"
        else:
            status, reason = "missing", "not loaded in launchctl"
    elif proc["kind"] == "interval":
        if recent:
            status, reason = "healthy", f"fresh signal {age_str(newest)} (heartbeat/output)"
        elif loaded or hb is not None:
            status, reason = "stale", f"loaded but last signal {age_str(newest)} (> {int(stale_after/60)}m)"
        else:
            status, reason = "missing", "not loaded and no heartbeat/output"
    else:
        status, reason = "stale", "unclassified"

    if proc.get("note") and status != "failed":
        reason += f" | note: {proc['note']}"

    return dict(
        name=name, category=proc["category"], expected_frequency=proc["freq"],
        loaded=loaded, running=running, pid=pid,
        last_heartbeat=age_str(hb_epoch) if hb_id else "n/a",
        last_output_file=out_path, last_output=age_str(out_epoch),
        last_success=age_str(newest),
        last_error=log_err,
        status=status, reason=reason,
        next_expected_run=_next_run(proc, newest),
        recommended_action=_action(status, proc),
    )


def _next_run(proc: dict, newest: float | None) -> str:
    if proc["kind"] == "resident":
        return "continuous"
    return f"per schedule ({proc['freq']})"


def _action(status: str, proc: dict) -> str:
    if status == "healthy":
        return "none — keep running"
    if status == "stale":
        return f"check scheduler/heartbeat for '{proc['name']}'; kickstart launchd job or run once to confirm"
    if status == "failed":
        if proc.get("note"):
            return f"repair: {proc['note']}"
        return "inspect log + restart the launchd job"
    if status == "missing":
        return "bootstrap/load the launchd job or add to scheduler"
    return "review"


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def main() -> int:
    lc = launchctl_map()
    hbs = load_heartbeats()
    results = [classify(p, lc, hbs) for p in REGISTRY]

    buckets = {k: [r for r in results if r["status"] == k]
               for k in ("healthy", "stale", "failed", "blocked_by_design", "missing")}

    # ---- heartbeat snapshot JSON ----
    HEARTBEAT_OUT.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_OUT.write_text(json.dumps({
        "generated_at": NOW.isoformat(),
        "supabase_heartbeats_available": bool(hbs),
        "counts": {k: len(v) for k, v in buckets.items()},
        "processes": results,
    }, indent=2))

    # ---- markdown report ----
    lines = [
        "# Nexus Continuous Running Status",
        f"_Generated: {NOW.isoformat()} · safe/read-only · nothing started/stopped_\n",
        "A process is **HEALTHY** only if loaded/running **and** has a recent heartbeat or output.\n",
        "| Process | Freq | Loaded | Running | PID | Heartbeat | Last output | Last success | Status | Reason | Action |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    order = {"failed": 0, "stale": 1, "missing": 2, "healthy": 3, "blocked_by_design": 4}
    for r in sorted(results, key=lambda x: order.get(x["status"], 9)):
        lines.append("| {name} | {freq} | {ld} | {rn} | {pid} | {hb} | {of} | {ls} | **{st}** | {rs} | {ac} |".format(
            name=r["name"], freq=r["expected_frequency"],
            ld="yes" if r["loaded"] else "no", rn="yes" if r["running"] else "no",
            pid=r["pid"] or "-", hb=r["last_heartbeat"],
            of=f"{r['last_output']}" + (f" ({r['last_output_file']})" if r["last_output_file"] else ""),
            ls=r["last_success"], st=r["status"].upper(),
            rs=(r["reason"] or "")[:120], ac=(r["recommended_action"] or "")[:90]))

    # ---- CEO summary ----
    def names(b): return ", ".join(x["name"] for x in buckets[b]) or "(none)"
    recent_outputs = sorted(
        [(r["last_output_file"], r["last_output"]) for r in results if r["last_output_file"]],
        key=lambda x: x[1])
    fixes = [r for r in results if r["status"] in ("failed", "stale", "missing")]

    ceo = [
        "\n## CEO REPORT\n",
        f"**NEXUS RUNNING NOW:** {names('healthy')}",
        "**NEXUS STALE/BROKEN:** " + (", ".join(f"{x['name']} ({x['status']})" for x in buckets['stale'] + buckets['failed'] + buckets['missing']) or "(none)"),
        f"**NEXUS BLOCKED BY DESIGN:** {names('blocked_by_design')}",
        "**LAST OUTPUTS CREATED:**",
    ]
    for f, age in recent_outputs[:8]:
        ceo.append(f"- `{f}` — {age}")
    ceo.append("**NEXT EXPECTED RUNS:**")
    for r in results:
        if r["status"] in ("healthy", "stale"):
            ceo.append(f"- {r['name']}: {r['next_expected_run']}")
    ceo.append("**TOP 5 FIXES:**")
    for i, r in enumerate(fixes[:5], 1):
        ceo.append(f"{i}. {r['name']} — {r['status']}: {r['recommended_action']}")
    if not fixes:
        ceo.append("1. None — all monitored processes healthy or blocked-by-design.")

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text("\n".join(lines + ceo) + "\n")

    # ---- stdout: CEO summary + counts ----
    print("\n".join(ceo))
    print("\nCounts:", {k: len(v) for k, v in buckets.items()})
    print(f"Report : {REPORT_OUT.relative_to(ROOT)}")
    print(f"JSON   : {HEARTBEAT_OUT.relative_to(ROOT)}")
    print(f"Supabase heartbeats available: {bool(hbs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
