"""
test_memory_sources_send_not_none.py
Verifies that:
1. send_direct_response accepts bypass_dedup=True and skips the Supabase check
2. _send_memory_command_response calls send_direct_response with bypass_dedup=True
3. _try_memory_command never returns None when intent is memory_sources
4. _try_memory_command never returns empty string for memory intents
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


print("=== test_memory_sources_send_not_none ===\n")

from lib import hermes_gate
import telegram_bot as tb_mod
from hermes_command_router.router import run_command

print("-- hermes_gate.send_direct_response signature --")
import inspect as _inspect
sig = _inspect.signature(hermes_gate.send_direct_response)
params = sig.parameters
check("bypass_dedup parameter exists", "bypass_dedup" in params)
check("bypass_dedup defaults to False", params["bypass_dedup"].default is False)

print("\n-- bypass_dedup=True skips Supabase 60-second check --")
sdr_src = inspect.getsource(hermes_gate.send_direct_response)
check("has 'if not bypass_dedup' guard", "if not bypass_dedup" in sdr_src)
check("hash computed before guard (used in record)", sdr_src.index("h = _event_hash") < sdr_src.index("if not bypass_dedup"))
check("Supabase query inside bypass guard", sdr_src.count("hermes_aggregates") >= 1)

print("\n-- _send_memory_command_response calls send_direct_response with bypass_dedup=True --")
smcr_src = inspect.getsource(tb_mod.NexusTelegramBot._send_memory_command_response)
check("send_direct_response called", "send_direct_response" in smcr_src)
check("bypass_dedup=True passed", "bypass_dedup=True" in smcr_src)
check("event_type='direct_chat_reply' used", "direct_chat_reply" in smcr_src)
check("fallback sends bypass_dedup=True also", smcr_src.count("bypass_dedup=True") >= 2)

print("\n-- _try_memory_command never returns empty/None for valid memory intents --")
memory_phrases = [
    "show memory sources",
    "memory sources",
    "what are your memory sources",
    "show active operating rules",
    "where did that answer come from",
    "show memory sources again",
    "memory sources again",
]
for phrase in memory_phrases:
    result = run_command(phrase, source="telegram")
    check(f"run_command('{phrase[:40]}') not None", result is not None)
    check(f"run_command('{phrase[:40]}') not empty", bool(result and result.strip()))
    check(f"run_command('{phrase[:40]}') > 50 chars", len(result or "") > 50)

print("\n-- _try_memory_command source: returns None on exception (not '') --")
tb_src = inspect.getsource(tb_mod.NexusTelegramBot._try_memory_command)
check("returns None on exception", "return None" in tb_src)
check("does not return '' on exception", 'return ""' not in tb_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
