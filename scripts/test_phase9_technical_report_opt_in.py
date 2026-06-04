"""test_phase9_technical_report_opt_in.py — technical evidence appears only on explicit opt-in phrases."""
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
    raw = bot.handle_inbound_message("show raw evidence")
    check("show raw evidence returns raw evidence header", "raw evidence" in raw.lower())

    tech = bot.handle_inbound_message("show technical report")
    check("show technical report returns technical header", tech.startswith("TECHNICAL REPORT"))
    check("show technical report includes raw evidence", "raw evidence" in tech.lower())

    full = bot.handle_inbound_message("show full HERMES REPORT")
    check("show full HERMES REPORT uses technical path", "technical report" in full.lower())
finally:
    cleanup_env()

print(f"\nPhase 9 technical report opt-in: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
