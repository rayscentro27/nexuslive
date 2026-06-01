"""test_no_evidence_dump_for_general_questions.py
General Telegram questions must never return evidence/handoff dumps.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_no_evidence_dump_for_general_questions ===\n")

from lib.hermes_conversational_router import route_conversational_intent

FORBIDDEN = [
    "strategic context from evidence",
    "i can answer from verified artifacts",
    "artifact_inventory",
    "handoff dump",
    "OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "Launch Nexus AI affiliate",
    "Hermes Executive Memory (v1",
]

questions = [
    "did you get sleep last night",
    "what can you answer",
    "what is the weather today",
    "what is the system health",
    "what is the best money making opportunity right now",
    "show memory sources",
]
for q in questions:
    resp = route_conversational_intent(q)
    for bad in FORBIDDEN:
        check(f"'{q}' no '{bad}'", bad.lower() not in (resp or "").lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
