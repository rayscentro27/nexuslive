"""
test_memory_v2_primary_mode_status.py
Verifies format_primary_status() output and 'show memory v2 primary status' command routing.
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


print("=== test_memory_v2_primary_mode_status ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- format_primary_status() structure --")
status = shadow.format_primary_status()
check("returns non-empty string", bool(status))
check("contains HERMES MEMORY V2 PRIMARY STATUS",
      "HERMES MEMORY V2 PRIMARY STATUS" in status)
check("contains Mode:", "Mode:" in status)
check("contains Safety:", "Safety:" in status)
check("contains Rollback:", "Rollback:" in status)
check("contains rollback command reference",
      "shadow" in status.lower() or "rollback" in status.lower())
check("contains artifacts/actions/decisions priority mention",
      "artifact" in status.lower() or "priority" in status.lower() or "override" in status.lower())

print("\n-- format_primary_status() when primary not active --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
status_shadow = shadow.format_primary_status()
check("shows mode when not primary", "primary not active" in status_shadow or "shadow" in status_shadow.lower())
os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- Command router routes memory_v2_primary_status --")
from hermes_command_router.intake import classify_intent

phrases = [
    "show memory v2 primary status",
    "memory v2 primary status",
    "v2 primary status",
    "is memory v2 primary active",
    "primary mode status",
]
for phrase in phrases:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == memory_v2_primary_status",
          intent == "memory_v2_primary_status")

print("\n-- Router has _plain_memory_v2_primary_status handler --")
from hermes_command_router.router import _PLAIN_INTENTS
check("_PLAIN_INTENTS has memory_v2_primary_status",
      "memory_v2_primary_status" in _PLAIN_INTENTS)
fn = _PLAIN_INTENTS.get("memory_v2_primary_status")
check("handler is callable", callable(fn))
if fn:
    result = fn()
    check("handler returns non-empty string", bool(result))
    check("handler result contains PRIMARY STATUS", "PRIMARY STATUS" in result or "PRIMARY" in result)

print("\n-- run_command routes primary status --")
from hermes_command_router.router import run_command
resp = run_command("show memory v2 primary status", source="cli")
check("run_command returns non-empty string", bool(resp))
check("run_command response contains PRIMARY", "PRIMARY" in resp.upper())

print("\n-- Evidence dump blocked for primary status phrases --")
from hermes_command_router.router import _EVIDENCE_DUMP_BLOCKED_PHRASES
check("'show memory v2 primary status' is blocked from evidence dump",
      "show memory v2 primary status" in _EVIDENCE_DUMP_BLOCKED_PHRASES)
check("'memory v2 primary status' is blocked",
      "memory v2 primary status" in _EVIDENCE_DUMP_BLOCKED_PHRASES)

print("\n-- SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
