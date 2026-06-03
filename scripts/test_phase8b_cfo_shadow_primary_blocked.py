"""test_phase8b_cfo_shadow_primary_blocked.py — Primary mode blocked in Phase 8B."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

from lib.hermes_cfo_loop_shadow import (
    get_cfo_loop_mode, is_primary_mode_blocked, should_run_cfo_shadow,
    format_shadow_status,
)

# ── Primary mode is always blocked ────────────────────────────────────────────
check("is_primary_mode_blocked() is True", is_primary_mode_blocked() is True)

# ── HERMES_CFO_LOOP_MODE=primary falls back to limited_primary (Phase 8C) ─────
os.environ["HERMES_CFO_LOOP_MODE"] = "primary"
check("primary mode falls back to limited_primary", get_cfo_loop_mode() == "limited_primary")
check("primary mode: shadow NOT active (limited_primary is the fallback)", not should_run_cfo_shadow("test message"))

# ── format_shadow_status shows mode when primary set ─────────────────────────
status = format_shadow_status()
check("status with primary env: does not show 'mode: primary'", "mode: primary" not in status.lower())

# ── off still works ───────────────────────────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "off"
check("off: mode is off", get_cfo_loop_mode() == "off")
check("off: should_run=False", not should_run_cfo_shadow("test message"))

# ── Various primary-like strings are blocked ──────────────────────────────────
for val in ["primary", "PRIMARY", "Primary", " primary "]:
    os.environ["HERMES_CFO_LOOP_MODE"] = val
    result = get_cfo_loop_mode()
    check(f"'{val}' blocked → limited_primary or off", result in ("limited_primary", "off"))

os.environ.pop("HERMES_CFO_LOOP_MODE", None)

print(f"\nPhase 8B primary blocked: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
