"""
test_hermes_operator_commands.py
Verifies operator Telegram commands route to internal handlers.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_operator_commands ===")

from lib.hermes_internal_first import try_internal_first

COMMAND_CASES = [
    ("what are our goals", "goals"),
    ("show goals", "goals"),
    ("what tools do you have", "tools_scouts"),
    ("what scouts are available", "tools_scouts"),
    ("what are you working on", "action_queue"),
    ("show action queue", "action_queue"),
    ("what is blocked", "action_queue"),
    ("show decision log", "decision_log"),
    ("what did you decide", "decision_log"),
    ("run the operating loop", "operating_loop"),
    ("explain that simply", "plain_english"),
    ("show technical details", "technical_details"),
]

for query, expected_topic in COMMAND_CASES:
    result = try_internal_first(query)
    check(f"has reply for: {query[:45]}", result is not None)
    if result:
        check(f"topic is {expected_topic}: '{query[:40]}'",
              result.matched_topic == expected_topic)
        check(f"reply non-empty: '{query[:40]}'", len(result.text.strip()) > 20)
        check(f"no raw tool call in reply: '{query[:35]}'",
              "search_files(" not in result.text)
        check(f"no 'Command timed out': '{query[:35]}'",
              "Command timed out" not in result.text)

# Specific content checks
result_goals = try_internal_first("what are our goals")
if result_goals:
    check("goals reply mentions goal or priority",
          "goal" in result_goals.text.lower() or "priority" in result_goals.text.lower())

result_scouts = try_internal_first("what scouts are available")
if result_scouts:
    check("scouts reply mentions scout", "scout" in result_scouts.text.lower())

result_explain = try_internal_first("explain that simply")
if result_explain:
    check("plain english reply mentions plain language",
          "plain" in result_explain.text.lower() or "language" in result_explain.text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
