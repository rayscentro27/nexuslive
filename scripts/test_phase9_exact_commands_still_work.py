"""test_phase9_exact_commands_still_work.py — key exact commands still work after Phase 9 cleanup."""
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
    checks = {
        "show cfo limited primary status": "cfo loop limited primary status",
        "show memory v2 primary status": "hermes memory v2 primary status",
        "show raw evidence": "raw evidence",
        "Hermes, run daily operating cycle": "today's nexus plan",
        "review launch packet": "funding readiness approval summary",
    }
    for message, expected in checks.items():
        response = bot.handle_inbound_message(message)
        check(f"exact command works: {message}", expected in (response or "").lower())
finally:
    cleanup_env()

print(f"\nPhase 9 exact commands still work: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
