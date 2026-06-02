"""
test_show_memory_sources_again_bypasses_dedup.py
Verifies that 'show memory sources again' is a valid intent that routes through
_PLAIN_INTENTS and produces the same content as 'show memory sources'.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_show_memory_sources_again_bypasses_dedup ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS

print("-- 'show memory sources again' variants classify correctly --")
again_phrases = [
    "show memory sources again",
    "memory sources again",
    "repeat memory sources",
    "resend memory sources",
]
for phrase in again_phrases:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → memory_sources_again", intent == "memory_sources_again")

print("\n-- memory_sources_again in _PLAIN_INTENTS --")
check("memory_sources_again in _PLAIN_INTENTS", "memory_sources_again" in _PLAIN_INTENTS)

print("\n-- memory_sources_again handler returns same content as memory_sources --")
handler_again = _PLAIN_INTENTS.get("memory_sources_again")
handler_base  = _PLAIN_INTENTS.get("memory_sources")
check("both handlers are the same function", handler_again is handler_base)

result_base  = run_command("show memory sources", source="telegram")
result_again = run_command("show memory sources again", source="telegram")
check("'show memory sources again' returns non-empty", bool(result_again and result_again.strip()))
check("content is identical to 'show memory sources'", result_base == result_again)
check("contains HERMES MEMORY SOURCES header", "HERMES MEMORY SOURCES" in (result_again or ""))

print("\n-- Non-'again' phrases still route to memory_sources --")
for phrase in ["show memory sources", "memory sources", "what are your memory sources"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → memory_sources (not again)", intent == "memory_sources")

print("\n-- 'show memory sources again' in MEMORY_INTENTS of _try_memory_command --")
import inspect
import telegram_bot as tb_mod
tb_src = inspect.getsource(tb_mod.NexusTelegramBot._try_memory_command)
check("memory_sources_again in MEMORY_INTENTS set", "memory_sources_again" in tb_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
