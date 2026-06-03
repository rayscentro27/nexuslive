"""test_phase8_cfo_loop_no_network_default.py — No network calls in default (mock) mode."""
import sys, os
import unittest.mock as mock
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

# Patch network libraries before importing prototype
with mock.patch("socket.socket") as mock_socket, \
     mock.patch("urllib.request.urlopen") as mock_url:

    from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop, MOCK_MODE

    # ── Confirm mock mode ─────────────────────────────────────────────────────
    check("MOCK_MODE is True", MOCK_MODE is True)

    # ── Process multiple messages — no network calls should be made ───────────
    loop = HermesCFOLoop()
    messages = [
        "how do we make money this week",
        "lets do 1",
        "what was task 1",
        "can you simplify your response",
        "explain your recommendation in plain language",
        "what are the scouts doing",
        "what is claude working on",
        "i approve them all",
    ]
    for msg in messages:
        try:
            response, trace = loop.process(msg)
            check(f"no exception: {msg[:40]}", True)
        except Exception as e:
            check(f"no exception: {msg[:40]}", False)

    # ── Verify no network calls were made ─────────────────────────────────────
    check("socket.socket not called", mock_socket.call_count == 0)
    check("urllib.request.urlopen not called", mock_url.call_count == 0)

# ── Verify HERMES_CFO_MODEL_PROVIDER is not set in test environment ───────────
provider = os.getenv("HERMES_CFO_MODEL_PROVIDER", "")
check("HERMES_CFO_MODEL_PROVIDER not set in test env", provider == "")

# ── Verify CFOReasoningBrain._live_reason raises when called directly ─────────
from prototypes.hermes_agentic_cfo_loop import CFOReasoningBrain, ConversationState
brain = CFOReasoningBrain()
state = ConversationState()
try:
    brain._live_reason("test", state, {}, {"intent": "unknown_answer", "confidence": 0.5})
    check("live_reason raises NotImplementedError in prototype", False)
except NotImplementedError:
    check("live_reason raises NotImplementedError in prototype", True)
except Exception as e:
    check("live_reason raises NotImplementedError in prototype", False)

print(f"\nPhase 8 no network default mode: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
