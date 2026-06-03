"""test_phase8_cfo_loop_trace_logging.py — Trace logging works correctly."""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")

from pathlib import Path
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop, TraceLogger, TRACE_FILE

# ── TraceLogger writes to JSONL file ─────────────────────────────────────────
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as tf:
    tmp_path = Path(tf.name)

logger = TraceLogger(trace_file=tmp_path)
trace_id = logger.log(
    message="test message",
    intent_result={"intent": "money_strategy", "confidence": 0.9},
    evidence_keys=["revenue_packet"],
    reasoning={"tool_to_call": "show_revenue_plan", "tool_args": {}, "safety_notes": "read-only", "mode": "mock"},
    tool_result={"status": "ok", "tool": "show_revenue_plan"},
    final_response="WEEKLY MONEY PLAN\n\n...",
)
check("trace_id returned", bool(trace_id))
check("trace file created", tmp_path.exists())

lines = tmp_path.read_text().strip().splitlines()
check("trace file has 1 line", len(lines) == 1)

entry = json.loads(lines[0])
check("trace has trace_id", "trace_id" in entry)
check("trace has timestamp", "timestamp" in entry)
check("trace has message", entry.get("message") == "test message")
check("trace has intent", entry.get("intent") == "money_strategy")
check("trace has confidence", entry.get("confidence") == 0.9)
check("trace has retrieved_evidence_keys", entry.get("retrieved_evidence_keys") == ["revenue_packet"])
check("trace has selected_tool", entry.get("selected_tool") == "show_revenue_plan")
check("trace has final_response_header", "WEEKLY MONEY PLAN" in (entry.get("final_response_header") or ""))
check("trace has safety_notes", bool(entry.get("safety_notes")))
check("trace has mode", entry.get("mode") == "mock")
tmp_path.unlink()

# ── Full loop produces trace ──────────────────────────────────────────────────
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as tf:
    tmp2 = Path(tf.name)

loop = HermesCFOLoop()
loop.trace_logger = TraceLogger(trace_file=tmp2)

response, trace_info = loop.process("how do we make money this week")
check("loop produces trace_id in info", bool(trace_info.get("trace_id")))
check("trace file written", tmp2.exists() and tmp2.stat().st_size > 0)

lines2 = tmp2.read_text().strip().splitlines()
check("exactly 1 trace line", len(lines2) == 1)
entry2 = json.loads(lines2[0])
check("full loop trace has intent", bool(entry2.get("intent")))
check("full loop trace has tool", bool(entry2.get("selected_tool")))
tmp2.unlink()

# ── Multiple messages produce multiple trace lines ────────────────────────────
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as tf:
    tmp3 = Path(tf.name)

loop3 = HermesCFOLoop()
loop3.trace_logger = TraceLogger(trace_file=tmp3)
for msg in ["how do we make money", "lets do 1", "what was task 1"]:
    loop3.process(msg)

lines3 = tmp3.read_text().strip().splitlines()
check("3 messages produce 3 trace lines", len(lines3) == 3)
for line in lines3:
    entry = json.loads(line)
    check(f"each trace has intent: {entry.get('intent')}", bool(entry.get("intent")))
tmp3.unlink()

# ── Trace file path exists (default) ─────────────────────────────────────────
check("TRACE_FILE path defined", TRACE_FILE is not None)
check("TRACE_FILE parent is strategy dir", "strategy" in str(TRACE_FILE))

print(f"\nPhase 8 trace logging: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
