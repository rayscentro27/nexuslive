#!/usr/bin/env python3
"""
run_daily_engine_prerequisite_check.py
=======================================
Check which existing runners and lib files are present before building
the Daily Opportunity Intake + Monetization Decision Cycle.

Outputs:
  docs/reports/evidence/daily_engine_prerequisite_check_<timestamp>.md
  docs/reports/evidence/daily_engine_prerequisite_check_<timestamp>.json
"""
from __future__ import annotations
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
ROOT = Path(__file__).resolve().parent.parent

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

EXISTING_RUNNERS = [
    ("scripts/run_hermes_operating_loop.py",           "Hermes operating loop",                    "reuse"),
    ("scripts/run_nexus_monetization_operating_cycle.py", "Monetization operating cycle",          "integrate"),
    ("scripts/run_content_pipeline.py",                "Content pipeline",                         "integrate"),
    ("scripts/run_nexus_learn_by_doing_cycle.py",      "Learn-by-doing / credit/funding cycle",    "integrate"),
    ("scripts/run_youtube_intelligence_cycle.py",      "YouTube intelligence cycle",               "reuse"),
    ("scripts/run_youtube_source_reconciliation.py",   "YouTube source reconciliation",            "reuse"),
    ("scripts/run_weekly_github_trend_research.py",    "Weekly GitHub trend research",             "reuse"),
    ("scripts/run_hermes_evidence_audit.py",           "Hermes evidence audit",                    "reuse"),
    ("scripts/run_control_center_wsgi.py",             "Control center WSGI",                      "no_duplicate"),
]

LAUNCHD_WORKERS = [
    ("com.raymonddavis.nexus.telegram",    "Telegram bot"),
    ("com.raymonddavis.nexus.scheduler",   "Scheduler"),
    ("com.nexus.youtube-channel-poller",   "YouTube channel poller"),
    ("com.nexus.research-worker",          "Research worker"),
    ("com.nexus.orchestrator",             "Orchestrator"),
    ("com.nexus.trading-engine",           "Trading engine (DRY_RUN)"),
    ("com.nexus.strategy-lab",             "Strategy lab"),
    ("com.nexus.signal-router",            "Signal router"),
    ("com.nexus.signal-review",            "Signal review"),
    ("com.nexus.hermes",                   "Hermes gateway"),
    ("com.nexus.hermes-status",            "Hermes status"),
]

OPERATING_STRUCTURE = [
    "lib/hermes_goal_registry.py",
    "lib/hermes_tool_scout_registry.py",
    "lib/hermes_action_queue.py",
    "lib/hermes_decision_log.py",
    "lib/hermes_operating_loop.py",
    "docs/HERMES_OPERATING_DOCTRINE.md",
    "lib/nexus_artifact_registry.py",
    "lib/hermes_telegram_source_intake.py",
    "lib/hermes_scout_dispatcher.py",
    "lib/hermes_context_pack_builder.py",
    "lib/hermes_evidence_mode.py",
    "lib/hermes_final_response_gate.py",
    "lib/notification_policy.py",
    "lib/telegram_notification_policy.py",
]

def check_all() -> dict:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    result: dict = {
        "check_id": f"prereq_{ts}",
        "checked_at": _now(),
        "runners": [],
        "launchd_workers": [],
        "operating_structure": [],
        "missing_operating_structure": [],
        "telegram_can_send": [],
        "must_not_duplicate": [],
        "safe_to_proceed": True,
        "blockers": [],
    }

    # Check script runners
    for path, label, action in EXISTING_RUNNERS:
        exists = (ROOT / path).exists()
        entry = {"path": path, "label": label, "action": action, "exists": exists}
        result["runners"].append(entry)
        if action in ("no_duplicate",):
            result["must_not_duplicate"].append(path)
        if not exists and action in ("reuse", "integrate"):
            result["blockers"].append(f"MISSING runner that daily engine would reuse: {path}")

    # Check launchd plists
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    for label, desc in LAUNCHD_WORKERS:
        plist = launch_agents / f"{label}.plist"
        exists = plist.exists()
        result["launchd_workers"].append({"label": label, "description": desc, "plist_exists": exists})
        if label in ("com.raymonddavis.nexus.telegram", "com.nexus.youtube-channel-poller"):
            result["telegram_can_send"].append({"label": label, "can_send": exists})

    # Check operating structure
    for path in OPERATING_STRUCTURE:
        exists = (ROOT / path).exists()
        entry = {"path": path, "exists": exists}
        result["operating_structure"].append(entry)
        if not exists:
            result["missing_operating_structure"].append(path)

    if result["blockers"]:
        result["safe_to_proceed"] = False

    return result


def write_reports(result: dict) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "docs" / "reports" / "evidence"
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / f"daily_engine_prerequisite_check_{ts}.md"
    json_path = out_dir / f"daily_engine_prerequisite_check_{ts}.json"

    runners_found = [r for r in result["runners"] if r["exists"]]
    runners_missing = [r for r in result["runners"] if not r["exists"]]
    struct_ok = [s for s in result["operating_structure"] if s["exists"]]
    struct_missing = result["missing_operating_structure"]

    plist_ok = [w for w in result["launchd_workers"] if w["plist_exists"]]

    md = [
        "# Daily Engine Prerequisite Check",
        f"*{result['checked_at'][:16]} UTC*",
        "",
        f"**Safe to proceed:** {'✅ Yes' if result['safe_to_proceed'] else '❌ No — see blockers'}",
        "",
        "## Existing Runners Found",
        "",
    ]
    for r in runners_found:
        md.append(f"- ✅ `{r['path']}` — {r['label']} → **{r['action']}**")
    if runners_missing:
        md.append("")
        md.append("## Missing Runners")
        for r in runners_missing:
            md.append(f"- ⚠️ `{r['path']}` — {r['label']} (daily engine will skip/fallback)")

    md += [
        "",
        "## Operating Structure",
        "",
        f"**{len(struct_ok)}/{len(OPERATING_STRUCTURE)} files present**",
        "",
    ]
    for s in result["operating_structure"]:
        mark = "✅" if s["exists"] else "❌"
        md.append(f"- {mark} `{s['path']}`")

    md += [
        "",
        "## Active launchd Workers",
        "",
    ]
    for w in plist_ok:
        md.append(f"- ✅ `{w['label']}` — {w['description']}")

    md += [
        "",
        "## Must Not Duplicate",
        "",
    ]
    for p in result["must_not_duplicate"]:
        md.append(f"- `{p}`")

    if result["blockers"]:
        md += ["", "## Blockers", ""]
        for b in result["blockers"]:
            md.append(f"- ❌ {b}")

    md += [
        "",
        "## Summary",
        "",
        f"- Runners found: {len(runners_found)} / {len(EXISTING_RUNNERS)}",
        f"- Operating structure complete: {len(struct_ok)}/{len(OPERATING_STRUCTURE)}",
        f"- Missing operating structure: {struct_missing or 'none'}",
        f"- Telegram can send: {[t['label'] for t in result['telegram_can_send'] if t['can_send']]}",
        f"- Blockers: {len(result['blockers'])}",
    ]

    md_path.write_text("\n".join(md))
    json_path.write_text(json.dumps(result, indent=2))
    return md_path, json_path


if __name__ == "__main__":
    result = check_all()
    md_path, json_path = write_reports(result)

    runners_found = sum(1 for r in result["runners"] if r["exists"])
    struct_ok = sum(1 for s in result["operating_structure"] if s["exists"])

    print(f"=== Daily Engine Prerequisite Check ===")
    print(f"Runners found:        {runners_found}/{len(EXISTING_RUNNERS)}")
    print(f"Operating structure:  {struct_ok}/{len(OPERATING_STRUCTURE)}")
    print(f"Missing structure:    {result['missing_operating_structure'] or 'none'}")
    print(f"Blockers:             {len(result['blockers'])}")
    print(f"Safe to proceed:      {'✅ Yes' if result['safe_to_proceed'] else '❌ No'}")
    print(f"Report: {md_path.relative_to(ROOT)}")
    sys.exit(0 if result["safe_to_proceed"] else 1)
