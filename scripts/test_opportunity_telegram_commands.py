"""test_opportunity_telegram_commands.py — new Telegram commands route correctly."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_opportunity_telegram_commands ===")
from lib.hermes_internal_first import try_internal_first

COMMANDS = [
    ("Hermes, what did you find today?",       "daily_intake"),
    ("what sources did you find",              "daily_intake"),
    ("what sources are pending",               "daily_intake"),
    ("what can make money this week",          "monetization_actions"),
    ("show top monetization actions",          "monetization_actions"),
    ("top opportunities",                      "monetization_actions"),
    ("show rejected opportunities",            "rejected_opportunities"),
    ("what did you reject",                    "rejected_opportunities"),
    ("what scouts are working",                "scouts_working"),
    ("scout status",                           "scouts_working"),
    ("show daily research review",             "daily_review"),
    ("what should I review first",             "daily_review"),
    ("build content from the best opportunity", "build_content_from_opportunity"),
    ("what needs my approval",                 "needs_approval"),
    ("what requires approval",                 "needs_approval"),
    ("show approval needed",                   "needs_approval"),
]

for cmd, expected_topic in COMMANDS:
    result = try_internal_first(cmd)
    check(f"has reply: {cmd[:45]!r}", result is not None)
    if result:
        ok = result.matched_topic == expected_topic
        check(f"topic is {expected_topic}: {cmd[:40]!r}", ok)
        check(f"reply non-empty: {cmd[:30]!r}", len(result.text.strip()) > 10)
        check(f"no Traceback: {cmd[:30]!r}", "Traceback" not in result.text)
        check(f"no raw JSON dump: {cmd[:30]!r}", result.text.count("{") < 8)
        check(f"no 'Command timed out': {cmd[:30]!r}", "timed out" not in result.text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
