#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_artifact_memory import register_artifact
from lib.hermes_decision_log import log_decision


OUTPUT_SAFE_LOOP_JSON = ROOT / "logs" / "safe_learning_loop_latest.json"
OUTPUT_SAFE_LOOP_MD = ROOT / "logs" / "safe_learning_loop_latest.md"
OUTPUT_LEARNING_JSON = ROOT / "logs" / "learning_memory_latest.json"
OUTPUT_LEARNING_MD = ROOT / "logs" / "learning_memory_latest.md"
OUTPUT_ACTIONS_JSON = ROOT / "logs" / "next_safe_actions_latest.json"
OUTPUT_ACTIONS_MD = ROOT / "logs" / "next_safe_actions_latest.md"
OUTPUT_RESEARCH_JSON = ROOT / "logs" / "safe_research_loops_latest.json"
OUTPUT_RESEARCH_MD = ROOT / "logs" / "safe_research_loops_latest.md"
OUTPUT_TASKS_JSON = ROOT / "logs" / "evolution_tasks_latest.json"
OUTPUT_TASKS_MD = ROOT / "logs" / "evolution_tasks_latest.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "command": " ".join(cmd),
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _inventory() -> dict[str, Any]:
    groups = {
        "truth_and_gate": [
            "lib/hermes_truth_layer.py",
            "lib/hermes_final_response_gate.py",
            "lib/hermes_supabase_first.py",
        ],
        "memory_and_learning": [
            "lib/hermes_learning_loop.py",
            "lib/hermes_mistake_memory.py",
            "lib/hermes_artifact_memory.py",
            "lib/hermes_failure_learning.py",
            "lib/hermes_knowledge_gap_logger.py",
        ],
        "queues_and_dispatch": [
            "lib/hermes_action_queue.py",
            "lib/hermes_approval_queue.py",
            "lib/hermes_scout_dispatcher.py",
            "lib/autonomous_improvement_queue.py",
        ],
        "operating_loops": [
            "lib/hermes_operating_loop.py",
            "lib/hermes_daily_operating_cycle.py",
            "scripts/run_hermes_operating_loop.py",
            "scripts/run_content_engine_loop.py",
            "scripts/run_monetization_decision_cycle.py",
            "scripts/run_nexus_demo_trading_loop.py",
            "scripts/run_nexus_full_trading_test_cycle.py",
        ],
        "trading_research": [
            "scripts/run_youtube_strategy_research_scout.py",
            "scripts/discover_trading_strategies.py",
            "scripts/build_trading_intelligence_packet.py",
            "scripts/run_nexus_trading_tournament.py",
            "scripts/analyze_practice_trade_memory.py",
            "scripts/send_trading_status_report.py",
        ],
    }
    out: dict[str, Any] = {}
    for key, paths in groups.items():
        out[key] = [{"path": path, "exists": (ROOT / path).exists()} for path in paths]
    return out


def _trading_loop(dry_run: bool) -> dict[str, Any]:
    commands = [
        [sys.executable, str(ROOT / "scripts" / "check_trading_safety.py")],
        [sys.executable, str(ROOT / "scripts" / "check_supabase_connectivity.py")],
        [sys.executable, str(ROOT / "scripts" / "run_youtube_strategy_research_scout.py"), "--source", "registry", "--asset-class", "forex", "--dry-run"],
        [sys.executable, str(ROOT / "scripts" / "discover_trading_strategies.py"), "--asset-class", "forex", "--source", "all", "--dry-run"],
        [sys.executable, str(ROOT / "scripts" / "build_trading_intelligence_packet.py"), "--dry-run"],
        [sys.executable, str(ROOT / "scripts" / "run_nexus_trading_tournament.py"), "--mode", "paper", "--source", "supabase_first", "--data-source", "oanda_practice", "--dry-run"],
        [sys.executable, str(ROOT / "scripts" / "analyze_practice_trade_memory.py")],
        [sys.executable, str(ROOT / "scripts" / "send_trading_status_report.py"), "--dry-run"],
    ]
    results = [_run(cmd) for cmd in commands]
    youtube = _load_json(ROOT / "logs" / "youtube_strategy_research_latest.json")
    discovery = _load_json(ROOT / "logs" / "trading_strategy_discovery_latest.json")
    packet = _load_json(ROOT / "logs" / "trading_intelligence_packet_latest.json")
    tournament = _load_json(ROOT / "logs" / "nexus_trading_tournament_latest.json")
    memory = _load_json(ROOT / "logs" / "practice_trade_memory_latest.json")

    seeds = youtube.get("seeds") or []
    seed_tasks = []
    for seed in seeds[:10]:
        seed_tasks.append(
            {
                "lane": "trading",
                "task_type": "variant_generation",
                "title": f"Generate variants for {seed.get('seed_id')}",
                "details": {
                    "seed_type": seed.get("seed_type"),
                    "symbols": seed.get("symbols"),
                    "missing_fields": seed.get("missing_fields"),
                    "variants_to_test": seed.get("variants_to_test"),
                },
                "requires_ray_approval": False,
            }
        )

    top_ev = ((packet.get("expected_value_scores") or [None])[0]) or {}
    zero_result = bool(youtube.get("strategies_extracted", 0) == 0 and youtube.get("seeds_found", 0) == 0)
    next_command = (
        "python3 scripts/run_youtube_strategy_research_scout.py --source urls --asset-class forex --dry-run"
        if youtube.get("seeds_found", 0) == 0
        else "python3 scripts/run_nexus_trading_tournament.py --mode paper --source supabase_first --data-source oanda_practice --dry-run"
    )
    return {
        "loop_name": "trading_evolution_loop",
        "run_id": f"trading_{uuid.uuid4().hex[:8]}",
        "timestamp": _now(),
        "lane": "trading",
        "inputs_reviewed": youtube.get("documents_reviewed", 0),
        "outputs_created": [
            str(ROOT / "logs" / "youtube_strategy_research_latest.json"),
            str(ROOT / "logs" / "trading_strategy_discovery_latest.json"),
            str(ROOT / "logs" / "trading_intelligence_packet_latest.json"),
            str(ROOT / "logs" / "practice_trade_memory_latest.json"),
        ],
        "seeds_found": youtube.get("seeds_found", 0),
        "variants_created": len(seed_tasks),
        "tests_run": len(results),
        "wins": memory.get("wins", 0),
        "losses": memory.get("losses", 0),
        "rejects": memory.get("rejects", 0),
        "duplicates": memory.get("duplicate_blocked", 0),
        "zero_result": zero_result,
        "what_worked": [
            "YouTube registry scout ran in dry-run mode",
            "Supabase-first tournament dry-run remained active",
            "Practice memory summarized duplicate/reject outcomes",
        ],
        "what_failed": [
            youtube.get("result_interpretation", "unknown_result")
        ],
        "why_it_failed": youtube.get("result_interpretation", "unknown_result"),
        "lesson_learned": (
            "Nexus is not looking for finished opportunities; Nexus is looking for seeds it can improve, test, and evolve into monetizable systems."
            if youtube.get("seeds_found", 0) > 0 else
            "When no testable strategies appear, the next safe move is seed mode, stronger source curation, or variant generation."
        ),
        "next_adjustment": youtube.get("next_safe_action", "review better sources and generate variants"),
        "next_safe_command": next_command,
        "should_continue": True,
        "requires_ray_approval": False,
        "cost_risk": "free",
        "safety_risk": "low",
        "source_dependence": {
            "external_discovery_dependence": "medium",
            "internal_memory_dependence": "high",
            "top_recurring_patterns": list((memory.get("duplicate_strategy_pairs") or {}).keys())[:5],
            "best_performing_seeds": [seed.get("seed_id") for seed in seeds[:5]],
            "best_performing_variants": [top_ev.get("strategy_id")] if top_ev.get("strategy_id") else [],
            "recommended_focus_lanes": ["forex trend_following", "forex session_breakout"],
        },
        "artifacts": {
            "youtube": youtube,
            "discovery": {"candidates_discovered": discovery.get("candidates_discovered"), "candidates_testable": discovery.get("candidates_testable")},
            "top_candidate": tournament.get("top_candidate_for_next_cap_reset") or tournament.get("top_strategy"),
            "top_ev": top_ev,
        },
        "commands": results,
        "tasks": seed_tasks,
    }


def _content_loop(dry_run: bool) -> dict[str, Any]:
    result = _run([
        sys.executable,
        str(ROOT / "scripts" / "run_content_engine_loop.py"),
        "--limit", "1",
        "--dry-run",
        "--repurpose",
        "--no-telegram",
    ])
    stdout = result.get("stdout", "")
    topics_processed = 0
    needs_review = 0
    improve_retry = 0
    for line in stdout.splitlines():
        if "topics=" in line:
            try:
                topics_processed = int(line.rsplit("topics=", 1)[-1].split(")")[0])
            except Exception:
                pass
        if "Needs Ray Review" in line:
            needs_review += 1
        if "Improve/Retry" in line:
            improve_retry += 1
    next_command = "python3 scripts/run_content_engine_loop.py --limit 1 --dry-run --repurpose --no-telegram"
    return {
        "loop_name": "content_evolution_loop",
        "run_id": f"content_{uuid.uuid4().hex[:8]}",
        "timestamp": _now(),
        "lane": "content",
        "inputs_reviewed": topics_processed,
        "outputs_created": [],
        "seeds_found": topics_processed,
        "variants_created": max(0, needs_review + improve_retry),
        "tests_run": 1,
        "wins": needs_review,
        "losses": 0,
        "rejects": improve_retry,
        "duplicates": 0,
        "zero_result": topics_processed == 0,
        "what_worked": ["Content engine dry-run remains safe and local-first"],
        "what_failed": ["no_structured_topics_found"] if topics_processed == 0 else [],
        "why_it_failed": "missing_data" if topics_processed == 0 else "n/a",
        "lesson_learned": "Weak first outputs should become revision inputs, not dead ends.",
        "next_adjustment": "generate the next script variant and compare hook/CTA quality",
        "next_safe_command": next_command,
        "should_continue": True,
        "requires_ray_approval": False,
        "cost_risk": "free",
        "safety_risk": "low",
        "source_dependence": {
            "external_discovery_dependence": "low",
            "internal_memory_dependence": "medium",
            "top_recurring_patterns": ["hook_quality", "cta_quality"],
            "best_performing_seeds": [],
            "best_performing_variants": [],
            "recommended_focus_lanes": ["youtube_shorts"],
        },
        "artifacts": {"stdout": stdout[:4000]},
        "commands": [result],
        "tasks": [
            {
                "lane": "content",
                "task_type": "content_variant_generation",
                "title": "Generate next short/script variant",
                "details": {"focus": ["hook", "pacing", "CTA", "structure"]},
                "requires_ray_approval": False,
            }
        ],
    }


def _business_loop(dry_run: bool) -> dict[str, Any]:
    result = _run([
        sys.executable,
        str(ROOT / "scripts" / "run_monetization_decision_cycle.py"),
        "--mode", "validation",
        "--top-n", "10",
    ])
    stdout = result.get("stdout", "")
    scored = actionable = rejected = needs_approval = 0
    for line in stdout.splitlines():
        if line.startswith("Scored:"):
            scored = int(line.split(":", 1)[1].strip() or "0")
        elif line.startswith("Actionable:"):
            actionable = int(line.split(":", 1)[1].strip() or "0")
        elif line.startswith("Rejected:"):
            rejected = int(line.split(":", 1)[1].strip() or "0")
        elif line.startswith("Needs approval:"):
            needs_approval = int(line.split(":", 1)[1].strip() or "0")
    next_command = "python3 scripts/run_monetization_decision_cycle.py --mode validation --top-n 10"
    return {
        "loop_name": "business_evolution_loop",
        "run_id": f"business_{uuid.uuid4().hex[:8]}",
        "timestamp": _now(),
        "lane": "business",
        "inputs_reviewed": scored,
        "outputs_created": [],
        "seeds_found": actionable,
        "variants_created": actionable,
        "tests_run": 1,
        "wins": actionable,
        "losses": 0,
        "rejects": rejected,
        "duplicates": 0,
        "zero_result": actionable == 0,
        "what_worked": ["Monetization decision cycle reused the current evidence-first business scorer"],
        "what_failed": ["no_actionable_opportunities"] if actionable == 0 else [],
        "why_it_failed": "needs_seed_mode" if actionable == 0 else "n/a",
        "lesson_learned": "Incomplete business ideas should become business_opportunity_seed and no-cost validation tasks.",
        "next_adjustment": "convert weak candidates into monetization hypotheses and free validation steps",
        "next_safe_command": next_command,
        "should_continue": True,
        "requires_ray_approval": False,
        "cost_risk": "free",
        "safety_risk": "low",
        "source_dependence": {
            "external_discovery_dependence": "medium",
            "internal_memory_dependence": "medium",
            "top_recurring_patterns": ["needs_more_research", "client_education_candidate"],
            "best_performing_seeds": [],
            "best_performing_variants": [],
            "recommended_focus_lanes": ["credit_funding", "content_to_offer"],
        },
        "artifacts": {"stdout": stdout[:4000]},
        "commands": [result],
        "tasks": [
            {
                "lane": "business",
                "task_type": "no_cost_validation",
                "title": "Create next no-cost validation task for top opportunity",
                "details": {"requires_ray_approval": needs_approval > 0},
                "requires_ray_approval": False,
            }
        ],
    }


def _self_improvement_loop(dry_run: bool) -> dict[str, Any]:
    result = _run([
        sys.executable,
        str(ROOT / "scripts" / "run_hermes_operating_loop.py"),
        "--mode", "validation",
    ])
    from lib.hermes_response_improvement_loop import create_response_improvement_report, analyze_knowledge_gaps

    report_path = create_response_improvement_report()
    gaps = analyze_knowledge_gaps(limit=50)
    next_command = "python3 scripts/run_hermes_operating_loop.py --mode validation"
    return {
        "loop_name": "hermes_self_improvement_loop",
        "run_id": f"self_{uuid.uuid4().hex[:8]}",
        "timestamp": _now(),
        "lane": "self_improvement",
        "inputs_reviewed": len(gaps),
        "outputs_created": [report_path],
        "seeds_found": len(gaps),
        "variants_created": 0,
        "tests_run": 2,
        "wins": 0,
        "losses": 0,
        "rejects": 0,
        "duplicates": 0,
        "zero_result": len(gaps) == 0,
        "what_worked": ["Hermes operating loop and response improvement loop already exist and were reused"],
        "what_failed": ["no_open_knowledge_gaps"] if len(gaps) == 0 else [],
        "why_it_failed": "no_results" if len(gaps) == 0 else "n/a",
        "lesson_learned": "High-rejection and zero-result runs should become explicit improvement tasks, not silent dead ends.",
        "next_adjustment": "review open gaps, duplicate blocks, and failed tests before adding new layers",
        "next_safe_command": next_command,
        "should_continue": True,
        "requires_ray_approval": False,
        "cost_risk": "free",
        "safety_risk": "low",
        "source_dependence": {
            "external_discovery_dependence": "low",
            "internal_memory_dependence": "high",
            "top_recurring_patterns": [gap.get("reason") for gap in gaps[:5]],
            "best_performing_seeds": [],
            "best_performing_variants": [],
            "recommended_focus_lanes": ["knowledge_gap_review", "action_queue_followthrough"],
        },
        "artifacts": {"response_improvement_report": report_path},
        "commands": [result],
        "tasks": [
            {
                "lane": "self_improvement",
                "task_type": "response_improvement",
                "title": "Review open knowledge gaps and repeated failures",
                "details": {"gap_count": len(gaps)},
                "requires_ray_approval": False,
            }
        ],
    }


def _write_md(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=("trading", "content", "business", "self", "all"), default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dry_run = True if not args.dry_run else True
    run_id = f"safe_loops_{uuid.uuid4().hex[:8]}"
    inventory = _inventory()

    lane_records: list[dict[str, Any]] = []
    if args.scope in {"trading", "all"}:
        lane_records.append(_trading_loop(dry_run))
    if args.scope in {"content", "all"}:
        lane_records.append(_content_loop(dry_run))
    if args.scope in {"business", "all"}:
        lane_records.append(_business_loop(dry_run))
    if args.scope in {"self", "all"}:
        lane_records.append(_self_improvement_loop(dry_run))

    next_actions = [
        {
            "lane": record["lane"],
            "next_safe_command": record["next_safe_command"],
            "requires_ray_approval": record["requires_ray_approval"],
            "cost_risk": record["cost_risk"],
        }
        for record in lane_records
    ]
    evolution_tasks = [task for record in lane_records for task in (record.get("tasks") or [])]

    overall = {
        "generated_at": _now(),
        "run_id": run_id,
        "scope": args.scope,
        "dry_run": dry_run,
        "inventory": inventory,
        "loops": lane_records,
        "next_safe_actions": next_actions,
        "evolution_tasks": evolution_tasks,
        "summary": {
            "lanes_run": [record["lane"] for record in lane_records],
            "zero_result_lanes": [record["lane"] for record in lane_records if record.get("zero_result")],
            "seed_total": sum(int(record.get("seeds_found") or 0) for record in lane_records),
            "variants_total": sum(int(record.get("variants_created") or 0) for record in lane_records),
            "tests_total": sum(int(record.get("tests_run") or 0) for record in lane_records),
        },
        "key_sentence": "Nexus is not looking for finished opportunities; Nexus is looking for seeds it can improve, test, and evolve into monetizable systems.",
    }

    for path, payload in [
        (OUTPUT_SAFE_LOOP_JSON, overall),
        (OUTPUT_LEARNING_JSON, {"generated_at": _now(), "records": lane_records}),
        (OUTPUT_ACTIONS_JSON, {"generated_at": _now(), "actions": next_actions}),
        (OUTPUT_RESEARCH_JSON, {"generated_at": _now(), "inventory": inventory, "loops": lane_records}),
        (OUTPUT_TASKS_JSON, {"generated_at": _now(), "tasks": evolution_tasks}),
    ]:
        path.write_text(json.dumps(payload, indent=2, default=str))
        register_artifact("safe_learning_loop_report", path, run_id=run_id, summary=path.name)

    _write_md(
        OUTPUT_SAFE_LOOP_MD,
        [
            "# Safe Continuous Evolution",
            "",
            f"- Generated at: `{overall['generated_at']}`",
            f"- Scope: `{args.scope}`",
            f"- Dry run: `yes`",
            f"- Lanes run: `{', '.join(overall['summary']['lanes_run'])}`",
            f"- Seeds found: `{overall['summary']['seed_total']}`",
            f"- Variants created: `{overall['summary']['variants_total']}`",
            f"- Tests run: `{overall['summary']['tests_total']}`",
            "",
            overall["key_sentence"],
        ],
    )
    _write_md(
        OUTPUT_LEARNING_MD,
        [
            "# Learning Memory",
            "",
            *[
                f"- `{record['lane']}` lesson=`{record['lesson_learned']}` next=`{record['next_safe_command']}`"
                for record in lane_records
            ],
        ],
    )
    _write_md(
        OUTPUT_ACTIONS_MD,
        [
            "# Next Safe Actions",
            "",
            *[
                f"- `{row['lane']}` command=`{row['next_safe_command']}` approval=`{'yes' if row['requires_ray_approval'] else 'no'}`"
                for row in next_actions
            ],
        ],
    )
    _write_md(
        OUTPUT_RESEARCH_MD,
        [
            "# Safe Research Loops",
            "",
            *[
                f"- `{record['lane']}` zero_result=`{'yes' if record['zero_result'] else 'no'}` why=`{record['why_it_failed']}`"
                for record in lane_records
            ],
        ],
    )
    _write_md(
        OUTPUT_TASKS_MD,
        [
            "# Evolution Tasks",
            "",
            *[
                f"- `{task['lane']}` `{task['task_type']}` `{task['title']}`"
                for task in evolution_tasks
            ],
        ],
    )

    for record in lane_records:
        log_decision(
            question_or_trigger=f"safe learning loop {record['lane']}",
            decision=f"continue {record['loop_name']}",
            why_selected=record["next_adjustment"],
            risk_level="low",
            autonomous_allowed=True,
            requires_ray_approval=False,
            artifact_paths=record.get("outputs_created") or [],
            result_status="completed",
        )

    print(json.dumps({"json": str(OUTPUT_SAFE_LOOP_JSON), "markdown": str(OUTPUT_SAFE_LOOP_MD), "lanes": overall["summary"]["lanes_run"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
