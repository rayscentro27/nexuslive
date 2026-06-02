"""
test_memory_commands_no_evidence_dump.py
Verifies that memory command phrases never produce a generic evidence dump
(artifact_inventory, handoff dump, stale Executive Memory, etc.).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

EVIDENCE_DUMP_PHRASES = [
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "[artifact_inventory]",
    "[handoff]",
]

STALE_MARKERS = [
    "Ollama OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "Executive Memory — as of",
    "Quality escalation fallback",
]

MEMORY_COMMAND_PHRASES = [
    "show memory sources",
    "where do you get memory from",
    "show active operating rules",
    "what active rules are you using",
    "where did that answer come from",
    "show approval rules",
    "show live answer rules",
    "what rules are you following",
    "show hermes rules",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_commands_no_evidence_dump ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _PLAIN_INTENTS, _EVIDENCE_DUMP_BLOCKED_PHRASES

print("-- _EVIDENCE_DUMP_BLOCKED_PHRASES defined --")
check("_EVIDENCE_DUMP_BLOCKED_PHRASES defined in router", bool(_EVIDENCE_DUMP_BLOCKED_PHRASES))
check("'show memory sources' in blocked phrases",
      "show memory sources" in _EVIDENCE_DUMP_BLOCKED_PHRASES)
check("'show active operating rules' in blocked phrases",
      "show active operating rules" in _EVIDENCE_DUMP_BLOCKED_PHRASES)
check("'where did that answer come from' in blocked phrases",
      "where did that answer come from" in _EVIDENCE_DUMP_BLOCKED_PHRASES)

print("\n-- _PLAIN_INTENTS covers all three memory command types --")
check("memory_sources in _PLAIN_INTENTS", "memory_sources" in _PLAIN_INTENTS)
check("active_operating_rules in _PLAIN_INTENTS", "active_operating_rules" in _PLAIN_INTENTS)
check("answer_source in _PLAIN_INTENTS", "answer_source" in _PLAIN_INTENTS)

print("\n-- Each memory command phrase produces no evidence dump --")
for phrase in MEMORY_COMMAND_PHRASES:
    intent, _, _ = classify_intent(phrase)
    result = run_command(phrase, source="telegram")
    for dump_phrase in EVIDENCE_DUMP_PHRASES:
        check(f"'{phrase[:35]}' — no '{dump_phrase[:35]}'",
              dump_phrase not in result)
    blocked_section = result.split("Blocked from live answers:")[-1] if "Blocked from live answers:" in result else ""
    for stale in STALE_MARKERS:
        if stale in result and stale in blocked_section:
            check(f"'{phrase[:35]}' — stale '{stale[:25]}' only in Blocked section", True)
        else:
            check(f"'{phrase[:35]}' — no active stale: '{stale[:25]}'",
                  stale not in result)
    check(f"'{phrase[:35]}' — no '═══' border", "═══" not in result)
    check(f"'{phrase[:35]}' — intent not 'unknown'", intent != "unknown")
    print()

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
