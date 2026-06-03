"""test_phase8_cfo_loop_prototype.py — Prototype runs in mock mode."""
import sys, os
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

from prototypes.hermes_agentic_cfo_loop import (
    HermesCFOLoop, run_cfo_loop, MOCK_MODE, ConversationState,
    IntentBrain, RetrievalBrain, CFOReasoningBrain, ToolExecutor, PlainEnglishResponder,
)

# ── Mock mode is active ───────────────────────────────────────────────────────
check("MOCK_MODE is True by default", MOCK_MODE is True)

# ── All brain classes instantiate ─────────────────────────────────────────────
loop = HermesCFOLoop()
check("HermesCFOLoop instantiates", loop is not None)
check("state is ConversationState", isinstance(loop.state, ConversationState))
check("intent_brain exists", isinstance(loop.intent_brain, IntentBrain))
check("retrieval_brain exists", isinstance(loop.retrieval_brain, RetrievalBrain))
check("cfo_brain exists", isinstance(loop.cfo_brain, CFOReasoningBrain))
check("tool_executor exists", isinstance(loop.tool_executor, ToolExecutor))
check("responder exists", isinstance(loop.responder, PlainEnglishResponder))

# ── Basic message processing ──────────────────────────────────────────────────
response, trace = loop.process("how do we make money this week")
check("process returns tuple", isinstance(response, str) and isinstance(trace, dict))
check("response is non-empty", len(response) > 50)
check("trace has intent", "intent" in trace)
check("trace has tool", "tool" in trace)
check("trace has confidence", "confidence" in trace)
check("trace has trace_id", "trace_id" in trace)

# ── Approval boundary in every response ──────────────────────────────────────
check("response has approval boundary", "approval boundary" in response.lower() or "approval" in response.lower())

# ── run_cfo_loop convenience function ────────────────────────────────────────
resp2, trace2 = run_cfo_loop("what are the scouts doing")
check("run_cfo_loop works", isinstance(resp2, str) and len(resp2) > 20)
check("scout status intent", trace2.get("intent") == "scout_status")

# ── State updates after processing ───────────────────────────────────────────
loop2 = HermesCFOLoop()
loop2.process("how do we make money this week")
check("state updated after money strategy", bool(loop2.state.last_option_map) or bool(loop2.state.active_recommendation))

print(f"\nPhase 8 CFO loop prototype: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
