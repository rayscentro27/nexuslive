"""test_phase8c_limited_primary_config.py — limited_primary mode config."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

import importlib

# ── limited_primary mode exists and is recognized ────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
import lib.hermes_cfo_loop_shadow as shadow_mod
importlib.reload(shadow_mod)
from lib.hermes_cfo_loop_shadow import (
    get_cfo_loop_mode, is_limited_primary_mode_active, is_shadow_mode_active,
    is_primary_mode_blocked, should_run_cfo_shadow, should_run_cfo_limited_primary,
    ALLOWLISTED_INTENTS, HARD_BLOCKED_INTENTS, LIMITED_PRIMARY_CONFIDENCE_THRESHOLD,
    format_limited_primary_status, handle_cfo_shadow_command,
)
check("limited_primary mode recognized", get_cfo_loop_mode() == "limited_primary")
check("is_limited_primary_mode_active is True", is_limited_primary_mode_active())
check("shadow is NOT active in limited_primary", not is_shadow_mode_active())
check("full primary is blocked", is_primary_mode_blocked())

# ── primary falls back to limited_primary (full primary still blocked) ────────
os.environ["HERMES_CFO_LOOP_MODE"] = "primary"
check("full primary falls back to limited_primary", get_cfo_loop_mode() == "limited_primary")

# ── shadow mode gate does NOT fire in limited_primary ─────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
check("should_run_cfo_shadow=False in limited_primary", not should_run_cfo_shadow("any message"))
check("should_run_cfo_limited_primary=True for real message", should_run_cfo_limited_primary("how do we make money"))

# ── status command commands ───────────────────────────────────────────────────
status_cmds = [
    "show cfo limited primary status",
    "cfo limited primary status",
    "show cfo primary status",
    "cfo primary status",
]
for cmd in status_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"'{cmd}': non-empty response", bool(result) and len(result) > 20)
    check(f"'{cmd}': contains limited primary", "limited" in (result or "").lower() or "primary" in (result or "").lower())

# ── rollback command ──────────────────────────────────────────────────────────
rb = handle_cfo_shadow_command("rollback cfo loop to shadow")
check("rollback command returns response", bool(rb) and len(rb) > 20)
check("rollback response has ROLLED BACK", "rolled back" in (rb or "").lower())
check("rollback has manual instructions", "launchctl" in (rb or "").lower())

# ── ALLOWLISTED_INTENTS ───────────────────────────────────────────────────────
required_allowlist = {
    "implementation_prompt_request", "acknowledgement_check", "scout_status",
    "approval_bulk_request", "draft_comparison", "summary_of_day", "implement_now",
}
for intent in required_allowlist:
    check(f"allowlist contains '{intent}'", intent in ALLOWLISTED_INTENTS)

# ── HARD_BLOCKED_INTENTS ──────────────────────────────────────────────────────
required_blocked = {
    "publish_content", "send_email", "payment_activation", "affiliate_application",
    "production_deploy", "live_trading",
}
for intent in required_blocked:
    check(f"hard_blocked contains '{intent}'", intent in HARD_BLOCKED_INTENTS)

# ── Threshold ─────────────────────────────────────────────────────────────────
check("confidence threshold is 0.80", LIMITED_PRIMARY_CONFIDENCE_THRESHOLD == 0.80)

# ── limited_primary status format ────────────────────────────────────────────
status = format_limited_primary_status()
check("status has allowlisted intents section", "allowlisted" in status.lower())
check("status has full primary blocked", "blocked" in status.lower())
check("status has rollback instructions", "rollback" in status.lower() or "launchctl" in status.lower())
check("status has safety note", "safety" in status.lower())

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C limited primary config: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
