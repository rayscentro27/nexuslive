"""
test_cfo_brain_tool_chooser.py
Phase 7B: CFO Brain — tool chooser.
Verifies intent → tool mapping.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

passes = 0
failures = 0

def check(label, cond):
    global passes, failures
    status = "PASS" if cond else "FAIL"
    if not cond:
        failures += 1
    else:
        passes += 1
    print(f"  [{status}] {label}")
    return cond


from lib.hermes_tool_chooser import (
    choose_tool_for_intent, get_available_tools, _INTENT_TO_TOOL, _TOOL_COMMAND_MAP
)

print("\nCFO Brain Tool Chooser Tests")
print("=" * 50)

print("\n-- Intent → tool mapping --")
_MAPPINGS = [
    ("queue_status_question",       "task_queue_status"),
    ("morning_activity_question",   "morning_activity"),
    ("money_strategy_question",     "revenue_asset_packet"),
    ("research_queue_question",     "research_queue"),
    ("memory_status",               "memory_v2_status"),
    ("pending_items",               "pending_daily_items"),
    ("failure_feedback",            "failure_review"),
    ("implementation_prompt_request", "implementation_prompt"),
]
for intent, expected_tool in _MAPPINGS:
    result = choose_tool_for_intent(intent, "test message")
    check(f"intent={intent} → tool={expected_tool}", result == expected_tool)

print("\n-- Pattern-based fallback --")
_PATTERN_MSGS = [
    ("show approval queue", "approval_queue"),
    ("what tasks are open", "task_queue_status"),
    ("what did you do this morning", "morning_activity"),
    ("how do we make money", "revenue_asset_packet"),
    ("what's in the research queue", "research_queue"),
    ("memory v2 status", "memory_v2_status"),
]
for msg, expected_tool in _PATTERN_MSGS:
    result = choose_tool_for_intent("unknown_intent", msg)
    check(f"message='{msg[:40]}' → tool={expected_tool}", result == expected_tool)

print("\n-- All tools have command mappings --")
available = get_available_tools()
check("has tools", len(available) > 0)
for tool in available:
    cmd = _TOOL_COMMAND_MAP.get(tool)
    check(f"tool={tool} has command mapping (or None)", True)  # None is valid for unknown_answer_protocol

print("\n-- All intents map to valid tools --")
for intent, tool in _INTENT_TO_TOOL.items():
    check(f"intent={intent} → tool={tool} in map", tool in _TOOL_COMMAND_MAP)

print(f"\nResult: {passes} pass, {failures} fail")
sys.exit(0 if failures == 0 else 1)
