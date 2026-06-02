"""
test_answer_source_clean_format.py
Verifies 'where did that answer come from' returns ANSWER SOURCE
in clean plain-text format without the large HERMES REPORT wrapper.
Full report wrapper only for explicit "full report" / "technical report" requests.
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


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_answer_source_clean_format ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
variants = [
    "where did that answer come from",
    "where does that come from",
    "where does your answer come from",
    "cite that answer",
    "cite source",
    "answer source",
    "what source did you use",
    "why did you answer that",
]
for v in variants:
    intent, _, _ = classify_intent(v)
    check(f"classify {v!r} → answer_source", intent == "answer_source")

print("\n-- Response is non-empty --")
result = run_command("where did that answer come from", source="telegram")
check("run_command returns non-empty string", bool(result and result.strip()))

print("\n-- Response contains ANSWER SOURCE --")
check("response contains ANSWER SOURCE", "ANSWER SOURCE" in result)

print("\n-- No HERMES REPORT wrapper by default --")
check("no '═══' report border", "═══" not in result)
check("no 'HERMES REPORT' header", "HERMES REPORT" not in result)
check("no 'What Happened:'", "What Happened:" not in result)
check("no 'Action Needed From You:'", "Action Needed From You:" not in result)
check("no 'Status: ✅ HEALTHY'", "Status: ✅ HEALTHY" not in result)

print("\n-- Content sections present --")
check("contains 'I answered from the current active context'",
      "I answered from the current active context" in result or "current active context" in result.lower())
check("contains 'Most recent evidence:'", "Most recent evidence:" in result)
check("contains decision log reference", "decision_log" in result or "hermes_decision_log" in result)
check("contains memory policy reference", "HERMES_MEMORY_SAFETY_CONTRACT" in result)
check("contains memory v2 mention", "memory v2" in result.lower() or "hermes_memory_v2" in result.lower())

print("\n-- Not archived executive memory --")
check("states did not use archived executive memory",
      "did not use archived executive memory" in result or "not use archived" in result.lower())

print("\n-- Hint for full report mode --")
check("mentions 'show technical source details' for full format",
      "show technical source details" in result or "technical" in result.lower())

print("\n-- No evidence dump --")
check("no [artifact_inventory] dump", "[artifact_inventory]" not in result)
check("no [handoff] dump", "[handoff]" not in result)
check("no 'I can answer from verified artifacts'",
      "I can answer from verified artifacts" not in result)

print("\n-- No stale strings --")
for s in STALE_MARKERS:
    check(f"no stale marker: {s!r}", s not in result)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
