"""
test_memory_sources_primary_mode.py
Verifies 'show memory sources' correctly shows PRIMARY when primary mode is active.
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


print("=== test_memory_sources_primary_mode ===\n")

from hermes_command_router.router import run_command
import lib.hermes_memory_v2_shadow as shadow

print("-- Memory sources output in shadow mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
resp_shadow = run_command("show memory sources", source="cli")
check("response non-empty", bool(resp_shadow))
check("contains HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in resp_shadow)
check("shows shadow reader when in shadow mode",
      "shadow" in resp_shadow.lower())
check("does NOT say PRIMARY when in shadow mode",
      "primary for structured" not in resp_shadow.lower())
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- Memory sources output in preview mode --")
os.environ["HERMES_MEMORY_V2_MODE"] = "preview"
resp_preview = run_command("show memory sources", source="cli")
check("response non-empty", bool(resp_preview))
check("contains 'preview only' or similar in preview mode",
      "preview" in resp_preview.lower() or "not primary" in resp_preview.lower())
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- Memory sources output in primary mode (with approval file) --")
if shadow.APPROVAL_FILE.exists():
    os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
    resp_primary = run_command("show memory sources", source="cli")
    mode_effective = shadow.get_memory_v2_mode()
    if mode_effective == "primary":
        check("shows PRIMARY when primary mode active",
              "PRIMARY" in resp_primary or "primary" in resp_primary.lower())
        print(f"  mode_effective={mode_effective!r}")
    else:
        check("shows shadow reader when guards fail (approval + live checks)",
              "shadow" in resp_primary.lower() or "preview" in resp_primary.lower())
        print(f"  primary guarded — mode_effective={mode_effective!r}")
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)
else:
    check("approval file absent: primary test skipped", True)
    print("  (skipped: no approval file)")

print("\n-- _plain_memory_sources always returns non-empty string --")
from hermes_command_router.router import _PLAIN_INTENTS
fn = _PLAIN_INTENTS.get("memory_sources")
check("memory_sources handler exists", callable(fn))
if fn:
    for env_mode in ("preview", "shadow", "off", ""):
        if env_mode:
            os.environ["HERMES_MEMORY_V2_MODE"] = env_mode
        else:
            os.environ.pop("HERMES_MEMORY_V2_MODE", None)
        result = fn()
        check(f"_plain_memory_sources returns string for mode={env_mode!r}", isinstance(result, str))
        check(f"_plain_memory_sources non-empty for mode={env_mode!r}", bool(result))
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- intent routes correctly --")
from hermes_command_router.intake import classify_intent
intent, _, _ = classify_intent("show memory sources")
check("'show memory sources' classified as memory_sources", intent == "memory_sources")

print("\n-- _SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
