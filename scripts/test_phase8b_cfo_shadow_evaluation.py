"""test_phase8b_cfo_shadow_evaluation.py — evaluate_phase8b_shadow_traces.py works."""
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
from lib.hermes_cfo_loop_shadow import build_shadow_trace, save_shadow_trace

from scripts.evaluate_phase8b_shadow_traces import run_evaluation, write_report, _SECRET_PATTERNS

# ── Empty trace case ──────────────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmpdir:
    orig_file = shadow_mod.SHADOW_TRACE_FILE
    orig_dir = shadow_mod.SHADOW_TRACE_DIR
    tmp_trace = Path(tmpdir) / "traces.jsonl"
    shadow_mod.SHADOW_TRACE_FILE = tmp_trace
    shadow_mod.SHADOW_TRACE_DIR = Path(tmpdir)

    ev_empty = run_evaluation()
    check("empty: total_traces=0", ev_empty["total_traces"] == 0)
    check("empty: recommendation contains 'remain_shadow'", "remain_shadow" in ev_empty["recommendation"])
    check("empty: supabase_writes=0", ev_empty["supabase_writes"] == 0)
    check("empty: network_calls=0", ev_empty["network_calls"] == 0)
    check("empty: live_response_changed_count=0", ev_empty["live_response_changed_count"] == 0)

    # ── Normal traces ─────────────────────────────────────────────────────────
    messages = [
        ("how do we make money", "WEEKLY MONEY PLAN", {"trace": {"intent": "money_strategy", "tool": "show_revenue_plan", "confidence": 0.9}, "response": "WEEKLY MONEY PLAN\n\nLead magnet."}),
        ("lets do 1", "PLAIN ANSWER", {"trace": {"intent": "option_selection", "tool": "select_option", "confidence": 0.95}, "response": "PLAIN ANSWER\n\nYou chose option 1."}),
        ("what was task 1", "PLAIN ANSWER", {"trace": {"intent": "task_reference", "tool": "select_option", "confidence": 0.9}, "response": "PLAIN ANSWER\n\nTask 1 was: Lead magnet."}),
    ]
    for msg, live, cfo_result in messages:
        t = build_shadow_trace(msg, live, cfo_result)
        save_shadow_trace(t)

    ev_normal = run_evaluation()
    check("normal: total_traces=3", ev_normal["total_traces"] == 3)
    check("normal: live_response_changed_count=0", ev_normal["live_response_changed_count"] == 0)
    check("normal: safety_flag_count=0", ev_normal["safety_flag_count"] == 0)
    check("normal: secret_leak_count=0", ev_normal["secret_leak_count"] == 0)
    check("normal: has top_intents", isinstance(ev_normal["top_intents"], dict))
    check("normal: has top_tools", isinstance(ev_normal["top_tools"], dict))
    check("normal: has recommendation", bool(ev_normal["recommendation"]))
    check("normal: acceptance_criteria dict", isinstance(ev_normal["acceptance_criteria"], dict))

    # ── Secret detection ──────────────────────────────────────────────────────
    shadow_mod.SHADOW_TRACE_FILE.write_text("", encoding="utf-8")
    bad_trace = build_shadow_trace("test", "LIVE", None)
    bad_trace["cfo_response_preview"] = "Here is your sk-abcdef1234567890 key"
    save_shadow_trace(bad_trace)
    ev_secret = run_evaluation()
    check("secret detection works", ev_secret["secret_leak_count"] > 0)

    # ── live_response_changed detection ──────────────────────────────────────
    shadow_mod.SHADOW_TRACE_FILE.write_text("", encoding="utf-8")
    bad_trace2 = build_shadow_trace("test2", "LIVE", None)
    bad_trace2["live_response_changed"] = True  # Simulate bug
    save_shadow_trace(bad_trace2)
    ev_changed = run_evaluation()
    check("live_changed detection works", ev_changed["live_response_changed_count"] > 0)
    check("live_changed recommendation is 'stop'", "stop" in ev_changed["recommendation"])

    # ── write_report works ────────────────────────────────────────────────────
    shadow_mod.SHADOW_TRACE_FILE.write_text("", encoding="utf-8")
    for msg, live, cfo_result in messages:
        t = build_shadow_trace(msg, live, cfo_result)
        save_shadow_trace(t)

    ev2 = run_evaluation()
    from scripts.evaluate_phase8b_shadow_traces import REPORT_DIR as ORIG_REPORT_DIR
    import scripts.evaluate_phase8b_shadow_traces as eval_mod
    eval_mod.REPORT_DIR = Path(tmpdir)

    md, js = write_report(ev2)
    check("report MD created", md.exists())
    check("report JSON created", js.exists())
    js_data = json.loads(js.read_text())
    check("report JSON has total_traces", "total_traces" in js_data)

    eval_mod.REPORT_DIR = ORIG_REPORT_DIR
    shadow_mod.SHADOW_TRACE_FILE = orig_file
    shadow_mod.SHADOW_TRACE_DIR = orig_dir

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B shadow evaluation: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
