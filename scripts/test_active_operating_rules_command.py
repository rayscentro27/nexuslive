"""
test_active_operating_rules_command.py
Verifies 'show active operating rules' routes correctly and returns
ACTIVE OPERATING RULES without triggering generic evidence dump.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Executive Memory — as of",
    "Quality escalation fallback",
]

EVIDENCE_DUMP_PHRASES = [
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "[artifact_inventory]",
    "[handoff]",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_active_operating_rules_command ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
variants = [
    "show active operating rules",
    "active operating rules",
    "what active rules are you using",
    "what rules are you following",
    "show hermes rules",
    "show live answer rules",
    "show approval rules",
    "what approval rules are active",
]
for v in variants:
    intent, _, _ = classify_intent(v)
    check(f"classify {v!r} → active_operating_rules", intent == "active_operating_rules")

print("\n-- MEMORY_INTENTS includes active_operating_rules --")
# Verify telegram_bot MEMORY_INTENTS will catch it
from hermes_command_router.router import _PLAIN_INTENTS
check("active_operating_rules in _PLAIN_INTENTS", "active_operating_rules" in _PLAIN_INTENTS)

print("\n-- Response is non-empty --")
result = run_command("show active operating rules", source="telegram")
check("run_command returns non-empty string", bool(result and result.strip()))

print("\n-- Response contains ACTIVE OPERATING RULES --")
check("response contains ACTIVE OPERATING RULES", "ACTIVE OPERATING RULES" in result)

print("\n-- Response is plain text (no HERMES REPORT wrapper) --")
check("no HERMES REPORT header", "HERMES REPORT" not in result)
check("no '═══' report border", "═══" not in result)
check("no 'What Happened:'", "What Happened:" not in result)

print("\n-- Rules content present --")
check("contains rule 1: Evidence first", "Evidence first" in result or "evidence first" in result.lower())
check("contains rule about inventing status", "invent" in result.lower() or "fabricat" in result.lower())
check("contains rule about Ray approval", "Ray approval" in result or "ray approval" in result.lower())
check("contains rule about live_answer memory", "live_answer" in result or "live answer" in result.lower())

print("\n-- Memory v2 section present --")
check("contains 'Memory v2:'", "Memory v2:" in result)
check("hermes_memory_v2 mentioned", "hermes_memory_v2" in result)
check("batch 1 mentioned", "Batch 1" in result or "batch 1" in result.lower())

print("\n-- Evidence section present --")
check("HERMES_MEMORY_SAFETY_CONTRACT mentioned", "HERMES_MEMORY_SAFETY_CONTRACT" in result)

print("\n-- No generic evidence dump --")
for phrase in EVIDENCE_DUMP_PHRASES:
    check(f"no evidence dump phrase: {phrase[:40]!r}", phrase not in result)

print("\n-- No stale strings --")
for s in STALE_MARKERS:
    check(f"no stale marker: {s!r}", s not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
