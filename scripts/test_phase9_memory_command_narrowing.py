"""test_phase9_memory_command_narrowing.py — _try_memory_command only handles memory intents."""
import sys

from phase9_test_helpers import cleanup_env, make_bot

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


bot = make_bot()
try:
    result = bot._try_memory_command("show memory v2 primary status")
    check("true memory command returns response", bool(result) and "memory v2" in result.lower())

    non_memory_phrases = [
        "what changed in the draft",
        "i approve them all",
        "create the implementation prompt now",
        "what did we work on today",
        "review the funding readiness launch packet and give me the approval decision summary",
        "what are all the scouts doing right now",
        "what should i approve first",
        "what is the current revenue packet score",
        "which asset is closest to launch ready",
    ]
    for phrase in non_memory_phrases:
        check(f"non-memory phrase bypasses _try_memory_command: {phrase}", bot._try_memory_command(phrase) is None)
finally:
    cleanup_env()

print(f"\nPhase 9 memory command narrowing: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
