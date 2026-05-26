"""
Nexus Watcher Loop — Persistent Intelligence Monitor
=====================================================
Continuous watcher system: watch → extract → score → update → alert → assign.

Watchers run on recurring schedules (separate from executor_loop.py daily tasks).
Each watcher monitors a specific intelligence stream and writes findings to Supabase.

Watchers:
  trading_intelligence    — strategy signals, regime shifts, paper trade setups
  monetization            — affiliate trends, revenue opportunities, CTA performance
  youtube_trend           — viral topics, title trends, growth signals
  affiliate_opportunity   — new programs, commission changes, traffic alignment
  seo_opportunity         — rising keywords, content gaps, competitor moves
  funding_intelligence    — grants, loans, credit programs, expiry alerts

Usage:
  python3 -m lib.nexus_watcher_loop               # run indefinitely
  python3 -m lib.nexus_watcher_loop --once        # one cycle then exit
  bin/nexus watchers run                          # via CLI
"""
from __future__ import annotations

import json
import os
import signal
import sys
import time
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

WATCHER_CYCLE_SECONDS = int(os.getenv("WATCHER_CYCLE_SECONDS", "600"))  # 10 min

_running = True


def _log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[watcher {ts}] {msg}", flush=True)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _flag(name: str) -> Path:
    d = ROOT / "artifacts" / "watcher_flags"
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{name}_last_run.json"


def _last_run_hours(name: str) -> float:
    f = _flag(name)
    if not f.exists():
        return 9999.0
    try:
        data = json.loads(f.read_text())
        last = datetime.fromisoformat(data["ran_at"].replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last).total_seconds() / 3600
    except Exception:
        return 9999.0


def _mark_run(name: str, result: dict) -> None:
    _flag(name).write_text(json.dumps({"ran_at": _now(), **result}, indent=2, default=str))


def _save_finding(watcher: str, finding_type: str, title: str, summary: str,
                  priority: str = "medium", score: float = 50.0,
                  action_required: bool = False, evidence: str = "") -> bool:
    """Save a watcher finding to worker_recommendations in Supabase."""
    try:
        import urllib.request
        url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            return False
        payload = {
            "worker_id": f"watcher_{watcher}",
            "recommendation_type": finding_type,
            "title": title,
            "summary": summary,
            "priority": priority,
            "action_required": action_required,
            "context": json.dumps({"score": score, "evidence": evidence, "source": "watcher_loop"}),
            "created_at": _now(),
        }
        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/worker_recommendations",
            data=data,
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json", "Prefer": "return=minimal"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


# ── Individual watchers ───────────────────────────────────────────────────────

def watch_monetization(interval_hours: float = 6.0) -> dict:
    """Scan affiliate opportunities and content monetization signals."""
    if _last_run_hours("monetization") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    findings = 0
    try:
        from lib.affiliate_engine import get_immediately_applicable
        programs = get_immediately_applicable()
        for prog in programs[:3]:
            ok = _save_finding(
                "monetization",
                "affiliate_opportunity",
                f"Ready affiliate: {prog.get('name','?')}",
                f"ROI: {prog.get('roi_score',0)} | Commission: {prog.get('commission','?')} | No prerequisites",
                priority="high",
                score=float(prog.get("roi_score", 60)),
                action_required=True,
            )
            if ok:
                findings += 1
    except Exception as exc:
        _log(f"Monetization watcher error: {exc}")

    result = {"watcher": "monetization", "findings": findings, "ran_at": _now()}
    _mark_run("monetization", result)
    return result


def watch_trading_intelligence(interval_hours: float = 1.0) -> dict:
    """Monitor trading research state. No live signals — research only."""
    if _last_run_hours("trading_intelligence") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    findings = 0
    try:
        # Check research artifacts for new trading-related content
        from scripts.prelaunch_utils import rest_select
        rows = rest_select(
            "research_artifacts?select=id,topic,title,summary,created_at"
            "&topic=ilike.*trad*&order=created_at.desc&limit=5",
            timeout=8,
        ) or []
        if rows:
            for row in rows[:2]:
                _save_finding(
                    "trading_intelligence",
                    "trading_research_signal",
                    f"Trading research: {row.get('title','?')[:60]}",
                    str(row.get("summary", ""))[:200],
                    priority="medium",
                    score=55.0,
                )
                findings += 1
    except Exception as exc:
        _log(f"Trading intelligence watcher error: {exc}")

    result = {"watcher": "trading_intelligence", "findings": findings, "ran_at": _now()}
    _mark_run("trading_intelligence", result)
    return result


def watch_seo_opportunity(interval_hours: float = 6.0) -> dict:
    """Identify SEO article opportunities from content strategy."""
    if _last_run_hours("seo_opportunity") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    findings = 0
    try:
        seo_file = ROOT / "state" / "content_strategy.yaml"
        if seo_file.exists():
            import re
            content = seo_file.read_text()
            keywords = re.findall(r"- \"([^\"]+)\"", content)
            for kw in keywords[:3]:
                _save_finding(
                    "seo_opportunity",
                    "seo_keyword",
                    f"SEO opportunity: {kw}",
                    f"Target keyword from content strategy. Write 1,200+ word article with Lendio/Nav.com CTA.",
                    priority="medium",
                    score=65.0,
                    action_required=False,
                )
                findings += 1
    except Exception as exc:
        _log(f"SEO watcher error: {exc}")

    result = {"watcher": "seo_opportunity", "findings": findings, "ran_at": _now()}
    _mark_run("seo_opportunity", result)
    return result


def watch_funding_intelligence(interval_hours: float = 24.0) -> dict:
    """Check funding intelligence state for new opportunities."""
    if _last_run_hours("funding_intelligence") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    findings = 0
    try:
        from scripts.prelaunch_utils import rest_select
        rows = rest_select(
            "knowledge_entries?select=id,topic,title,summary,created_at"
            "&topic=eq.funding&order=created_at.desc&limit=5",
            timeout=8,
        ) or []
        for row in rows[:2]:
            _save_finding(
                "funding_intelligence",
                "funding_opportunity",
                f"Funding intel: {row.get('title','?')[:60]}",
                str(row.get("summary",""))[:200],
                priority="medium",
                score=60.0,
            )
            findings += 1
    except Exception as exc:
        _log(f"Funding intelligence watcher error: {exc}")

    result = {"watcher": "funding_intelligence", "findings": findings, "ran_at": _now()}
    _mark_run("funding_intelligence", result)
    return result


def watch_content_trends(interval_hours: float = 2.0) -> dict:
    """Identify trending content opportunities for content engine."""
    if _last_run_hours("content_trends") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    findings = 0
    # Content trend topics derived from current operational knowledge
    trend_topics = [
        ("AI business tools 2026", "ai_automation", 72),
        ("How to get business funding with bad credit", "funding", 80),
        ("Affiliate marketing for beginners 2026", "affiliate", 75),
        ("Build $1000/week passive income with AI", "monetization", 85),
    ]
    try:
        for title, topic, score in trend_topics[:2]:
            _save_finding(
                "content_trends",
                "content_opportunity",
                f"Trending topic: {title}",
                f"High-intent search topic. Create YouTube script + SEO article + newsletter section.",
                priority="high" if score >= 75 else "medium",
                score=float(score),
                action_required=score >= 75,
            )
            findings += 1
    except Exception as exc:
        _log(f"Content trends watcher error: {exc}")

    result = {"watcher": "content_trends", "findings": findings, "ran_at": _now()}
    _mark_run("content_trends", result)
    return result


# ── YouTube intelligence watcher ─────────────────────────────────────────────

def watch_youtube_intelligence(
    interval_hours: float = 12.0,
    division: str | None = None,
    limit: int = 8,
) -> dict:
    """Process due YouTube sources, extract intelligence, feed consensus."""
    if not division and _last_run_hours("youtube_intelligence") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    try:
        from lib.youtube_intelligence_worker import run_due_sources
        result = run_due_sources(division=division, limit=limit)
        if result.get("processed", 0) > 0:
            _log(f"  YouTube intel: {result['processed']} sources | {result['total_findings']} findings | {result['evidence_count']} evidence rows")
            _mark_run("youtube_intelligence", result)
        return result
    except Exception as exc:
        _log(f"YouTube intelligence watcher error: {exc}")
        return {"error": str(exc), "findings": 0}


# ── Consensus runner ──────────────────────────────────────────────────────────

def run_consensus_if_due(interval_hours: float = 6.0) -> dict:
    """Run the consensus engine to re-rank all opportunities."""
    if _last_run_hours("consensus_engine") < interval_hours:
        return {"skipped": True, "reason": "not_due"}

    try:
        from lib.nexus_consensus_engine import run_consensus
        result = run_consensus(save_to_supabase=True)
        _log(f"Consensus: {result['ranked_count']} opps | {result['critical_count']} CRITICAL | {result['high_count']} HIGH")
        _mark_run("consensus_engine", result)
        return result
    except Exception as exc:
        _log(f"Consensus engine error: {exc}")
        return {"error": str(exc)}


# ── Watcher cycle ─────────────────────────────────────────────────────────────

def run_watcher_cycle() -> dict:
    """Run all watchers. Returns summary of what fired."""
    summary = {"cycle_at": _now(), "watchers_ran": [], "total_findings": 0}

    watchers = [
        ("monetization",         lambda: watch_monetization(6.0)),
        ("trading_intelligence", lambda: watch_trading_intelligence(1.0)),
        ("seo_opportunity",      lambda: watch_seo_opportunity(6.0)),
        ("funding_intelligence", lambda: watch_funding_intelligence(24.0)),
        ("content_trends",       lambda: watch_content_trends(2.0)),
        ("youtube_intelligence", lambda: watch_youtube_intelligence(12.0)),
    ]

    for name, fn in watchers:
        try:
            result = fn()
            if not result.get("skipped"):
                findings = result.get("findings", 0)
                summary["watchers_ran"].append(name)
                summary["total_findings"] += findings
                _log(f"  {name}: {findings} findings")
        except Exception as exc:
            _log(f"  {name} ERROR: {exc}")

    # Run consensus every 6h
    consensus = run_consensus_if_due(6.0)
    if not consensus.get("skipped"):
        summary["watchers_ran"].append("consensus_engine")
        summary["consensus_top"] = consensus.get("top_opportunity", {}).get("title", "")

    return summary


def run_watcher_loop(once: bool = False) -> None:
    """Persistent watcher loop. Runs until interrupted."""
    _log("Nexus Watcher Loop starting...")
    _log(f"Cycle: {WATCHER_CYCLE_SECONDS}s | Press Ctrl+C to stop.")

    def _shutdown(sig, frame):
        global _running
        _running = False
        _log("Watcher loop shutting down...")

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    cycle = 0
    while _running:
        cycle += 1
        _log(f"=== Watcher Cycle {cycle} ===")
        summary = run_watcher_cycle()

        if summary["watchers_ran"]:
            _log(f"Active: {', '.join(summary['watchers_ran'])} | Findings: {summary['total_findings']}")
        else:
            _log("All watchers idle (none due)")

        if once:
            _log("--once: exiting.")
            break

        _log(f"Next check in {WATCHER_CYCLE_SECONDS}s...\n")
        for _ in range(WATCHER_CYCLE_SECONDS):
            if not _running:
                break
            time.sleep(1)

    _log("Watcher loop stopped.")


if __name__ == "__main__":
    once = "--once" in sys.argv
    run_watcher_loop(once=once)
