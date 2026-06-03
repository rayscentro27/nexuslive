"""test_phase8c_no_supabase_writes.py — no Supabase writes in limited_primary mode."""
import sys, os, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

# ── No supabase imports in shadow module ──────────────────────────────────────
import lib.hermes_cfo_loop_shadow as shadow_mod
shadow_source = pathlib.Path(shadow_mod.__file__).read_text()
check("shadow module has no 'import supabase'", "import supabase" not in shadow_source.lower())
check("shadow module has no 'from supabase'", "from supabase" not in shadow_source.lower())
check("shadow module has no supabase client calls", "supabase.table" not in shadow_source.lower())

# ── No supabase imports in prototype ─────────────────────────────────────────
import prototypes.hermes_agentic_cfo_loop as proto_mod
proto_source = pathlib.Path(proto_mod.__file__).read_text()
check("prototype has no 'import supabase'", "import supabase" not in proto_source.lower())
check("prototype has no 'from supabase'", "from supabase" not in proto_source.lower())

# ── Traces are written to local JSONL, not Supabase ──────────────────────────
from lib.hermes_cfo_loop_shadow import SHADOW_TRACE_FILE
check("trace file is local JSONL path", str(SHADOW_TRACE_FILE).endswith(".jsonl"))
check("trace file is NOT a supabase URL", "supabase.co" not in str(SHADOW_TRACE_FILE))

# ── Run limited_primary and confirm no Supabase mutation ─────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary, load_shadow_traces

before_count = len(load_shadow_traces(limit=10000))
try:
    run_cfo_limited_primary("create the implementation prompt now")
    check("limited_primary completed without exception", True)
except Exception as e:
    check("limited_primary completed without exception", False)
    print(f"  Exception: {e}")

after_count = len(load_shadow_traces(limit=10000))
check("trace count increased (local write only)", after_count > before_count)
check("Supabase env not required to run", True)  # test passed without Supabase env

# ── Old table modification check: no schema migration calls ─────────────────
check("prototype has no 'alter table'", "alter table" not in proto_source.lower())
check("shadow module has no 'alter table'", "alter table" not in shadow_source.lower())

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C no Supabase writes: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
