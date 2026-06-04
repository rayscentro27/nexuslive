"""test_nav_relay_approval_summary_route.py — Nav/Relay approval recall routes deterministically."""
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
    phrases = [
        "what did I approve for Nav and Relay?",
        "what did I approve for nav.com and relay",
        "what did I approve for Nav",
        "what did I approve for Relay",
        "show Nav Relay approval",
        "show Nav and Relay monetization decision",
        "what is the Nav Relay decision",
        "did I approve Nav and Relay",
    ]
    for phrase in phrases:
        response = bot.handle_inbound_message(phrase)
        lower = response.lower()
        check(f"{phrase}: header present", response.startswith("NAV / RELAY APPROVAL SUMMARY"))
        check(f"{phrase}: nav approved text present", "nav.com as the first monetization path for internal preparation" in lower)
        check(f"{phrase}: relay approved text present", "relay as the second monetization path for internal preparation" in lower)
finally:
    cleanup_env()

print(f"\nNav/Relay approval summary route: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
