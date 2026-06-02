"""
test_memory_sources_no_recently_block.py
Verifies that no memory command response contains the blocking fallback text
"Memory sources command already answered recently." or any variant thereof.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

BLOCK_PHRASES = [
    "already answered recently",
    "Memory sources command already answered recently",
    "Say 'show memory sources again' to repeat",
    "command already answered",
]

MEMORY_COMMANDS = [
    "show memory sources",
    "memory sources",
    "where do you get memory from",
    "what are your memory sources",
    "show memory sources again",
    "memory sources again",
    "repeat memory sources",
    "resend memory sources",
    "show active operating rules",
    "where did that answer come from",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_sources_no_recently_block ===\n")

from hermes_command_router.router import run_command

for cmd in MEMORY_COMMANDS:
    result = run_command(cmd, source="telegram") or ""
    for phrase in BLOCK_PHRASES:
        check(f"'{cmd[:40]}' — no '{phrase[:40]}'", phrase not in result)
    check(f"'{cmd[:40]}' — non-empty response", bool(result.strip()))
    print()

print("\n-- _send_memory_command_response does not contain fallback block text --")
import inspect
import telegram_bot as tb_mod
smcr_src = inspect.getsource(tb_mod.NexusTelegramBot._send_memory_command_response)
check("'already answered recently' absent from _send_memory_command_response",
      "already answered recently" not in smcr_src)
check("'command already answered' absent from _send_memory_command_response",
      "command already answered" not in smcr_src)
check("uses logger.warning on send failure (not fallback message)", "logger.warning" in smcr_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
