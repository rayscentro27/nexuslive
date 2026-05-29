"""
test_provider_mode_commands.py
Verifies provider mode commands route to the internal handler,
never fall through to LLM, and return meaningful replies.
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

print("=== test_provider_mode_commands ===")

from lib.hermes_internal_first import try_internal_first

COMMANDS = [
    "show provider mode",
    "what brain are you using",
    "what brain",
    "provider mode",
    "which model are you using",
    "what llm",
    "current provider",
]

for cmd in COMMANDS:
    result = try_internal_first(cmd)
    check(f"has internal reply for: {cmd[:45]}", result is not None)
    if result:
        check(f"topic is provider_mode: {cmd[:40]}", result.matched_topic == "provider_mode")
        check(f"source is provider_policy: {cmd[:40]}", "provider_policy" in result.source or "provider" in result.source)
        check(f"reply is non-empty: {cmd[:40]}", len(result.text.strip()) > 20)
        check(f"no raw tool call in reply: {cmd[:40]}", "search_files(" not in result.text)

# enable gateway command
result_enable = try_internal_first("enable gateway")
check("enable gateway returns reply", result_enable is not None)
if result_enable:
    check("enable gateway mentions HERMES_ALLOW_HERMES_GATEWAY",
          "HERMES_ALLOW_HERMES_GATEWAY" in result_enable.text)
    check("enable gateway mentions experimental", "experimental" in result_enable.text.lower())

# disable gateway / reliable mode command
result_disable = try_internal_first("use reliable mode")
check("use reliable mode returns reply", result_disable is not None)
if result_disable:
    check("use reliable mode mentions gateway=false or disable",
          "false" in result_disable.text.lower() or "disable" in result_disable.text.lower())
    check("use reliable mode mentions reliable", "reliable" in result_disable.text.lower())

# disable gateway command
result_disable2 = try_internal_first("disable gateway")
check("disable gateway returns reply", result_disable2 is not None)
if result_disable2:
    check("disable gateway mentions reliable or false",
          "reliable" in result_disable2.text.lower() or "false" in result_disable2.text.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
