"""
test_memory_v2_comparison_mode_aware.py
Verifies compare memory v2 output varies correctly for each HERMES_MEMORY_V2_MODE.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_comparison_mode_aware ===\n")

from hermes_command_router.router import run_command
import lib.hermes_memory_v2_shadow as shadow

STALE_STRINGS = [
    "not primary yet",
    "Enable shadow mode",
    "Primary requires Ray approval",
    "ready for shadow-reader testing",
]

print("-- PRIMARY mode output --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
primary_resp = run_command("compare memory v2", source="cli")
check("primary: contains MEMORY READER COMPARISON", "MEMORY READER COMPARISON" in primary_resp)
check("primary: says PRIMARY for structured memory",
      "PRIMARY for structured memory" in primary_resp or "PRIMARY" in primary_resp)
for stale in STALE_STRINGS:
    check(f"primary: does NOT contain {stale!r}", stale not in primary_resp)
check("primary: contains excluded section",
      "excluded" in primary_resp.lower())
check("primary: recommendation is primary-aware",
      "primary" in primary_resp.lower() and "active" in primary_resp.lower())
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- SHADOW mode output --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
shadow_resp = run_command("compare memory v2", source="cli")
check("shadow: contains MEMORY READER COMPARISON", "MEMORY READER COMPARISON" in shadow_resp)
check("shadow: mentions shadow", "shadow" in shadow_resp.lower())
check("shadow: does NOT say 'not primary yet'", "not primary yet" not in shadow_resp)
check("shadow: does NOT say 'Enable shadow mode'", "Enable shadow mode" not in shadow_resp)
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- PREVIEW mode output --")
os.environ["HERMES_MEMORY_V2_MODE"] = "preview"
preview_resp = run_command("compare memory v2", source="cli")
check("preview: contains MEMORY READER COMPARISON", "MEMORY READER COMPARISON" in preview_resp)
check("preview: mentions preview", "preview" in preview_resp.lower())
check("preview: does NOT say 'not primary yet'", "not primary yet" not in preview_resp)
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- OFF mode output --")
os.environ["HERMES_MEMORY_V2_MODE"] = "off"
off_resp = run_command("compare memory v2", source="cli")
check("off: contains MEMORY READER COMPARISON", "MEMORY READER COMPARISON" in off_resp)
check("off: mentions off or not active",
      "off" in off_resp.lower() or "not active" in off_resp.lower())
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- No evidence dump in any mode --")
for mode, resp in [("primary", primary_resp), ("shadow", shadow_resp),
                   ("preview", preview_resp), ("off", off_resp)]:
    check(f"{mode}: no stale Executive Memory dump",
          "Executive Memory" not in resp or "archived" in resp.lower())

print("\n-- reader recommendation is neutral (no stale wording) --")
from lib.hermes_memory_v2_reader import compare_v2_with_current_memory
# Reader recommendation is mode-neutral; mode-specific text is in router output
cmp_data = compare_v2_with_current_memory()
rec_data = cmp_data.get("recommendation", "")
check("reader recommendation: does NOT say 'Enable shadow mode'",
      "Enable shadow mode" not in rec_data)
check("reader recommendation: does NOT say 'Primary requires Ray approval'",
      "Primary requires Ray approval" not in rec_data)
check("reader recommendation: does NOT say 'not primary live Telegram yet'",
      "not primary live Telegram yet" not in rec_data)

os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
rec_shadow_resp = run_command("compare memory v2", source="cli")
check("router output: shadow mode says shadow is active",
      "shadow" in rec_shadow_resp.lower())
check("router output: shadow does NOT say 'Enable shadow mode'",
      "Enable shadow mode" not in rec_shadow_resp)
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- _SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
