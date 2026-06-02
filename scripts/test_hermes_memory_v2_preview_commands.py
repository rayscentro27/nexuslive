"""
test_hermes_memory_v2_preview_commands.py
Verifies Telegram command routing for all v2 preview commands.
Checks: intent classification, _PLAIN_INTENTS registration, response content,
no evidence dump, no stale markers, SAFE_REPEATABLE_MEMORY_INTENTS membership.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_preview_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS, _EVIDENCE_DUMP_BLOCKED_PHRASES
import telegram_bot as tb_mod

INTENT_PHRASE_MAP = {
    "memory_v2_preview": [
        "show memory v2 preview", "preview memory v2", "show hermes memory v2",
        "show v2 preview",
    ],
    "memory_v2_compare": [
        "compare memory v2", "compare current memory and v2", "memory comparison",
    ],
    "memory_v2_rules": [
        "show memory v2 rules", "memory v2 rules",
    ],
    "memory_v2_status": [
        "show memory v2 status", "memory v2 status",
    ],
}

print("-- Intent classification --")
for expected_intent, phrases in INTENT_PHRASE_MAP.items():
    for phrase in phrases:
        intent, _, _ = classify_intent(phrase)
        check(f"'{phrase[:45]}' → {expected_intent}", intent == expected_intent)

print("\n-- All v2 intents in _PLAIN_INTENTS --")
for intent in INTENT_PHRASE_MAP:
    check(f"'{intent}' in _PLAIN_INTENTS", intent in _PLAIN_INTENTS)
    if intent in _PLAIN_INTENTS:
        handler = _PLAIN_INTENTS[intent]
        result = handler()
        check(f"_PLAIN_INTENTS['{intent}']() returns str", isinstance(result, str))
        check(f"_PLAIN_INTENTS['{intent}']() non-empty", bool(result and result.strip()))

print("\n-- All v2 intents in SAFE_REPEATABLE_MEMORY_INTENTS --")
safe = tb_mod.NexusTelegramBot.SAFE_REPEATABLE_MEMORY_INTENTS
for intent in INTENT_PHRASE_MAP:
    check(f"'{intent}' in SAFE_REPEATABLE_MEMORY_INTENTS", intent in safe)

print("\n-- v2 phrases in _EVIDENCE_DUMP_BLOCKED_PHRASES --")
for phrase in ["show memory v2 preview", "compare memory v2", "show memory v2 status",
               "show memory v2 rules", "preview memory v2"]:
    check(f"'{phrase}' in blocked phrases", phrase in _EVIDENCE_DUMP_BLOCKED_PHRASES)

print("\n-- run_command responses for v2 preview commands --")
expected_headers = {
    "show memory v2 preview":  "HERMES MEMORY V2 PREVIEW",
    "compare memory v2":       "MEMORY READER COMPARISON",
    "show memory v2 rules":    "MEMORY V2 OPERATING RULES",
    "show memory v2 status":   "HERMES MEMORY V2 STATUS",
}
for cmd, expected_header in expected_headers.items():
    result = run_command(cmd, source="telegram") or ""
    check(f"'{cmd[:35]}' non-empty", bool(result.strip()))
    check(f"'{cmd[:35]}' contains '{expected_header}'", expected_header in result)
    check(f"'{cmd[:35]}' no '═══' wrapper", "═══" not in result)
    check(f"'{cmd[:35]}' no 'HERMES REPORT'", "HERMES REPORT" not in result)
    check(f"'{cmd[:35]}' no evidence dump", "[artifact_inventory]" not in result)
    check(f"'{cmd[:35]}' says preview/not primary",
          "preview" in result.lower() or "not" in result.lower())
    print()

print(f"{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
