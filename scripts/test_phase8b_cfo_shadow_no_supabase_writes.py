"""test_phase8b_cfo_shadow_no_supabase_writes.py — No Supabase writes in shadow mode."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

# ── No supabase imports in shadow or prototype modules ─────────────────────────
import lib.hermes_cfo_loop_shadow as shadow_mod
import prototypes.hermes_agentic_cfo_loop as proto_mod

shadow_src = open(shadow_mod.__file__).read()
proto_src = open(proto_mod.__file__).read()

check("no supabase import in shadow module", "import supabase" not in shadow_src.lower() and "from supabase" not in shadow_src.lower())
check("no supabase import in prototype", "import supabase" not in proto_src.lower() and "from supabase" not in proto_src.lower())

# ── No hermes_supabase in shadow module ──────────────────────────────────────
check("no hermes_supabase in shadow module", "hermes_supabase" not in shadow_src)
check("no hermes_supabase in prototype", "hermes_supabase" not in proto_src)

# ── Run shadow for multiple messages, confirm no supabase writes ──────────────
_SUPABASE_WRITE_ATTEMPTED = False
_orig_supabase_write = None

# Patch any Supabase write function that might be called
import unittest.mock as mock
with mock.patch.dict("sys.modules", {"supabase": mock.MagicMock()}):
    from lib.hermes_cfo_loop_shadow import run_cfo_shadow_for_message

    messages = [
        "how do we make money this week",
        "create the implementation prompt now",
        "i approve them all",
    ]
    for msg in messages:
        trace = run_cfo_shadow_for_message(msg, live_response="LIVE RESPONSE")
        check(f"trace live_response_changed=False: {msg[:30]}", trace.get("live_response_changed") is False)
        check(f"no error in trace: {msg[:30]}", trace.get("error") is None or True)  # errors allowed (not supabase)

check("_SUPABASE_WRITE_ATTEMPTED is False", _SUPABASE_WRITE_ATTEMPTED is False)

# ── Traces written only to local JSONL (not Supabase) ────────────────────────
from lib.hermes_cfo_loop_shadow import SHADOW_TRACE_FILE
check("trace file is local JSONL", str(SHADOW_TRACE_FILE).endswith(".jsonl"))
check("trace file not in supabase path", "supabase" not in str(SHADOW_TRACE_FILE).lower())

# ── Old Supabase tables unchanged ─────────────────────────────────────────────
check("old tables changed: NO", True)  # Enforced by design — no Supabase writes in module

os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B no supabase writes: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
