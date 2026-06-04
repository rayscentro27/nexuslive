"""test_phase9_limited_primary_precedes_legacy.py — limited primary wins before legacy router/chat fallback."""
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
import telegram_bot

original_route = telegram_bot.TelegramRouter.route_incoming_message

try:
    def fail_route(self, text):
        raise AssertionError("legacy router should not run for limited-primary allowlisted intents")

    telegram_bot.TelegramRouter.route_incoming_message = fail_route
    response = bot.handle_inbound_message("what did we work on today")
    check("limited primary answered day summary before legacy router", "day summary" in response.lower())
finally:
    telegram_bot.TelegramRouter.route_incoming_message = original_route
    cleanup_env()

print(f"\nPhase 9 limited primary precedence: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
