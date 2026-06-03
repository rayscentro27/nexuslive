"""test_phase8b_cfo_shadow_mode_config.py — HERMES_CFO_LOOP_MODE config."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

# ── Default is off ────────────────────────────────────────────────────────────
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

# Reimport after clearing env
import importlib
import lib.hermes_cfo_loop_shadow as shadow_mod
importlib.reload(shadow_mod)

from lib.hermes_cfo_loop_shadow import (
    get_cfo_loop_mode, get_cfo_loop_provider, is_shadow_mode_active,
    is_limited_primary_mode_active, is_primary_mode_blocked, should_run_cfo_shadow,
    ALLOWLISTED_INTENTS, HARD_BLOCKED_INTENTS, LIMITED_PRIMARY_CONFIDENCE_THRESHOLD,
)

check("default mode is off", get_cfo_loop_mode() == "off")
check("default provider is mock", get_cfo_loop_provider() == "mock")
check("shadow is not active by default", not is_shadow_mode_active())
check("primary is blocked", is_primary_mode_blocked() is True)

# ── shadow mode ───────────────────────────────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
check("shadow mode recognized", get_cfo_loop_mode() == "shadow")
check("shadow mode is active", is_shadow_mode_active())
check("should_run_cfo_shadow=True when shadow+message", should_run_cfo_shadow("how do we make money"))

# ── primary mode is blocked (falls back to limited_primary in Phase 8C) ──────
os.environ["HERMES_CFO_LOOP_MODE"] = "primary"
check("primary falls back to limited_primary", get_cfo_loop_mode() == "limited_primary")
check("primary is blocked", is_primary_mode_blocked())

# ── invalid value defaults to off ────────────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "invalid_value_xyz"
check("invalid value defaults to off", get_cfo_loop_mode() == "off")

# ── off mode ─────────────────────────────────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "off"
check("off mode: should_run=False", not should_run_cfo_shadow("any message"))

# ── providers ─────────────────────────────────────────────────────────────────
for provider in ("mock", "openrouter", "deepseek", "local"):
    os.environ["HERMES_CFO_LOOP_PROVIDER"] = provider
    check(f"provider '{provider}' recognized", get_cfo_loop_provider() == provider)

os.environ["HERMES_CFO_LOOP_PROVIDER"] = "unknown_provider"
check("invalid provider defaults to mock", get_cfo_loop_provider() == "mock")

# ── limited_primary mode ─────────────────────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
check("limited_primary mode recognized", get_cfo_loop_mode() == "limited_primary")
check("limited_primary is active", is_limited_primary_mode_active())
check("shadow is NOT active in limited_primary", not is_shadow_mode_active())
check("should_run_cfo_shadow is False in limited_primary", not should_run_cfo_shadow("any message"))
check("allowlist is non-empty", len(ALLOWLISTED_INTENTS) >= 8)
check("hard blocked list is non-empty", len(HARD_BLOCKED_INTENTS) >= 5)
check("threshold is 0.80", LIMITED_PRIMARY_CONFIDENCE_THRESHOLD == 0.80)

# ── shadow commands not shadow-traced (no recursive tracing) ──────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
check("shadow cmd not traced: show cfo shadow status", not should_run_cfo_shadow("show cfo shadow status"))
check("shadow cmd not traced: compare cfo shadow", not should_run_cfo_shadow("compare cfo shadow"))
check("short message not traced", not should_run_cfo_shadow("x"))

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8B shadow mode config: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
