"""
test_memory_command_dedup_not_swallowed.py
Verifies memory commands are not silently swallowed by:
1. _try_memory_command exception handler (returns None → falls to generic routing)
2. Empty string return from run_command
3. Dedup suppression (same hash within 4s)
4. Final response gate blocking
"""
import sys, hashlib, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_command_dedup_not_swallowed ===\n")

from hermes_command_router.router import run_command
from lib.hermes_final_response_gate import inspect as gate_inspect

MEMORY_COMMANDS = [
    "show memory sources",
    "show active operating rules",
    "where did that answer come from",
    "what rules are you following",
]

print("-- run_command returns non-empty for all memory commands --")
results = {}
for cmd in MEMORY_COMMANDS:
    result = run_command(cmd, source="telegram")
    results[cmd] = result
    check(f"run_command('{cmd[:40]}') is non-empty", bool(result and result.strip()))
    check(f"run_command('{cmd[:40]}') > 50 chars", len(result or "") > 50)

print("\n-- Final response gate does not block memory command responses --")
for cmd, result in results.items():
    gate_result = gate_inspect(result)
    check(f"gate passes '{cmd[:40]}'", gate_result.passed or gate_result.safe_text == result)
    # In warn mode, safe_text == original (not blocked)
    check(f"gate does not replace text for '{cmd[:40]}'", gate_result.safe_text == result)

print("\n-- Responses for distinct intents are distinguishable --")
# Commands mapping to different intents must have different hashes.
# Commands mapping to the same intent (synonyms) will have the same hash — that is correct.
distinct_intent_cmds = [
    "show memory sources",        # → memory_sources
    "show active operating rules", # → active_operating_rules
    "where did that answer come from",  # → answer_source
]
hashes = {cmd: hashlib.sha256((run_command(cmd, source="telegram") or "").encode()).hexdigest()[:16]
          for cmd in distinct_intent_cmds}
unique_hashes = set(hashes.values())
check("three distinct-intent commands produce distinct content hashes",
      len(unique_hashes) == 3)

print("\n-- Repeated run_command returns same non-empty result (not swallowed) --")
for cmd in MEMORY_COMMANDS[:2]:
    r1 = run_command(cmd, source="telegram")
    r2 = run_command(cmd, source="telegram")
    check(f"second call non-empty: '{cmd[:40]}'", bool(r2 and r2.strip()))
    check(f"second call consistent: '{cmd[:40]}'", r1 == r2)

print("\n-- _try_memory_command source checks --")
import hermes_command_router.router as router_mod
import telegram_bot as tb_mod
import inspect as inspect_mod

tb_src = inspect_mod.getsource(tb_mod.NexusTelegramBot._try_memory_command)
# Safe intents now defined in SAFE_REPEATABLE_MEMORY_INTENTS class attribute
safe_intents = tb_mod.NexusTelegramBot.SAFE_REPEATABLE_MEMORY_INTENTS
check("_try_memory_command has exception handler (except Exception)",
      "except Exception" in tb_src)
check("_try_memory_command returns None on exception (not empty string)",
      "return None" in tb_src)
check("active_operating_rules in SAFE_REPEATABLE_MEMORY_INTENTS",
      "active_operating_rules" in safe_intents)
check("memory_sources in SAFE_REPEATABLE_MEMORY_INTENTS", "memory_sources" in safe_intents)
check("answer_source in SAFE_REPEATABLE_MEMORY_INTENTS", "answer_source" in safe_intents)

print("\n-- _PLAIN_INTENTS handlers return strings, not tuples --")
from hermes_command_router.router import _PLAIN_INTENTS
for intent_name, handler in _PLAIN_INTENTS.items():
    try:
        result = handler()
        check(f"_PLAIN_INTENTS['{intent_name}']() returns str", isinstance(result, str))
        check(f"_PLAIN_INTENTS['{intent_name}']() non-empty", bool(result and result.strip()))
    except Exception as e:
        check(f"_PLAIN_INTENTS['{intent_name}']() no exception: {e}", False)
        check(f"_PLAIN_INTENTS['{intent_name}']() (skipped)", True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
