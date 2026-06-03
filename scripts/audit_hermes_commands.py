#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict

from audit_hermes_common import (
    AUDIT_DIR,
    CommandEntry,
    ROOT,
    ensure_audit_dir,
    extract_continuity_entries,
    extract_intent_entries,
    extract_paths_and_tables,
    extract_plain_intent_handlers,
    extract_shadow_command_entries,
    first_header,
    likely_duplicate,
    normalize_category,
    now_timestamp,
    rel,
    risk_level,
    safe_bot,
    uses_old_report_wrapper,
    write_json,
    write_md,
)


def build_inventory() -> list[CommandEntry]:
    plain_handlers = extract_plain_intent_handlers()
    intake_entries = extract_intent_entries()
    continuity_entries = extract_continuity_entries()
    shadow_entries = extract_shadow_command_entries()

    phrase_set = {item["phrase"].lower().strip().rstrip(".?!") for item in intake_entries}
    inventory: list[CommandEntry] = []

    for item in intake_entries:
        intent = item["intent"]
        file_path = "hermes_command_router/router.py" if intent in plain_handlers else "hermes_command_router/intake.py"
        handler = plain_handlers.get(intent, "run_command -> build_report/model path")
        io_info = extract_paths_and_tables((ROOT / file_path))
        inventory.append(CommandEntry(
            category=normalize_category(intent),
            phrase=item["phrase"],
            normalized_intent=intent,
            handler=handler,
            file_path=file_path,
            output_header="",
            read_sources=io_info["file_paths"] + io_info["tables"],
            write_targets=io_info["file_paths"] if io_info["write_tokens"] else [],
            safety_risk_level=risk_level(item["phrase"], item["requires_approval"]),
            approval_required=item["requires_approval"],
            command_style="natural-language intent",
            active_in_live_telegram=True,
            shadow_only=False,
            duplicate_or_overlapping=likely_duplicate(item["phrase"], phrase_set),
            old_report_wrapper=uses_old_report_wrapper(intent),
        ))

    for item in continuity_entries:
        inventory.append(CommandEntry(
            category=normalize_category(item["phrase"]),
            phrase=item["phrase"],
            normalized_intent="telegram_continuity_exact",
            handler=item["handler_expr"],
            file_path="telegram_bot.py",
            output_header="",
            read_sources=[],
            write_targets=[],
            safety_risk_level=risk_level(item["phrase"]),
            approval_required=False,
            command_style="exact command",
            active_in_live_telegram=True,
            shadow_only=False,
            duplicate_or_overlapping=likely_duplicate(item["phrase"], phrase_set),
            old_report_wrapper=False,
        ))

    for item in shadow_entries:
        inventory.append(CommandEntry(
            category="shadow/primary mode",
            phrase=item["phrase"],
            normalized_intent="cfo_shadow_command",
            handler=item["handler_expr"],
            file_path="lib/hermes_cfo_loop_shadow.py",
            output_header="",
            read_sources=["docs/reports/strategy/shadow/hermes_cfo_loop_shadow_traces.jsonl"],
            write_targets=["docs/reports/strategy/shadow/hermes_cfo_loop_shadow_traces.jsonl"] if "clear" in item["phrase"] else [],
            safety_risk_level="low",
            approval_required=False,
            command_style="exact command",
            active_in_live_telegram=True,
            shadow_only="shadow" in item["phrase"] and "limited primary" not in item["phrase"],
            duplicate_or_overlapping=False,
            old_report_wrapper=False,
        ))

    deduped: dict[tuple[str, str], CommandEntry] = {}
    for entry in inventory:
        key = (entry.phrase.lower(), entry.handler)
        deduped[key] = entry
    return list(deduped.values())


def is_safe_to_test(entry: CommandEntry) -> tuple[bool, str]:
    phrase = entry.phrase.lower()
    safe_intents = {
        "date_time_question",
        "show_last_daily_plan",
        "daily_operating_cycle",
        "show_approval_queue",
        "daily_continue_while_out",
        "thirty_day_revenue_plan",
        "daily_top_revenue_move",
        "daily_blockers",
        "while_out_summary",
        "pending_daily_items",
        "compare_since_last_plan",
        "approval_impact",
        "show_research_queue",
        "show_scout_assignments",
        "show_unresolved_questions",
        "memory_v2_preview",
        "memory_v2_status",
        "memory_v2_primary_status",
        "memory_v2_shadow_status",
        "memory_v2_live_check",
        "memory_sources",
        "memory_sources_again",
        "answer_source",
        "active_operating_rules",
    }
    safe_exact_phrases = {
        "show cfo shadow status",
        "show cfo loop mode",
        "show cfo shadow traces",
        "compare cfo shadow",
        "show cfo limited primary status",
        "show cfo primary status",
        "rollback cfo loop to shadow",
        "show action queue",
        "show decision log",
        "show approval policy",
        "what changed",
        "show memory v2 primary status",
    }
    if entry.approval_required:
        return False, "approval-required"
    if any(word in phrase for word in [
        "approve item", "reject item", "mark ", "clear stale", "save ", "record ",
        "create ", "build ", "fix ", "improve ", "dedupe ", "run qa", "run test agent",
        "send ", "deploy", "publish", "email", "affiliate", "stripe", "payment", "trade"
    ]):
        return False, "write-or-unsafe-capable"
    if "report_request" in entry.normalized_intent or "knowledge_report" in entry.normalized_intent:
        return False, "email/report path"
    if entry.category in {"fallback/help/small talk"}:
        return False, "not useful for deterministic audit"
    if entry.normalized_intent == "cfo_shadow_command":
        return (phrase in safe_exact_phrases, "not in safe exact whitelist" if phrase not in safe_exact_phrases else "")
    if entry.file_path == "telegram_bot.py":
        return (phrase in safe_exact_phrases, "telegram exact not in safe whitelist" if phrase not in safe_exact_phrases else "")
    if entry.normalized_intent not in safe_intents:
        return False, "intent outside safe deterministic whitelist"
    safe_prefixes = (
        "show ", "what ", "which ", "is ", "are ", "compare ", "why ",
        "where ", "review ", "rollback cfo", "cfo ", "memory v2 ",
        "hermes, run daily operating cycle", "daily operating cycle",
    )
    if entry.command_style == "exact command" and not phrase.startswith(safe_prefixes):
        return False, "exact command outside deterministic audit scope"
    return True, ""


def run_entry(entry: CommandEntry) -> dict:
    from hermes_command_router.router import run_command
    from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command

    os.environ.setdefault("HERMES_CFO_LOOP_MODE", "limited_primary")
    os.environ.setdefault("HERMES_CFO_LOOP_PROVIDER", "mock")
    phrase = entry.phrase
    response = ""
    if entry.normalized_intent == "cfo_shadow_command":
        response = handle_cfo_shadow_command(phrase) or ""
    elif entry.file_path == "telegram_bot.py":
        response = safe_bot().handle_inbound_message(phrase)
    elif entry.file_path == "hermes_command_router/router.py":
        response = run_command(phrase, source="audit")
    else:
        response = run_command(phrase, source="audit")
    lower = response.lower()
    return {
        "phrase": phrase,
        "intent": entry.normalized_intent,
        "handler": entry.handler,
        "output_header": first_header(response),
        "passed": bool(response),
        "evidence_dump": "artifact_inventory" in lower or "i can answer from verified artifacts" in lower,
        "quality_fallback": "i wasn't able to generate a quality response" in lower,
        "mock_output": "based on mock data" in lower or "research_scout_1" in lower,
        "response_preview": response[:240],
    }


def main() -> int:
    ensure_audit_dir()
    timestamp = now_timestamp()
    inventory = build_inventory()
    by_phrase = defaultdict(list)
    for entry in inventory:
        by_phrase[entry.phrase.lower()].append(entry)

    safe_results = []
    skipped = []
    tested_intents: set[str] = set()
    for entry in inventory:
        okay, reason = is_safe_to_test(entry)
        if not okay:
            skipped.append({"phrase": entry.phrase, "intent": entry.normalized_intent, "reason": reason})
            continue
        if entry.normalized_intent in tested_intents and entry.command_style != "exact command":
            skipped.append({"phrase": entry.phrase, "intent": entry.normalized_intent, "reason": "duplicate intent coverage"})
            continue
        try:
            safe_results.append(run_entry(entry))
            tested_intents.add(entry.normalized_intent)
        except Exception as exc:
            safe_results.append({
                "phrase": entry.phrase,
                "intent": entry.normalized_intent,
                "handler": entry.handler,
                "output_header": "",
                "passed": False,
                "evidence_dump": False,
                "quality_fallback": False,
                "mock_output": False,
                "response_preview": f"ERROR: {exc}",
            })

    header_map = {item["phrase"]: item["output_header"] for item in safe_results if item["output_header"]}
    command_rows = []
    table_rows = [["Command", "What it does", "Safe?", "Writes?", "Approval needed?"]]
    for entry in sorted(inventory, key=lambda x: (x.category, x.phrase.lower())):
        entry.output_header = header_map.get(entry.phrase, "")
        command_rows.append(entry.__dict__)
        table_rows.append([
            entry.phrase,
            entry.normalized_intent,
            "yes" if is_safe_to_test(entry)[0] else "no",
            "yes" if entry.write_targets else "no",
            "yes" if entry.approval_required else "no",
        ])

    inventory_json = {
        "timestamp": timestamp,
        "commands": command_rows,
        "summary": {
            "total_commands": len(inventory),
            "categories": sorted({entry.category for entry in inventory}),
        },
    }
    inventory_md = ["# Hermes Command Inventory", "", f"Timestamp: {timestamp}", ""]
    current_category = None
    for entry in sorted(inventory, key=lambda x: (x.category, x.phrase.lower())):
        if entry.category != current_category:
            current_category = entry.category
            inventory_md += [f"## {current_category}", ""]
        inventory_md += [
            f"### {entry.phrase}",
            f"- normalized intent: {entry.normalized_intent}",
            f"- handler: {entry.handler}",
            f"- file path: {entry.file_path}",
            f"- output header: {header_map.get(entry.phrase, '(not executed)')}",
            f"- read sources: {', '.join(entry.read_sources) or 'unknown'}",
            f"- write targets: {', '.join(entry.write_targets) or 'none'}",
            f"- safety risk level: {entry.safety_risk_level}",
            f"- approval required: {entry.approval_required}",
            f"- command style: {entry.command_style}",
            f"- active in live Telegram: {entry.active_in_live_telegram}",
            f"- shadow only: {entry.shadow_only}",
            f"- duplicate/overlapping: {entry.duplicate_or_overlapping}",
            f"- old report wrapper: {entry.old_report_wrapper}",
            "",
        ]
    inventory_md += ["## Simple Table", "", "\n".join(" | ".join(row) for row in table_rows)]
    write_json(AUDIT_DIR / f"hermes_command_inventory_{timestamp}.json", inventory_json)
    write_md(AUDIT_DIR / f"hermes_command_inventory_{timestamp}.md", "\n".join(inventory_md))

    failing = [item for item in safe_results if not item["passed"]]
    command_test_json = {
        "timestamp": timestamp,
        "summary": {
            "total_commands_found": len(inventory),
            "commands_tested": len(safe_results),
            "commands_skipped": len(skipped),
            "commands_passing": sum(1 for item in safe_results if item["passed"]),
            "commands_failing": len(failing),
            "commands_producing_evidence_dump": sum(1 for item in safe_results if item["evidence_dump"]),
            "commands_producing_quality_fallback": sum(1 for item in safe_results if item["quality_fallback"]),
            "duplicate_commands": sum(1 for entries in by_phrase.values() if len(entries) > 1),
            "orphaned_intents": [],
            "missing_handlers": [item["phrase"] for item in safe_results if "ERROR" in item["response_preview"]],
            "handlers_with_no_phrases": [],
            "phrases_with_no_handlers": [],
        },
        "tested": safe_results,
        "skipped": skipped,
        "supabase_write_attempted": False,
    }
    command_test_md = [
        "# Hermes Command Test Results",
        "",
        f"Timestamp: {timestamp}",
        "",
        f"- total commands found: {command_test_json['summary']['total_commands_found']}",
        f"- commands tested: {command_test_json['summary']['commands_tested']}",
        f"- commands skipped: {command_test_json['summary']['commands_skipped']}",
        f"- commands passing: {command_test_json['summary']['commands_passing']}",
        f"- commands failing: {command_test_json['summary']['commands_failing']}",
        f"- commands producing evidence dump: {command_test_json['summary']['commands_producing_evidence_dump']}",
        f"- commands producing quality fallback: {command_test_json['summary']['commands_producing_quality_fallback']}",
        "",
        "## Tested Commands",
        "",
    ]
    for item in safe_results:
        command_test_md += [
            f"### {item['phrase']}",
            f"- intent: {item['intent']}",
            f"- handler: {item['handler']}",
            f"- output header: {item['output_header'] or '(none)'}",
            f"- passed: {item['passed']}",
            f"- evidence dump: {item['evidence_dump']}",
            f"- quality fallback: {item['quality_fallback']}",
            f"- mock output: {item['mock_output']}",
            f"- preview: {item['response_preview']}",
            "",
        ]
    command_test_md += ["## Skipped Commands", ""]
    for item in skipped[:200]:
        command_test_md.append(f"- {item['phrase']} ({item['intent']}): {item['reason']}")
    write_json(AUDIT_DIR / f"hermes_command_test_results_{timestamp}.json", command_test_json)
    write_md(AUDIT_DIR / f"hermes_command_test_results_{timestamp}.md", "\n".join(command_test_md))

    print(json.dumps({
        "timestamp": timestamp,
        "inventory_count": len(inventory),
        "tested": len(safe_results),
        "skipped": len(skipped),
        "supabase_write_attempted": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
