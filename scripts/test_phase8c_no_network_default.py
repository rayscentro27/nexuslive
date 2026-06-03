"""test_phase8c_no_network_default.py — no network calls in mock/default mode."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

# ── Default provider is mock ──────────────────────────────────────────────────
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)
from lib.hermes_cfo_loop_shadow import get_cfo_loop_provider
check("default provider is mock", get_cfo_loop_provider() == "mock")

# ── mock mode uses no network ─────────────────────────────────────────────────
import prototypes.hermes_agentic_cfo_loop as proto_mod
import importlib
os.environ.pop("HERMES_CFO_MODEL_PROVIDER", None)
importlib.reload(proto_mod)
check("MOCK_MODE is True when no provider env set", proto_mod.MOCK_MODE is True)

# ── CFO reasoning brain raises NotImplementedError for live ──────────────────
from prototypes.hermes_agentic_cfo_loop import CFOReasoningBrain, ConversationState
brain = CFOReasoningBrain()
state = ConversationState()
try:
    # Force live mode by patching MOCK_MODE
    original = proto_mod.MOCK_MODE
    proto_mod.MOCK_MODE = False
    brain_live = CFOReasoningBrain()
    # Need to call _live_reason which raises NotImplementedError
    raised = False
    try:
        brain_live._live_reason("test", state, {}, {"intent": "test", "confidence": 0.9})
    except NotImplementedError:
        raised = True
    check("live mode raises NotImplementedError (network blocked in prototype)", raised)
finally:
    proto_mod.MOCK_MODE = original

# ── prototype source has no real network imports ──────────────────────────────
import pathlib
source = pathlib.Path(proto_mod.__file__).read_text()
check("prototype has no 'import requests'", "import requests" not in source)
check("prototype has no 'import httpx'", "import httpx" not in source)
check("prototype has no 'import aiohttp'", "import aiohttp" not in source)
check("prototype has no openrouter call", "openrouter.ai" not in source)

# ── shadow module has no network imports ─────────────────────────────────────
import lib.hermes_cfo_loop_shadow as shadow_mod
shadow_source = pathlib.Path(shadow_mod.__file__).read_text()
check("shadow module has no 'import requests'", "import requests" not in shadow_source)
check("shadow module has no 'import httpx'", "import httpx" not in shadow_source)

# ── Run limited_primary without network env — no exception ───────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)
os.environ.pop("HERMES_CFO_MODEL_PROVIDER", None)
from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary
try:
    resp, used = run_cfo_limited_primary("create the implementation prompt now")
    check("limited_primary runs without network: no exception", True)
    check("limited_primary returns response", used is True or resp is None)
except Exception as e:
    check("limited_primary runs without network: no exception", False)
    print(f"  Exception: {e}")

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)

print(f"\nPhase 8C no network default: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
