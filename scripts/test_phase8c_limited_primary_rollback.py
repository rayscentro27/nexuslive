"""test_phase8c_limited_primary_rollback.py — rollback command and instructions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import (
    handle_cfo_shadow_command, format_rollback_instructions,
)

# ── Rollback command returns proper response ──────────────────────────────────
rollback_cmds = [
    "rollback cfo loop to shadow",
    "rollback cfo to shadow",
]
for cmd in rollback_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"'{cmd}': returns non-empty", bool(result) and len(result or "") > 20)
    check(f"'{cmd}': has ROLLED BACK text", "rolled back" in (result or "").lower())
    check(f"'{cmd}': has launchctl instructions", "launchctl" in (result or "").lower())
    check(f"'{cmd}': shows manual steps", "unload" in (result or "").lower())
    check(f"'{cmd}': shows HERMES_CFO_LOOP_MODE=shadow", "shadow" in (result or "").lower())

# ── format_rollback_instructions directly ────────────────────────────────────
rb = format_rollback_instructions()
check("rollback: header is CFO LOOP ROLLED BACK TO SHADOW", "CFO LOOP ROLLED BACK TO SHADOW" in rb)
check("rollback: step 1 (edit plist)", "plist" in rb.lower())
check("rollback: set to shadow", "shadow" in rb.lower())
check("rollback: launchctl unload command", "launchctl unload" in rb.lower())
check("rollback: launchctl load command", "launchctl load" in rb.lower())
check("rollback: approval boundary", "approval boundary" in rb.lower())
check("rollback: explains cannot edit from Telegram", "telegram" in rb.lower() or "directly" in rb.lower())

# ── Rollback command is not intercepted as shadow trace ──────────────────────
from lib.hermes_cfo_loop_shadow import should_run_cfo_limited_primary
check("rollback cmd not treated as limited_primary message",
      not should_run_cfo_limited_primary("rollback cfo loop to shadow"))

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C rollback: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
