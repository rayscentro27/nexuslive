"""
test_answer_source_no_evidence_dump.py
Verifies that "where did that answer come from" returns a clean answer
source explanation, not a raw evidence/data dump.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_answer_source_no_evidence_dump ===\n")

from hermes_command_router.router import _run_answer_source, run_command
from hermes_command_router.intake import classify_intent

# ── 1. Handler output ─────────────────────────────────────────────────────
status, evidence, rec = _run_answer_source()
full = "\n".join(evidence)
check("answer_source returns healthy", status == "healthy")
check("contains ANSWER SOURCE header", "ANSWER SOURCE" in full)
check("mentions active context", "active context" in full)
check("mentions decision log", "decision log" in full.lower())
check("mentions memory policy", "MEMORY_SAFETY_CONTRACT" in full)
check("did not use archived executive memory", "did not use archived executive memory" in full)

# ── 2. No raw data dumps ─────────────────────────────────────────────────
RAW_DUMP_PATTERNS = [
    "artifact_inventory",
    "[artifact_inventory]",
    "[handoffs]",
    "quality escalation fallback",
    "Executive Memory — as of",
    "Ollama OFFLINE",
    "Beehiiv pending",
]
for pattern in RAW_DUMP_PATTERNS:
    check(f"no '{pattern}' in answer source", pattern not in full)

# ── 3. Intent classification ─────────────────────────────────────────────
for phrase in [
    "where did that answer come from",
    "where does that come from",
    "where does your answer come from",
    "cite that answer",
    "cite source",
    "answer source",
    "what source did you use",
    "why did you answer that",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → answer_source", intent == "answer_source")

# Non-matching
for phrase in [
    "show memory sources",
    "memory sources",
    "what memory sources",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' NOT answer_source", intent != "answer_source")
    check(f"'{phrase}' is memory_sources", intent == "memory_sources")

# ── 4. run_command output ─────────────────────────────────────────────────
resp = run_command("where did that answer come from", source="telegram")
check("run_command answer source contains ANSWER SOURCE header", "ANSWER SOURCE" in resp)
check("run_command answer source no archive dump", "Hermes Executive Memory" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
