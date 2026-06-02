"""
test_memory_status_commands_bypass_dedup.py
Verifies that all safe repeatable memory status intents bypass dedup and content filter.
Checks:
1. SAFE_REPEATABLE_MEMORY_INTENTS contains required intents.
2. send_direct_response has bypass_dedup and bypass_content_filter params.
3. _send_memory_command_response passes both bypass flags.
4. _contains_forbidden_content does NOT block memory command responses.
5. 'sources:' removed from _FORBIDDEN_CONTENT_PATTERNS (was the root cause).
6. Research reports are still blocked by remaining patterns.
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


print("=== test_memory_status_commands_bypass_dedup ===\n")

import inspect
import telegram_bot as tb_mod
from lib import hermes_gate
from hermes_command_router.router import run_command

print("-- SAFE_REPEATABLE_MEMORY_INTENTS contains required intents --")
safe = tb_mod.NexusTelegramBot.SAFE_REPEATABLE_MEMORY_INTENTS
required = {
    "memory_sources", "memory_sources_again",
    "active_operating_rules", "answer_source",
    "archived_executive_memory", "stale_memory_debug",
}
for intent in required:
    check(f"'{intent}' in SAFE_REPEATABLE_MEMORY_INTENTS", intent in safe)

print("\n-- send_direct_response bypass parameters --")
sdr_src = inspect.getsource(hermes_gate.send_direct_response)
check("bypass_dedup: bool = False present", "bypass_dedup: bool = False" in sdr_src)
check("bypass_content_filter: bool = False present", "bypass_content_filter: bool = False" in sdr_src)
check("content filter gated on 'if not bypass_content_filter'", "if not bypass_content_filter" in sdr_src)
check("Supabase dedup gated on 'if not bypass_dedup'", "if not bypass_dedup" in sdr_src)

print("\n-- _send_memory_command_response passes both bypass flags --")
smcr_src = inspect.getsource(tb_mod.NexusTelegramBot._send_memory_command_response)
check("bypass_dedup=True in _send_memory_command_response", "bypass_dedup=True" in smcr_src)
check("bypass_content_filter=True in _send_memory_command_response", "bypass_content_filter=True" in smcr_src)

print("\n-- 'sources:' removed from _FORBIDDEN_CONTENT_PATTERNS (root-cause fix) --")
check("'sources:' NOT in _FORBIDDEN_CONTENT_PATTERNS",
      "sources:" not in hermes_gate._FORBIDDEN_CONTENT_PATTERNS)

print("\n-- _contains_forbidden_content does NOT block memory command responses --")
memory_responses = [
    run_command("show memory sources", source="telegram") or "",
    run_command("show active operating rules", source="telegram") or "",
    run_command("where did that answer come from", source="telegram") or "",
]
for resp in memory_responses:
    preview = resp[:60].replace('\n', '↵')
    check(f"not blocked: '{preview}...'",
          not hermes_gate._contains_forbidden_content(resp))

print("\n-- Research reports STILL blocked by remaining patterns --")
research_msgs = [
    "🏛️ Nexus Research\nKey Findings:\n- item 1\nResearch artifacts saved",
    "🏛️ Nexus Intelligence Brief\nSomething happened",
    "Nexus Research Run Complete\nKey Findings:\n- item 1",
    "Intelligence Brief: market summary\nKey Findings:\n- data",
]
for msg in research_msgs:
    preview = msg[:50].replace('\n', '↵')
    check(f"blocked: '{preview}...'",
          hermes_gate._contains_forbidden_content(msg))

print("\n-- All safe intents return full responses (no block text) --")
for intent_phrase, intent_name in [
    ("show memory sources", "memory_sources"),
    ("show active operating rules", "active_operating_rules"),
    ("where did that answer come from", "answer_source"),
    ("show memory sources again", "memory_sources_again"),
]:
    result = run_command(intent_phrase, source="telegram") or ""
    check(f"'{intent_name}': non-empty", bool(result.strip()))
    check(f"'{intent_name}': no block text", "already answered recently" not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
