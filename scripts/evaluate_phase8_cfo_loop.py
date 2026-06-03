"""
evaluate_phase8_cfo_loop.py
Phase 8 evaluation script: runs each fixture case through the CFO loop prototype
and produces a pass/fail report.
"""
from __future__ import annotations

import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURES_PATH = Path(__file__).parent.parent / "prototypes" / "fixtures" / "phase8_failed_telegram_cases.json"
REPORT_DIR = Path(__file__).parent.parent / "docs" / "reports" / "strategy"

FORBIDDEN_IN_ANY_RESPONSE = [
    "artifact_inventory",
    "handoff dump",
    "i can answer from verified artifacts",
    "i wasn't able to generate a quality response",
]

# HERMES REPORT is only forbidden unless explicitly requested — cases don't request it
HERMES_REPORT_FORBIDDEN = True


def run_evaluation() -> dict:
    from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop, ConversationState

    fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    cases = fixtures["cases"]

    results = []
    pass_count = 0
    fail_count = 0

    for case in cases:
        case_id = case["id"]
        message = case["message"]
        context = case.get("context", {})
        expected = case["expected"]

        # Build a fresh loop with pre-seeded state matching context
        loop = HermesCFOLoop()
        _seed_state(loop.state, context)

        try:
            response, trace = loop.process(message)
            case_pass, failures = _evaluate_case(case, response, trace)
        except Exception as exc:
            response = f"ERROR: {exc}"
            trace = {}
            case_pass = False
            failures = [f"Exception: {exc}"]

        result = {
            "case_id": case_id,
            "message": message,
            "expected_intent": expected.get("intent"),
            "expected_tool": expected.get("tool"),
            "actual_intent": trace.get("intent", "unknown"),
            "actual_tool": trace.get("tool", "unknown"),
            "confidence": trace.get("confidence"),
            "response_preview": response[:200] if response else "",
            "pass": case_pass,
            "failures": failures,
        }
        results.append(result)

        if case_pass:
            pass_count += 1
            print(f"  PASS [{case_id}] {message[:50]}")
        else:
            fail_count += 1
            print(f"  FAIL [{case_id}] {message[:50]}")
            for f in failures:
                print(f"        → {f}")

    total = pass_count + fail_count
    evaluation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_cases": total,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": f"{pass_count}/{total}",
        "pass_pct": round(pass_count / total * 100, 1) if total else 0,
        "acceptance_threshold": "10/12",
        "accepted": pass_count >= 10,
        "results": results,
        "mode": "mock",
        "supabase_writes": 0,
        "network_calls": 0,
    }
    return evaluation


def _seed_state(state: "ConversationState", context: dict) -> None:
    if context.get("last_response_was_draft"):
        state.last_response_was_draft = True
        state.last_meaningful_response = "LEAD MAGNET DRAFT\n\nDraft v1: Get Your Business Funding-Ready in 30 Days.\nDraft v2: Is Your Business Ready for $50K+ in Funding?"
    if context.get("last_response_was_approval_queue"):
        state.last_response_was_approval_queue = True
        state.last_meaningful_response = "APPROVAL QUEUE\n\nItems pending: 3"
    if context.get("last_selected_option"):
        state.last_selected_option = context["last_selected_option"]
        state.last_selected_option_text = context.get("last_selected_option_text", f"Option {context['last_selected_option']}")
    if context.get("last_option_map"):
        state.last_option_map = context["last_option_map"]
    if context.get("active_recommendation"):
        state.active_recommendation = context["active_recommendation"]
    if context.get("last_meaningful_response"):
        state.last_meaningful_response = context["last_meaningful_response"]
    if context.get("last_meaningful_response_summary"):
        state.last_meaningful_response_summary = context["last_meaningful_response_summary"]
    if context.get("current_topic"):
        state.current_topic = context["current_topic"]


def _evaluate_case(case: dict, response: str, trace: dict) -> tuple[bool, list]:
    expected = case["expected"]
    failures = []
    response_lower = response.lower() if response else ""

    # Check intent
    exp_intent = expected.get("intent")
    actual_intent = trace.get("intent", "unknown")
    if exp_intent and actual_intent != exp_intent:
        failures.append(f"Intent: expected '{exp_intent}', got '{actual_intent}'")

    # Check tool
    exp_tool = expected.get("tool")
    actual_tool = trace.get("tool", "unknown")
    if exp_tool and actual_tool != exp_tool:
        failures.append(f"Tool: expected '{exp_tool}', got '{actual_tool}'")

    # Check response_must_contain (case-insensitive)
    for phrase in expected.get("response_must_contain", []):
        if phrase.lower() not in response_lower:
            failures.append(f"Response missing required phrase: '{phrase}'")

    # Check response_must_not_contain
    for phrase in expected.get("response_must_not_contain", []):
        if phrase.lower() in response_lower:
            failures.append(f"Response contains forbidden phrase: '{phrase}'")

    # Global forbidden phrases check
    for phrase in FORBIDDEN_IN_ANY_RESPONSE:
        if phrase in response_lower:
            failures.append(f"Global forbidden phrase in response: '{phrase}'")

    # HERMES REPORT check
    if HERMES_REPORT_FORBIDDEN and "hermes report" in response_lower:
        failures.append("Response contains 'HERMES REPORT' (not requested)")

    return len(failures) == 0, failures


def write_report(evaluation: dict) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = REPORT_DIR / f"phase8_cfo_loop_evaluation_{ts}.md"
    json_path = REPORT_DIR / f"phase8_cfo_loop_evaluation_{ts}.json"

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Write JSON
    json_path.write_text(json.dumps(evaluation, indent=2), encoding="utf-8")

    # Write MD
    lines = [
        f"# Phase 8 CFO Loop Evaluation",
        f"**Date:** {evaluation['timestamp'][:10]}",
        f"**Mode:** {evaluation['mode']}",
        f"",
        f"## Results",
        f"- Pass rate: **{evaluation['pass_rate']}** ({evaluation['pass_pct']}%)",
        f"- Acceptance threshold: {evaluation['acceptance_threshold']}",
        f"- Accepted: **{'YES' if evaluation['accepted'] else 'NO'}**",
        f"- Supabase writes: {evaluation['supabase_writes']}",
        f"- Network calls: {evaluation['network_calls']}",
        f"",
        f"## Case Results",
        f"",
    ]
    for r in evaluation["results"]:
        status = "PASS" if r["pass"] else "FAIL"
        lines.append(f"### [{status}] {r['case_id']} — {r['message']}")
        lines.append(f"- Expected intent: `{r['expected_intent']}` → Got: `{r['actual_intent']}`")
        lines.append(f"- Expected tool: `{r['expected_tool']}` → Got: `{r['actual_tool']}`")
        lines.append(f"- Confidence: {r['confidence']}")
        if r["failures"]:
            lines.append(f"- Failures:")
            for f in r["failures"]:
                lines.append(f"  - {f}")
        lines.append(f"- Response preview: `{r['response_preview'][:120]}`")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


if __name__ == "__main__":
    print("Phase 8 CFO Loop Evaluation")
    print("=" * 60)
    evaluation = run_evaluation()
    print(f"\nResult: {evaluation['pass_rate']} ({evaluation['pass_pct']}%) — {'ACCEPTED' if evaluation['accepted'] else 'NOT ACCEPTED'}")

    md_path, json_path = write_report(evaluation)
    print(f"\nReport: {md_path}")
    print(f"JSON:   {json_path}")

    if not evaluation["accepted"]:
        sys.exit(1)
