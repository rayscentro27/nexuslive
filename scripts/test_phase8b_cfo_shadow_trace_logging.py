"""test_phase8b_cfo_shadow_trace_logging.py — Shadow mode writes JSONL traces correctly."""
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
    save_shadow_trace, load_shadow_traces, clear_shadow_traces,
    build_shadow_trace, run_cfo_shadow_for_message, SHADOW_TRACE_FILE,
)

# ── Use temp trace file for tests ─────────────────────────────────────────────
with tempfile.TemporaryDirectory() as tmpdir:
    tmp_trace = Path(tmpdir) / "shadow_traces.jsonl"
    orig_file = shadow_mod.SHADOW_TRACE_FILE
    orig_dir = shadow_mod.SHADOW_TRACE_DIR
    shadow_mod.SHADOW_TRACE_FILE = tmp_trace
    shadow_mod.SHADOW_TRACE_DIR = tmp_trace.parent

    # ── save_shadow_trace writes JSONL ────────────────────────────────────────
    t1 = build_shadow_trace("how do we make money", "WEEKLY MONEY PLAN", None)
    save_shadow_trace(t1)
    check("trace file created", tmp_trace.exists())
    lines = tmp_trace.read_text().strip().splitlines()
    check("1 line written", len(lines) == 1)
    entry = json.loads(lines[0])
    check("has timestamp", bool(entry.get("timestamp")))
    check("has message_hash", bool(entry.get("message_hash")))
    check("has normalized_message", bool(entry.get("normalized_message")))
    check("live_response_changed=False", entry.get("live_response_changed") is False)
    check("has cfo_loop_mode", "cfo_loop_mode" in entry)
    check("has duration_ms", "duration_ms" in entry)
    check("has safety_flags", "safety_flags" in entry)
    check("has evidence_keys_used", "evidence_keys_used" in entry)

    # ── Multiple traces accumulate ────────────────────────────────────────────
    for i in range(4):
        t = build_shadow_trace(f"message {i}", f"RESPONSE {i}", None)
        save_shadow_trace(t)
    lines2 = tmp_trace.read_text().strip().splitlines()
    check("5 total traces", len(lines2) == 5)

    # ── load_shadow_traces ────────────────────────────────────────────────────
    loaded = load_shadow_traces(limit=100)
    check("load returns 5 traces", len(loaded) == 5)
    check("each loaded trace has timestamp", all("timestamp" in t for t in loaded))

    # ── clear_shadow_traces ───────────────────────────────────────────────────
    count = clear_shadow_traces()
    check("clear returns correct count", count == 5)
    lines3 = tmp_trace.read_text().strip().splitlines()
    check("trace file is empty after clear", lines3 == [] or lines3 == [""])
    loaded2 = load_shadow_traces()
    check("load returns 0 after clear", len(loaded2) == 0)

    # ── run_cfo_shadow_for_message writes to trace file ───────────────────────
    trace = run_cfo_shadow_for_message("what are the scouts doing", live_response="SCOUT STATUS\n\nActive: 1")
    lines4 = tmp_trace.read_text().strip().splitlines()
    check("run writes 1 trace line", len(lines4) == 1)
    written = json.loads(lines4[0])
    check("written trace has cfo_intent", "cfo_intent" in written)
    check("written trace cfo_loop_mode=shadow", written.get("cfo_loop_mode") == "shadow")

    shadow_mod.SHADOW_TRACE_FILE = orig_file
    shadow_mod.SHADOW_TRACE_DIR = orig_dir

# ── SHADOW_TRACE_FILE path ─────────────────────────────────────────────────────
check("SHADOW_TRACE_FILE is defined", SHADOW_TRACE_FILE is not None)
check("SHADOW_TRACE_FILE ends in .jsonl", str(SHADOW_TRACE_FILE).endswith(".jsonl"))
check("SHADOW_TRACE_FILE in shadow/ dir", "shadow" in str(SHADOW_TRACE_FILE))

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B shadow trace logging: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
