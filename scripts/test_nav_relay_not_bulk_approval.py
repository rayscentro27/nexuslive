"""test_nav_relay_not_bulk_approval.py — Nav/Relay approval recall never falls into bulk approval output."""
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
    response = bot.handle_inbound_message("what did I approve for Nav and Relay?")
    lower = response.lower()
    check("not approval bulk check", "approval bulk check" not in lower)
    check("no lesson approvals shown", "lesson:" not in lower)
    check("no lead magnet approvals shown", "lead magnet" not in lower)
    check("no video approvals shown", "video" not in lower)
    check("no newsletter approvals shown", "newsletter" not in lower)
finally:
    cleanup_env()

print(f"\nNav/Relay not bulk approval: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
