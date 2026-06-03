"""test_phase8b_cfo_shadow_no_network_default.py — No network calls in mock/shadow mode."""
import sys, os
import unittest.mock as mock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

# ── No network calls in mock mode ─────────────────────────────────────────────
with mock.patch("socket.socket") as mock_socket, \
     mock.patch("urllib.request.urlopen") as mock_url:

    from lib.hermes_cfo_loop_shadow import run_cfo_shadow_for_message
    from prototypes.hermes_agentic_cfo_loop import MOCK_MODE

    check("MOCK_MODE is True", MOCK_MODE is True)

    messages = [
        "how do we make money this week",
        "what are all the scouts doing",
        "i approve them all",
        "what is claude working on",
        "explain your recommendation in plain language",
    ]
    for msg in messages:
        try:
            trace = run_cfo_shadow_for_message(msg, live_response="TEST LIVE RESPONSE")
            check(f"no exception: {msg[:40]}", True)
            check(f"trace returned: {msg[:30]}", isinstance(trace, dict))
        except Exception as e:
            check(f"no exception: {msg[:40]}", False)

    check("socket.socket not called during shadow", mock_socket.call_count == 0)
    check("urllib.urlopen not called during shadow", mock_url.call_count == 0)

# ── Provider mock is default ──────────────────────────────────────────────────
from lib.hermes_cfo_loop_shadow import get_cfo_loop_provider
check("provider is mock", get_cfo_loop_provider() == "mock")

# ── No supabase client in shadow module ───────────────────────────────────────
import lib.hermes_cfo_loop_shadow as shadow_mod
src = open(shadow_mod.__file__).read()
check("no 'import supabase' in shadow module", "import supabase" not in src.lower() and "from supabase" not in src.lower())
check("no 'import requests' in shadow module", "import requests" not in src)
check("no 'import httpx' in shadow module", "import httpx" not in src)
check("no 'import aiohttp' in shadow module", "import aiohttp" not in src)

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B no network default: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
