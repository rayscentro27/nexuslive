"""
test_memory_sources_exact_block_text_absent.py
Verifies the exact block text that was appearing in live Telegram tests is absent
from all memory command code paths.

These are the exact strings observed in the wild:
  "Memory sources command already answered recently. Say 'show memory sources again' to repeat."

Tests confirm:
1. The exact block text is absent from run_command() output for all memory phrases.
2. The exact block text is absent from _send_memory_command_response source code.
3. The exact block text was removed along with its surrounding fallback logic.
4. All expected content keywords are PRESENT in the real response.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

EXACT_BLOCK_TEXT = "Memory sources command already answered recently. Say 'show memory sources again' to repeat."
BLOCK_SUBSTRING  = "already answered recently"

MEMORY_PHRASES = [
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

EXPECTED_CONTENT_BY_PHRASE = {
    "show memory sources":        "HERMES MEMORY SOURCES",
    "memory sources":             "HERMES MEMORY SOURCES",
    "where do you get memory from": "HERMES MEMORY SOURCES",
    "show memory sources again":  "HERMES MEMORY SOURCES",
    "repeat memory sources":      "HERMES MEMORY SOURCES",
    "show active operating rules": "ACTIVE OPERATING RULES",
    "where did that answer come from": "ANSWER SOURCE",
}


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_sources_exact_block_text_absent ===\n")

from hermes_command_router.router import run_command
import telegram_bot as tb_mod

print("-- Exact block text absent from all run_command() outputs --")
for phrase in MEMORY_PHRASES:
    result = run_command(phrase, source="telegram") or ""
    check(f"exact block text absent: '{phrase[:45]}'", EXACT_BLOCK_TEXT not in result)
    check(f"'already answered recently' absent: '{phrase[:35]}'", BLOCK_SUBSTRING not in result)

print("\n-- Expected content present in responses --")
for phrase, expected in EXPECTED_CONTENT_BY_PHRASE.items():
    result = run_command(phrase, source="telegram") or ""
    check(f"'{phrase[:40]}' → contains '{expected}'", expected in result)

print("\n-- Exact block text absent from _send_memory_command_response source --")
smcr_src = inspect.getsource(tb_mod.NexusTelegramBot._send_memory_command_response)
check("exact block text absent from method source", EXACT_BLOCK_TEXT not in smcr_src)
check("'already answered recently' absent from method source", BLOCK_SUBSTRING not in smcr_src)

print("\n-- Exact block text absent from telegram_bot module (entire file) --")
import telegram_bot as _tb_file
full_src = inspect.getsource(_tb_file)
check("exact block text absent from entire telegram_bot module", EXACT_BLOCK_TEXT not in full_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
