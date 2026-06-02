"""
test_memory_v2_primary_blocked.py
Verifies that HERMES_MEMORY_V2_MODE=primary is blocked in Phase 4E.
Primary mode must never silently activate live Telegram v2 switching.
"""
import sys, os, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_primary_blocked ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- primary mode is NOT in _VALID_MODES --")
check("'primary' not in _VALID_MODES",
      shadow.MODE_PRIMARY not in shadow._VALID_MODES)

print("\n-- get_memory_v2_mode() blocks primary --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
mode = shadow.get_memory_v2_mode()
check("primary env var returns shadow or preview (not primary)", mode != "primary")
check("returns a valid mode", mode in shadow._VALID_MODES)

print("\n-- is_primary_mode_requested() detects it --")
check("is_primary_mode_requested() True when env=primary",
      shadow.is_primary_mode_requested() is True)

print("\n-- format_shadow_status() warns about primary when env=primary --")
status = shadow.format_shadow_status()
check("format_shadow_status contains 'Primary' warning",
      "Primary" in status or "primary" in status.lower())
check("format_shadow_status contains 'blocked'",
      "blocked" in status.lower())
check("format_shadow_status does NOT say primary is active",
      "primary mode active" not in status.lower())

print("\n-- format_v2_live_status() blocks primary --")
live = shadow.format_v2_live_status()
check("live status says 'not enabled' or 'blocked'",
      "not enabled" in live.lower() or "blocked" in live.lower())
check("live status says 'requires Ray approval'",
      "ray approval" in live.lower())

print("\n-- run_command shadow status returns blocking message --")
from hermes_command_router.router import run_command
result = run_command("show memory v2 shadow status", source="telegram") or ""
check("shadow status response non-empty", bool(result.strip()))
check("shadow status mentions primary blocked or warning",
      "blocked" in result.lower() or "Primary" in result)

print("\n-- source code does not allow primary mode silently --")
src = inspect.getsource(shadow)
check("source blocks primary with warning log",
      "primary" in src and ("warning" in src.lower() or "blocked" in src.lower()))
check("source never sets live reader to primary",
      "switch.*primary" not in src.lower() or "blocked" in src.lower())

print("\n-- telegram_bot does not switch reader when mode=primary --")
import telegram_bot as tb_mod
tb_src = inspect.getsource(tb_mod)
check("telegram_bot shadow block uses is_shadow_mode_enabled guard",
      "is_shadow_mode_enabled" in tb_src)
check("no unconditional primary reader switch in telegram_bot",
      "memory_v2_primary" not in tb_src or "blocked" in tb_src.lower())

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
