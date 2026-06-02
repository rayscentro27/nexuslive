"""
test_memory_sources_repeat_always_returns.py
Verifies that calling run_command('show memory sources', ...) twice in immediate
succession returns identical, non-empty HERMES MEMORY SOURCES content both times.
Simulates the Telegram dedup scenario: same intent, same content, called back-to-back.
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


print("=== test_memory_sources_repeat_always_returns ===\n")

from hermes_command_router.router import run_command

print("-- Immediate repeat returns HERMES MEMORY SOURCES every time --")
for i in range(3):
    result = run_command("show memory sources", source="telegram") or ""
    check(f"call #{i+1}: non-empty", bool(result.strip()))
    check(f"call #{i+1}: contains HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in result)
    check(f"call #{i+1}: no 'already answered recently'", "already answered recently" not in result)
    check(f"call #{i+1}: no 'Say show memory sources again'", "Say 'show memory sources again'" not in result)

print("\n-- 'again' variant also returns HERMES MEMORY SOURCES every time --")
for phrase in ["show memory sources again", "memory sources again", "repeat memory sources"]:
    for i in range(2):
        result = run_command(phrase, source="telegram") or ""
        check(f"'{phrase[:40]}' call #{i+1}: HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in result)
        check(f"'{phrase[:40]}' call #{i+1}: no block text", "already answered recently" not in result)

print("\n-- Content is consistent across all memory_sources variants --")
base = run_command("show memory sources", source="telegram") or ""
for phrase in ["memory sources", "where do you get memory from", "show memory sources again",
               "memory sources again", "repeat memory sources"]:
    r = run_command(phrase, source="telegram") or ""
    check(f"'{phrase[:40]}' content matches base", r == base)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
