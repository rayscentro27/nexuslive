"""
test_show_memory_sources_visible_telegram.py
Verifies that 'show memory sources' is routed through _try_memory_command,
sets _memory_command_pending=True, and that handle_update would route to
_send_memory_command_response (bypass_dedup=True) instead of _send_message_once.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_show_memory_sources_visible_telegram ===\n")

import telegram_bot as tb_mod
from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- _try_memory_command sets _memory_command_pending on memory intents --")
tb_src = inspect.getsource(tb_mod.NexusTelegramBot._try_memory_command)
check("_try_memory_command sets _memory_command_pending=True", "_memory_command_pending = True" in tb_src)
check("memory_sources_again in MEMORY_INTENTS", "memory_sources_again" in tb_src)
check("returns None on exception (not empty string)", "return None" in tb_src)

print("\n-- handle_update checks _memory_command_pending before sending --")
hu_src = inspect.getsource(tb_mod.NexusTelegramBot.handle_update)
check("handle_update checks _memory_command_pending", "_memory_command_pending" in hu_src)
check("handle_update calls _send_memory_command_response", "_send_memory_command_response" in hu_src)
check("handle_update clears _memory_command_pending before send", "_memory_command_pending = False" in hu_src)
check("handle_update has else: _send_message_once branch", "_send_message_once" in hu_src)

print("\n-- _send_memory_command_response exists and uses bypass_dedup=True --")
smcr_src = inspect.getsource(tb_mod.NexusTelegramBot._send_memory_command_response)
check("_send_memory_command_response defined", bool(smcr_src))
check("uses bypass_dedup=True", "bypass_dedup=True" in smcr_src)
check("calls send_direct_response", "send_direct_response" in smcr_src)
check("has fallback notice on send failure", "already answered recently" in smcr_src)

print("\n-- __init__ declares _memory_command_pending --")
init_src = inspect.getsource(tb_mod.NexusTelegramBot.__init__)
check("__init__ has _memory_command_pending = False", "_memory_command_pending" in init_src)

print("\n-- send_direct_response accepts bypass_dedup parameter --")
from lib import hermes_gate
sdr_src = inspect.getsource(hermes_gate.send_direct_response)
check("send_direct_response has bypass_dedup parameter", "bypass_dedup" in sdr_src)
check("bypass_dedup=False default", "bypass_dedup: bool = False" in sdr_src)
check("skips Supabase check when bypass_dedup=True", "if not bypass_dedup" in sdr_src)

print("\n-- run_command returns non-empty for memory commands --")
for phrase in ["show memory sources", "memory sources", "where do you get memory from"]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → memory_sources", intent == "memory_sources")
    result = run_command(phrase, source="telegram")
    check(f"run_command('{phrase[:30]}') non-empty", bool(result and result.strip()))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
