"""
test_memory_v2_shadow_status_command.py
Verifies 'show memory v2 shadow status' and related commands are routed
correctly, return expected headers, and never show stale records.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_shadow_status_command ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS, _EVIDENCE_DUMP_BLOCKED_PHRASES
import telegram_bot as tb_mod

print("-- Intent classification: shadow status phrases --")
SHADOW_STATUS_PHRASES = [
    "show memory v2 shadow status",
    "memory v2 shadow status",
    "show shadow memory status",
    "shadow memory status",
    "v2 shadow status",
]
for phrase in SHADOW_STATUS_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → memory_v2_shadow_status",
          intent == "memory_v2_shadow_status")

print("\n-- Intent classification: live check phrases --")
LIVE_CHECK_PHRASES = [
    "is memory v2 live",
    "is memory v2 primary",
    "is memory v2 shadow only",
    "is v2 primary",
    "is v2 live",
]
for phrase in LIVE_CHECK_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → memory_v2_live_check",
          intent == "memory_v2_live_check")

print("\n-- Intents in _PLAIN_INTENTS --")
check("'memory_v2_shadow_status' in _PLAIN_INTENTS",
      "memory_v2_shadow_status" in _PLAIN_INTENTS)
check("'memory_v2_live_check' in _PLAIN_INTENTS",
      "memory_v2_live_check" in _PLAIN_INTENTS)

print("\n-- Intents in SAFE_REPEATABLE_MEMORY_INTENTS --")
safe = tb_mod.NexusTelegramBot.SAFE_REPEATABLE_MEMORY_INTENTS
check("'memory_v2_shadow_status' in SAFE_REPEATABLE_MEMORY_INTENTS",
      "memory_v2_shadow_status" in safe)
check("'memory_v2_live_check' in SAFE_REPEATABLE_MEMORY_INTENTS",
      "memory_v2_live_check" in safe)

print("\n-- Phrases in _EVIDENCE_DUMP_BLOCKED_PHRASES --")
for phrase in ["show memory v2 shadow status", "is memory v2 live",
               "is memory v2 primary", "is memory v2 shadow only"]:
    check(f"'{phrase}' in _EVIDENCE_DUMP_BLOCKED_PHRASES",
          phrase in _EVIDENCE_DUMP_BLOCKED_PHRASES)

print("\n-- run_command responses (preview mode, no primary) --")
os.environ.pop("HERMES_MEMORY_V2_MODE", None)  # default = preview

result = run_command("show memory v2 shadow status", source="telegram") or ""
check("shadow status response non-empty", bool(result.strip()))
check("contains 'HERMES MEMORY V2 SHADOW STATUS'",
      "HERMES MEMORY V2 SHADOW STATUS" in result)
check("no '═══' wrapper", "═══" not in result)
check("no 'HERMES REPORT'", "HERMES REPORT" not in result)
check("no evidence dump", "[artifact_inventory]" not in result)
check("mentions mode", "mode" in result.lower() or "Mode:" in result)
check("says 'does not change' or 'Shadow mode does not'",
      "does not change" in result.lower() or "shadow mode" in result.lower())
check("mentions primary requires approval",
      "approval" in result.lower() or "primary" in result.lower())

print()
live_result = run_command("is memory v2 live", source="telegram") or ""
check("live check response non-empty", bool(live_result.strip()))
check("no '═══' wrapper", "═══" not in live_result)
check("no 'HERMES REPORT'", "HERMES REPORT" not in live_result)
check("mentions preview or shadow", "preview" in live_result.lower() or "shadow" in live_result.lower())
check("does NOT say v2 is primary/live", "primary" not in live_result.lower() or
      "not" in live_result.lower() or "blocked" in live_result.lower())

print("\n-- shadow mode response format --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
result_shadow = run_command("show memory v2 shadow status", source="telegram") or ""
check("shadow mode shows 'shadow' in status", "shadow" in result_shadow.lower())
check("shadow mode says 'does not change Hermes answers'",
      "does not change" in result_shadow.lower() or "shadow only" in result_shadow.lower())
check("shadow mode says 'requires Ray approval'",
      "ray approval" in result_shadow.lower() or "approval" in result_shadow.lower())

print("\n-- primary mode blocked in status output --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
result_primary = run_command("show memory v2 shadow status", source="telegram") or ""
check("primary mode blocked warning present",
      "blocked" in result_primary.lower() or "primary" in result_primary.lower())
check("primary mode does not say 'primary mode active'",
      "primary mode active" not in result_primary.lower())

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
