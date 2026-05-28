"""
register_existing_artifacts.py
================================
Backfill the nexus_artifact_registry.jsonl with all existing artifacts found in the
docs/reports/ tree that are not yet registered.

Safe to run multiple times — uses file-path deduplication.

Usage:
  python scripts/register_existing_artifacts.py
  python scripts/register_existing_artifacts.py --dry-run
  python scripts/register_existing_artifacts.py --dir docs/reports/youtube
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCAN_DIRS = [
    "docs/reports/youtube",
    "docs/reports/github_trends",
    "docs/reports/evidence",
    "docs/reports/scout_dispatch",
    "docs/reports/agent_handoffs",
    "docs/reports/intake",
    "docs/reports/hermes_handoffs",
    "docs/reports/hermes_decisions",
    "docs",
]

REGISTRY_PATH = ROOT / "docs" / "reports" / "artifact_registry" / "nexus_artifact_registry.jsonl"

# Map file patterns to (artifact_type, agent_name)
PATTERN_MAP: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"youtube_intelligence_report"),     "report",       "youtube_intelligence_extractor"),
    (re.compile(r"content_intelligence_"),           "report",       "youtube_intelligence_extractor"),
    (re.compile(r"monetization_intelligence_"),      "report",       "youtube_intelligence_extractor"),
    (re.compile(r"nexus_improvement_intelligence_"), "report",       "youtube_intelligence_extractor"),
    (re.compile(r"compliance_intelligence_"),        "report",       "youtube_intelligence_extractor"),
    (re.compile(r"quality_review_"),                 "report",       "youtube_quality_reviewer"),
    (re.compile(r"youtube_source_reconciliation"),   "report",       "youtube_reconciliation"),
    (re.compile(r"aionui_system_improvement"),       "report",       "hermes_agent_handoff_builder"),
    (re.compile(r"github_trending_research"),        "report",       "github_trend_researcher"),
    (re.compile(r"github_trending_recommendations"), "report",       "github_trend_researcher"),
    (re.compile(r"scout_dispatch_.*\.md"),           "prompt",       "hermes_scout_dispatcher"),
    (re.compile(r"agent_handoff_.*\.md"),            "prompt",       "hermes_agent_handoff_builder"),
    (re.compile(r"hermes_evidence_audit"),           "report",       "hermes_evidence_audit"),
    (re.compile(r"handoff_.*\.json"),                "report",       "hermes"),
    (re.compile(r"hermes_decision_log"),             "report",       "hermes"),
    (re.compile(r"hermes_proactive_notifications"),  "notification", "hermes_proactive_notifier"),
    (re.compile(r"FUNCTIONALITY_AUDIT"),             "report",       "hermes"),
]


def _load_registered_paths() -> set[str]:
    if not REGISTRY_PATH.exists():
        return set()
    paths = set()
    for line in REGISTRY_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                d = json.loads(line)
                fp = d.get("file_path", "")
                if fp:
                    paths.add(fp)
                    paths.add(str(Path(fp).resolve()))
            except Exception:
                pass
    return paths


def _classify(path: Path) -> tuple[str, str]:
    name = path.name
    for pat, artifact_type, agent_name in PATTERN_MAP:
        if pat.search(name):
            return artifact_type, agent_name
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "report", "hermes"
    if suffix == ".json":
        return "report", "hermes"
    if suffix == ".jsonl":
        return "report", "hermes"
    return "other", "hermes"


def _extract_source_url(path: Path) -> str:
    try:
        text = path.read_text(errors="ignore")
        m = re.search(r'https?://[^\s\)\]"\']+', text)
        if m:
            return m.group(0)[:300]
    except Exception:
        pass
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill artifact registry")
    parser.add_argument("--dry-run", action="store_true", help="Preview only — no writes")
    parser.add_argument("--dir", default="", help="Scan only this subdirectory (relative to ROOT)")
    args = parser.parse_args()

    dry_run = args.dry_run

    if dry_run:
        print("DRY RUN — no writes will occur")
    print(f"Registry: {REGISTRY_PATH}")

    registered_paths = _load_registered_paths()
    print(f"Already registered: {len(registered_paths)} paths")

    try:
        from lib.nexus_artifact_registry import register_artifact
    except ImportError as e:
        print(f"ERROR: Cannot import register_artifact: {e}")
        sys.exit(1)

    scan_dirs = [args.dir] if args.dir else SCAN_DIRS
    candidates: list[Path] = []
    for d in scan_dirs:
        full = ROOT / d
        if not full.exists():
            continue
        for ext in ("*.md", "*.json"):
            for p in full.rglob(ext):
                if "nexus_artifact_registry" in p.name:
                    continue
                if p.stat().st_size == 0:
                    continue
                candidates.append(p)

    candidates = sorted(set(candidates), key=lambda p: p.stat().st_mtime)
    print(f"Candidate files found: {len(candidates)}")

    registered  = 0
    skipped     = 0
    errors      = 0

    for path in candidates:
        abs_str = str(path.resolve())
        rel_str = str(path)
        if abs_str in registered_paths or rel_str in registered_paths:
            skipped += 1
            continue

        artifact_type, agent_name = _classify(path)
        source_url = _extract_source_url(path)
        title = path.stem.replace("_", " ")[:80]

        print(f"  {'[DRY] ' if dry_run else ''}Registering [{artifact_type}] {path.name}")

        if not dry_run:
            try:
                register_artifact(
                    agent_name=agent_name,
                    agent_type="hermes",
                    source_input=source_url,
                    source_type="other",
                    artifact_type=artifact_type,
                    title=title,
                    summary=f"Backfilled from {path.relative_to(ROOT)}",
                    file_path=str(path),
                    tags=["backfill"],
                    what_hermes_should_know=f"Existing artifact registered via backfill: {path.name}",
                    next_action="",
                )
                registered += 1
            except Exception as e:
                print(f"    ERROR: {e}")
                errors += 1
        else:
            registered += 1

    print(f"\n{'DRY RUN ' if dry_run else ''}Results:")
    print(f"  Registered: {registered}")
    print(f"  Skipped (already registered): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Registry: {REGISTRY_PATH}")

    if dry_run:
        print("\nRun without --dry-run to apply.")


if __name__ == "__main__":
    main()
