"""test_phase8c_existing_commands_still_work.py — Phase 6A-8B commands unaffected."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from hermes_command_router.router import run_command
from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command

# ── Phase 8B status commands still work ──────────────────────────────────────
phase8b_cmds = [
    "show cfo shadow status",
    "cfo shadow status",
    "show cfo loop mode",
    "show cfo shadow traces",
    "cfo shadow traces",
    "compare cfo shadow",
    "cfo shadow compare",
]
for cmd in phase8b_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"Phase 8B '{cmd}': returns non-empty", bool(result) and len(result or "") > 10)

# ── Phase 8C status commands work ────────────────────────────────────────────
phase8c_cmds = [
    "show cfo limited primary status",
    "show cfo primary status",
    "rollback cfo loop to shadow",
]
for cmd in phase8c_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"Phase 8C '{cmd}': returns non-empty", bool(result) and len(result or "") > 10)

# ── Approval queue still works ────────────────────────────────────────────────
try:
    result = run_command("show approval queue", source="test")
    check("show approval queue: non-empty", bool(result) and len(result) > 10)
    check("show approval queue: has approval content", "approval" in (result or "").lower())
    check("show approval queue: no live answer sources", "live answer sources:" not in (result or ""))
except Exception as e:
    check("show approval queue: no exception", False)
    print(f"  Exception: {e}")

# ── CFO shadow command handler does NOT intercept non-CFO commands ────────────
non_shadow_cmds = [
    "show approval queue",
    "daily operating cycle plan",
    "how do we make money this week",
    "what are we working on",
]
for cmd in non_shadow_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"'{cmd}': handle_cfo_shadow_command returns None (not intercepted)", result is None)

# ── Approval queue not intercepted by limited_primary in test context ─────────
from lib.hermes_cfo_loop_shadow import should_run_cfo_limited_primary
check("should_run_cfo_limited_primary=False for CFO status cmds",
      not should_run_cfo_limited_primary("show cfo limited primary status"))
check("should_run_cfo_limited_primary=False for rollback",
      not should_run_cfo_limited_primary("rollback cfo loop to shadow"))

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C existing commands: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
