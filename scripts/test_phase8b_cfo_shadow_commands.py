"""test_phase8b_cfo_shadow_commands.py — Shadow Telegram commands work."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

from pathlib import Path

os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

import lib.hermes_cfo_loop_shadow as shadow_mod
from lib.hermes_cfo_loop_shadow import (
    handle_cfo_shadow_command, format_shadow_status, format_recent_shadow_traces,
    compare_live_vs_shadow, save_shadow_trace, build_shadow_trace, clear_shadow_traces,
    _handle_clear_traces,
)

# ── Use temp trace file ───────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_trace = Path(tmpdir) / "shadow_traces.jsonl"
    orig_file = shadow_mod.SHADOW_TRACE_FILE
    orig_dir = shadow_mod.SHADOW_TRACE_DIR
    shadow_mod.SHADOW_TRACE_FILE = tmp_trace
    shadow_mod.SHADOW_TRACE_DIR = tmp_trace.parent

    # Seed some traces
    for msg in ["how do we make money", "lets do 1", "what was task 1"]:
        t = build_shadow_trace(msg, f"LIVE for {msg}", {"trace": {"intent": "money_strategy", "tool": "show_revenue_plan", "confidence": 0.9}, "response": "WEEKLY MONEY PLAN\n\nOptions here."})
        save_shadow_trace(t)

    # ── format_shadow_status ─────────────────────────────────────────────────
    status = format_shadow_status()
    check("status is string", isinstance(status, str))
    check("status has 'CFO LOOP SHADOW STATUS'", "CFO LOOP SHADOW STATUS" in status)
    check("status has 'Mode:'", "Mode:" in status)
    check("status has 'shadow'", "shadow" in status)
    check("status has 'Live response changed: NO'", "Live response changed: NO" in status)
    check("status has 'Provider:'", "Provider:" in status)
    check("status has 'Recent traces:'", "Recent traces:" in status)
    check("status has approval boundary", "approval" in status.lower())

    # ── format_recent_shadow_traces ──────────────────────────────────────────
    traces_out = format_recent_shadow_traces(10)
    check("traces output is string", isinstance(traces_out, str))
    check("traces has 'CFO SHADOW TRACES'", "CFO SHADOW TRACES" in traces_out)
    check("traces has message content", "Message:" in traces_out)
    check("traces has Intent:", "Intent:" in traces_out)
    check("traces has Tool:", "Tool:" in traces_out)
    check("traces has approval boundary", "approval" in traces_out.lower())

    # ── compare_live_vs_shadow ────────────────────────────────────────────────
    comparison = compare_live_vs_shadow()
    check("comparison is string", isinstance(comparison, str))
    check("comparison has 'CFO LIVE VS SHADOW'", "CFO LIVE VS SHADOW" in comparison)
    check("comparison has 'Live response:'", "Live response:" in comparison)
    check("comparison has CFO info section", "Shadow would have:" in comparison or "CFO Loop would have:" in comparison)
    check("comparison has approval boundary", "approval" in comparison.lower())

    # ── handle_cfo_shadow_command dispatches correctly ────────────────────────
    commands = [
        "show cfo shadow status",
        "cfo shadow status",
        "show cfo loop mode",
        "cfo loop mode",
        "show cfo shadow traces",
        "cfo shadow traces",
        "compare cfo shadow",
    ]
    for cmd in commands:
        result = handle_cfo_shadow_command(cmd)
        check(f"command '{cmd}' returns string", isinstance(result, str) and len(result) > 20)
        check(f"command '{cmd}' has approval boundary", "approval" in (result or "").lower())

    # ── unknown command returns None ─────────────────────────────────────────
    check("unknown command returns None", handle_cfo_shadow_command("some random message") is None)

    # ── clear traces command ─────────────────────────────────────────────────
    clear_result = handle_cfo_shadow_command("clear cfo shadow test traces")
    check("clear command returns string", isinstance(clear_result, str))
    check("clear result mentions cleared", "cleared" in clear_result.lower() or "clear" in clear_result.lower())

    shadow_mod.SHADOW_TRACE_FILE = orig_file
    shadow_mod.SHADOW_TRACE_DIR = orig_dir

# ── No traces case ────────────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmpdir2:
    shadow_mod.SHADOW_TRACE_FILE = Path(tmpdir2) / "empty.jsonl"
    shadow_mod.SHADOW_TRACE_DIR = Path(tmpdir2)

    empty_traces = format_recent_shadow_traces(10)
    check("empty traces: no crash", isinstance(empty_traces, str))
    check("empty traces: has 'No traces'", "No traces" in empty_traces or "no trace" in empty_traces.lower())

    empty_status = format_shadow_status()
    check("empty status: has '0' traces", "0" in empty_status)

    shadow_mod.SHADOW_TRACE_FILE = orig_file
    shadow_mod.SHADOW_TRACE_DIR = orig_dir

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B shadow commands: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
