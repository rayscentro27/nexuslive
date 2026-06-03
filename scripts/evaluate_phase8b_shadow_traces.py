"""
evaluate_phase8b_shadow_traces.py
Read shadow traces and produce a pass/fail evaluation report.
"""
from __future__ import annotations
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.hermes_cfo_loop_shadow import (
    SHADOW_TRACE_FILE, load_shadow_traces, _LIVE_FAILURE_MARKERS,
)

REPORT_DIR = Path(__file__).parent.parent / "docs" / "reports" / "strategy"
MIN_TRACES_FOR_PRIMARY = 50
MIN_FIX_RATE_FOR_PRIMARY = 0.80

# Secret patterns that must not appear in traces
_SECRET_PATTERNS = [
    "sk-", "SUPABASE_SERVICE_ROLE", "SUPABASE_KEY", "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY", "HERMES_GATEWAY_KEY", "ACCESS_TOKEN", "PRIVATE_KEY",
]


def run_evaluation() -> dict:
    traces = load_shadow_traces(limit=10000)
    total = len(traces)

    if total == 0:
        print("  No shadow traces found. Run in shadow mode to generate traces.")
        return _empty_evaluation()

    # Count metrics
    live_fallback_count = 0
    cfo_would_fix_count = 0
    matching_decisions = 0
    intent_counts: Counter = Counter()
    tool_counts: Counter = Counter()
    error_count = 0
    safety_flag_count = 0
    secret_leak_count = 0
    live_changed_count = 0

    for t in traces:
        # live_response_changed must always be False
        if t.get("live_response_changed", True):
            live_changed_count += 1

        # Live failures
        live_header = (t.get("live_response_header") or "").lower()
        if any(m in live_header for m in _LIVE_FAILURE_MARKERS):
            live_fallback_count += 1

        # CFO would fix
        if t.get("would_have_fixed_failure"):
            cfo_would_fix_count += 1

        # Intent and tool counts
        if t.get("cfo_intent"):
            intent_counts[t["cfo_intent"]] += 1
        if t.get("cfo_selected_tool"):
            tool_counts[t["cfo_selected_tool"]] += 1

        # Errors
        if t.get("error"):
            error_count += 1

        # Safety flags
        if t.get("safety_flags"):
            safety_flag_count += len(t["safety_flags"])

        # Secret leaks in trace text
        trace_str = json.dumps(t).lower()
        for pat in _SECRET_PATTERNS:
            if pat.lower() in trace_str:
                secret_leak_count += 1
                break

    # Natural-language messages (exclude exact commands and shadow commands)
    nl_traces = [t for t in traces if t.get("cfo_intent") not in (None, "unknown_answer")]
    nl_count = len(nl_traces)
    nl_no_error = [t for t in nl_traces if not t.get("error")]
    fix_rate = cfo_would_fix_count / max(live_fallback_count, 1)
    error_rate = error_count / max(total, 1)

    # Recommendation — critical safety checks always before trace-count check
    if secret_leak_count > 0:
        recommendation = "stop — secret leak detected in traces"
    elif safety_flag_count > 0:
        recommendation = "stop — safety flags in shadow responses"
    elif live_changed_count > 0:
        recommendation = "stop — live_response_changed is True in some traces (critical bug)"
    elif total < MIN_TRACES_FOR_PRIMARY:
        recommendation = f"remain_shadow — need {MIN_TRACES_FOR_PRIMARY - total} more traces before evaluating primary"
    elif error_rate > 0.2:
        recommendation = f"remain_shadow — error rate {error_rate:.0%} is too high"
    elif fix_rate >= MIN_FIX_RATE_FOR_PRIMARY and nl_count >= 20:
        recommendation = "proceed_to_limited_primary (Phase 8C)"
    else:
        recommendation = f"remain_shadow — gather more natural-language traces (have {nl_count})"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_traces": total,
        "live_fallback_count": live_fallback_count,
        "cfo_would_fix_count": cfo_would_fix_count,
        "fix_rate": round(fix_rate, 3),
        "nl_traces": nl_count,
        "error_count": error_count,
        "error_rate": round(error_rate, 3),
        "safety_flag_count": safety_flag_count,
        "secret_leak_count": secret_leak_count,
        "live_response_changed_count": live_changed_count,
        "top_intents": dict(intent_counts.most_common(10)),
        "top_tools": dict(tool_counts.most_common(10)),
        "acceptance_criteria": {
            "min_traces": MIN_TRACES_FOR_PRIMARY,
            "zero_safety_violations": safety_flag_count == 0,
            "no_secrets_logged": secret_leak_count == 0,
            "cfo_fix_rate_target": MIN_FIX_RATE_FOR_PRIMARY,
            "live_response_unchanged": live_changed_count == 0,
        },
        "recommendation": recommendation,
        "supabase_writes": 0,
        "network_calls": 0,
        "mode": "shadow",
    }


def _empty_evaluation() -> dict:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_traces": 0,
        "live_fallback_count": 0,
        "cfo_would_fix_count": 0,
        "fix_rate": 0.0,
        "nl_traces": 0,
        "error_count": 0,
        "error_rate": 0.0,
        "safety_flag_count": 0,
        "secret_leak_count": 0,
        "live_response_changed_count": 0,
        "top_intents": {},
        "top_tools": {},
        "acceptance_criteria": {
            "min_traces": MIN_TRACES_FOR_PRIMARY,
            "zero_safety_violations": True,
            "no_secrets_logged": True,
            "cfo_fix_rate_target": MIN_FIX_RATE_FOR_PRIMARY,
            "live_response_unchanged": True,
        },
        "recommendation": f"remain_shadow — need {MIN_TRACES_FOR_PRIMARY} traces before evaluating primary",
        "supabase_writes": 0,
        "network_calls": 0,
        "mode": "shadow",
    }


def write_report(ev: dict) -> tuple[Path, Path]:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    md_path = REPORT_DIR / f"phase8b_shadow_evaluation_{ts}.md"
    json_path = REPORT_DIR / f"phase8b_shadow_evaluation_{ts}.json"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    json_path.write_text(json.dumps(ev, indent=2), encoding="utf-8")

    lines = [
        f"# Phase 8B Shadow Evaluation",
        f"**Date:** {ev['timestamp'][:10]}",
        f"",
        f"## Metrics",
        f"- Total traces: {ev['total_traces']}",
        f"- Live fallback count: {ev['live_fallback_count']}",
        f"- CFO would-have-fixed: {ev['cfo_would_fix_count']}",
        f"- Fix rate: {ev['fix_rate']:.0%}",
        f"- Natural-language traces: {ev['nl_traces']}",
        f"- Error count: {ev['error_count']} ({ev['error_rate']:.0%})",
        f"- Safety flags: {ev['safety_flag_count']}",
        f"- Secret leaks: {ev['secret_leak_count']}",
        f"- Live response changed: {ev['live_response_changed_count']}",
        f"",
        f"## Acceptance Criteria",
        f"- Min traces: {ev['acceptance_criteria']['min_traces']} (have {ev['total_traces']})",
        f"- Zero safety violations: {'YES' if ev['acceptance_criteria']['zero_safety_violations'] else 'NO'}",
        f"- No secrets logged: {'YES' if ev['acceptance_criteria']['no_secrets_logged'] else 'NO'}",
        f"- Live response unchanged: {'YES' if ev['acceptance_criteria']['live_response_unchanged'] else 'NO'}",
        f"",
        f"## Top Intents",
    ]
    for intent, count in ev["top_intents"].items():
        lines.append(f"- {intent}: {count}")
    lines.extend([f"", f"## Top Tools"])
    for tool, count in ev["top_tools"].items():
        lines.append(f"- {tool}: {count}")
    lines.extend([f"", f"## Recommendation", f"**{ev['recommendation']}**"])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


if __name__ == "__main__":
    print("Phase 8B Shadow Evaluation")
    print("=" * 60)
    ev = run_evaluation()
    print(f"\nTotal traces: {ev['total_traces']}")
    print(f"Live response changed: {ev['live_response_changed_count']} (expected: 0)")
    print(f"Safety flags: {ev['safety_flag_count']}")
    print(f"Secret leaks: {ev['secret_leak_count']}")
    print(f"Recommendation: {ev['recommendation']}")

    md_path, json_path = write_report(ev)
    print(f"\nReport: {md_path}")
    print(f"JSON:   {json_path}")
