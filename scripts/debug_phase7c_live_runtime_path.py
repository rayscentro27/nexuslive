"""
debug_phase7c_live_runtime_path.py
Phase 7C: Live runtime path trace for Hermes Telegram routing.

Simulates the exact routing path for 10 key messages and reports:
- intake intent classification
- whether CFO Brain activates
- CFO intent
- whether conversation state resolves references
- option/task lookup result
- first 500 chars of response
- evidence/quality fallback detection
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "docs" / "reports" / "strategy"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
TS = datetime.now().strftime("%Y%m%d_%H%M%S")

EVIDENCE_DUMP_MARKERS = [
    "Live answer sources:", "Confidence: ", "Source 1:", "artifact_inventory",
    "handoff_state", "HERMES REPORT", "intelligence_division", "handoff",
]
GENERIC_FALLBACK_MARKERS = [
    "i wasn't able to generate", "quality response", "based on what i have available",
    "plain-language mode", "plain language mode enabled", "i wasn't fully sure",
]

TEST_MESSAGES = [
    ("HOW DO WE MAKE MONEY THIS WEEK", "how do we make money this week"),
    ("LETS DO 1",                      "lets do 1"),
    ("WHAT WAS TASK 1",                "what was task 1"),
    ("CAN YOU SIMPLIFY YOUR RESPONSE", "can you simplify your response"),
    ("EXPLAIN YOUR RECOMMENDATION IN PLAIN LANGUAGE", "explain your recommendation in plain language"),
    ("WHAT DID YOU DO THIS MORNING",   "what did you do this morning"),
    ("THAT IS NOT WHAT I MEANT",       "that is not what i meant"),
    ("show failed responses",          "show failed responses"),
    ("Hermes, run daily operating cycle", "hermes, run daily operating cycle"),
    ("show memory v2 primary status",  "show memory v2 primary status"),
]

results = []


def _has_evidence_dump(text: str) -> bool:
    return any(m in (text or "") for m in EVIDENCE_DUMP_MARKERS)


def _has_generic_fallback(text: str) -> bool:
    return any(m in (text or "").lower() for m in GENERIC_FALLBACK_MARKERS)


def trace_message(raw: str, normalized: str) -> dict:
    record = {
        "message": raw,
        "normalized": normalized,
        "intake_intent": None,
        "intake_conf": None,
        "in_safe_intents": None,
        "cfo_brain_activates": None,
        "cfo_intent": None,
        "conversation_state_before": {},
        "option_1_resolves": None,
        "task_1_resolves": None,
        "last_recommendation_exists": None,
        "last_response_exists": None,
        "tool_chooser_result": None,
        "response_header": None,
        "response_preview": None,
        "has_evidence_dump": None,
        "has_generic_fallback": None,
        "notes": [],
    }

    # 1. Intake classification
    try:
        from hermes_command_router.intake import classify_intent
        intent, conf, _ = classify_intent(normalized)
        record["intake_intent"] = intent
        record["intake_conf"] = conf
    except Exception as e:
        record["notes"].append(f"intake error: {e}")

    # 2. Check if in SAFE intents
    try:
        _SAFE = {
            "small_talk", "date_time_question", "tomorrow_plan", "unknown_handling",
            "knowledge_gap_review", "memory_sources", "memory_sources_again",
            "active_operating_rules", "answer_source", "archived_executive_memory",
            "stale_memory_debug", "memory_v2_preview", "memory_v2_compare",
            "memory_v2_rules", "memory_v2_status", "memory_v2_shadow_status",
            "memory_v2_live_check", "memory_v2_primary_status",
            "lesson_record", "lesson_pending", "lesson_active",
            "lesson_approve_all", "lesson_approve", "lesson_reject",
            "lesson_deprecate", "lesson_learned", "lesson_source", "lesson_gap_generate",
            "daily_operating_cycle", "daily_approval_needed", "daily_continue_while_out",
            "daily_top_revenue_move", "daily_blockers", "thirty_day_revenue_plan",
            "show_last_daily_plan", "while_out_summary", "pending_daily_items",
            "compare_since_last_plan", "mark_daily_item_complete",
            "show_approval_queue", "show_approval_item", "approve_item", "reject_item",
            "approval_impact", "clear_stale_approvals", "bulk_approve_blocked",
            "build_revenue_asset_packet", "show_revenue_asset_packet",
            "show_launch_ready_assets", "show_content_awaiting_approval",
            "show_cta_options", "show_launch_checklist", "show_approval_checklist",
            "generate_approval_candidates",
            "show_revenue_packet_gaps", "improve_revenue_asset_packet",
            "show_improved_cta_options", "show_offer_bridge",
            "show_packet_improvement_plan", "rescore_revenue_packet",
            "show_final_review_checklist",
            "fix_revenue_packet_assets", "show_asset_fix_report", "rescore_after_fixes",
            "show_research_queue", "show_scout_assignments", "show_unresolved_questions",
            "create_implementation_prompt", "show_cfo_notes", "save_cfo_decision",
            "dedupe_research_queue",
            "show_failed_responses", "log_bad_response", "learn_from_that",
            "create_tests_from_failures",
        }
        record["in_safe_intents"] = record["intake_intent"] in _SAFE
    except Exception as e:
        record["notes"].append(f"safe_intents check error: {e}")

    # 3. CFO Brain activation
    try:
        from lib.hermes_cfo_brain import should_use_cfo_brain, classify_cfo_intent
        activates = should_use_cfo_brain(normalized)
        record["cfo_brain_activates"] = activates
        if activates:
            record["cfo_intent"] = classify_cfo_intent(normalized)
    except Exception as e:
        record["notes"].append(f"cfo_brain import error: {e}")

    # 4. Conversation state
    try:
        from lib.hermes_conversation_state import (
            load_conversation_state, get_option, get_task,
            get_last_recommendation, get_last_response_full,
        )
        state = load_conversation_state()
        record["conversation_state_before"] = {
            "has_option_map": bool(state.get("last_option_map")),
            "option_count": len(state.get("last_option_map") or {}),
            "has_task_map": bool(state.get("last_task_map")),
            "current_topic": state.get("current_topic"),
        }
        record["option_1_resolves"] = get_option(1) is not None
        record["task_1_resolves"] = get_task(1) is not None
        record["last_recommendation_exists"] = bool(get_last_recommendation())
        record["last_response_exists"] = bool(get_last_response_full())
    except Exception as e:
        record["notes"].append(f"conversation_state error: {e}")

    # 5. Process through CFO Brain
    try:
        from lib.hermes_cfo_brain import process_with_cfo_brain
        if record.get("cfo_brain_activates"):
            response = process_with_cfo_brain(raw, normalized)
            if response:
                record["response_header"] = response.split("\n")[0]
                record["response_preview"] = response[:500]
                record["has_evidence_dump"] = _has_evidence_dump(response)
                record["has_generic_fallback"] = _has_generic_fallback(response)
            else:
                record["notes"].append("CFO Brain returned None — would fall to TelegramRouter")
    except Exception as e:
        record["notes"].append(f"process_with_cfo_brain error: {e}")

    # 6. For exact commands, check run_command
    if not record.get("cfo_brain_activates") and record["in_safe_intents"]:
        try:
            from hermes_command_router.router import run_command
            cmd_response = run_command(normalized)
            if cmd_response:
                record["response_header"] = (cmd_response or "").split("\n")[0][:80]
                record["response_preview"] = (cmd_response or "")[:500]
                record["has_evidence_dump"] = _has_evidence_dump(cmd_response)
                record["has_generic_fallback"] = _has_generic_fallback(cmd_response)
            else:
                record["notes"].append("run_command returned empty — would fall to TelegramRouter")
        except Exception as e:
            record["notes"].append(f"run_command error: {e}")

    return record


print("\nPhase 7C Live Runtime Path Trace")
print("=" * 60)

for raw, norm in TEST_MESSAGES:
    print(f"\n{'─' * 60}")
    print(f"MSG: {raw}")
    rec = trace_message(raw, norm)
    results.append(rec)

    print(f"  intake: intent={rec['intake_intent']} conf={rec['intake_conf']} in_safe={rec['in_safe_intents']}")
    print(f"  cfo_brain: activates={rec['cfo_brain_activates']} intent={rec['cfo_intent']}")
    print(f"  state: option1={rec['option_1_resolves']} task1={rec['task_1_resolves']} rec={rec['last_recommendation_exists']}")
    print(f"  header: {rec['response_header']}")
    if rec['has_evidence_dump']:
        print(f"  !! EVIDENCE DUMP DETECTED")
    if rec['has_generic_fallback']:
        print(f"  !! GENERIC FALLBACK DETECTED")
    for note in rec['notes']:
        print(f"  NOTE: {note}")

# Save report
report_lines = [
    f"# Phase 7C Live Runtime Trace",
    f"Generated: {datetime.now().isoformat()}",
    "",
    "## Summary",
    "",
    "| Message | Intake Intent | CFO Brain | CFO Intent | Option 1 | Evidence Dump | Generic Fallback |",
    "|---------|--------------|-----------|------------|----------|---------------|-----------------|",
]
for r in results:
    report_lines.append(
        f"| {r['message'][:40]} | {r['intake_intent']} | {r['cfo_brain_activates']} | {r['cfo_intent']} | {r['option_1_resolves']} | {r['has_evidence_dump']} | {r['has_generic_fallback']} |"
    )

report_lines += ["", "## Detailed Records", ""]
for r in results:
    report_lines += [
        f"### {r['message']}",
        f"- Normalized: {r['normalized']}",
        f"- Intake intent: {r['intake_intent']} ({r['intake_conf']})",
        f"- In SAFE_REPEATABLE_MEMORY_INTENTS: {r['in_safe_intents']}",
        f"- CFO Brain activates: {r['cfo_brain_activates']}",
        f"- CFO intent: {r['cfo_intent']}",
        f"- State: option1={r['option_1_resolves']} task1={r['task_1_resolves']} rec={r['last_recommendation_exists']}",
        f"- Response header: {r['response_header']}",
        f"- Evidence dump: {r['has_evidence_dump']}",
        f"- Generic fallback: {r['has_generic_fallback']}",
    ]
    if r['notes']:
        report_lines += [f"- Notes: {'; '.join(r['notes'])}"]
    if r['response_preview']:
        report_lines += [f"```", r['response_preview'][:400], "```"]
    report_lines.append("")

report_path = REPORT_DIR / f"phase7c_live_runtime_trace_{TS}.md"
report_path.write_text("\n".join(report_lines))
print(f"\nReport saved: {report_path}")

# Summary counts
evidence_count = sum(1 for r in results if r.get('has_evidence_dump'))
fallback_count = sum(1 for r in results if r.get('has_generic_fallback'))
none_count = sum(1 for r in results if not r.get('response_preview'))
print(f"\nSummary: {len(results)} messages, {evidence_count} evidence dumps, {fallback_count} generic fallbacks, {none_count} no response (falls to TelegramRouter)")
