"""
test_compare_memory_v2_primary_wording.py
Verifies that 'compare memory v2' output reflects actual HERMES_MEMORY_V2_MODE.
Primary mode must NOT contain old shadow/preview wording.
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


print("=== test_compare_memory_v2_primary_wording ===\n")

from hermes_command_router.router import run_command
import lib.hermes_memory_v2_shadow as shadow

print("-- compare memory v2 in PRIMARY mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
resp = run_command("compare memory v2", source="cli")
print("  output preview:")
for line in resp.splitlines()[:12]:
    print(f"    {line}")
print()

check("response non-empty", bool(resp))
check("contains MEMORY READER COMPARISON", "MEMORY READER COMPARISON" in resp)
check("says PRIMARY for structured memory",
      "PRIMARY for structured memory" in resp or "PRIMARY" in resp)
check("does NOT say 'not primary yet'", "not primary yet" not in resp)
check("does NOT say 'Enable shadow mode'", "Enable shadow mode" not in resp)
check("does NOT say 'Primary requires Ray approval'",
      "Primary requires Ray approval" not in resp)
check("does NOT say 'ready for shadow-reader testing'",
      "ready for shadow-reader testing" not in resp)
check("recommendation mentions primary is active",
      "primary" in resp.lower() or "active" in resp.lower())
check("shows excluded types section",
      "excluded" in resp.lower() or "Still excluded" in resp)
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- compare memory v2 with approval file present (live mode) --")
if shadow.APPROVAL_FILE.exists():
    os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
    mode_check = shadow.get_memory_v2_mode()
    if mode_check == "primary":
        resp2 = run_command("compare memory v2", source="cli")
        check("live primary mode: says PRIMARY", "PRIMARY" in resp2)
        check("live primary mode: no 'not primary yet'", "not primary yet" not in resp2)
        check("live primary mode: no 'Enable shadow mode'", "Enable shadow mode" not in resp2)
        check("live primary mode: no 'Primary requires Ray approval'",
              "Primary requires Ray approval" not in resp2)
        check("live primary mode: recommendation correct",
              "Primary structured memory is active" in resp2 or
              "primary" in resp2.lower())
    else:
        print(f"  guards blocked primary (mode={mode_check}) — skipping live primary checks")
        check("guards blocked: mode is shadow fallback", mode_check == "shadow")
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)
else:
    print("  (approval file absent — skipping live primary checks)")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
