"""test_telegram_conversation_routing.py
Simulates the 10 validation scenarios from Part 8 of the directive.
"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from unittest.mock import patch
PASS = FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else: FAIL += 1; print(f"  FAIL  {label}")
print("=== test_telegram_conversation_routing (Part 8 validation) ===\n")

from lib.hermes_conversational_router import route_conversational_intent, classify_conversational_intent
from lib.hermes_language_pack import (
    CATEGORY_SMALL_TALK, CATEGORY_CAPABILITY, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_EXTERNAL_INFO, CATEGORY_MEMORY_SOURCE,
)
import lib.hermes_knowledge_gap_logger as kgl
from hermes_command_router.router import run_command

FORBIDDEN = ["strategic context from evidence", "i can answer from verified artifacts",
             "artifact_inventory", "handoff dump", "OFFLINE", "Beehiiv pending",
             "YouTube Studio pending", "Hermes Executive Memory (v1",
             "Launch Nexus AI affiliate"]

def no_forbidden(resp):
    r = (resp or "").lower()
    return not any(f.lower() in r for f in FORBIDDEN)

# 1. did you get sleep last night
cat = classify_conversational_intent("did you get sleep last night")
check("1. 'did you get sleep last night' → small_talk", cat == CATEGORY_SMALL_TALK)
r1 = route_conversational_intent("did you get sleep last night")
check("1. small talk response is natural", isinstance(r1, str) and len(r1) > 5)
check("1. no stale dump", no_forbidden(r1))

# 2. what can you answer
cat2 = classify_conversational_intent("what can you answer")
check("2. 'what can you answer' → capability", cat2 == CATEGORY_CAPABILITY)
r2 = route_conversational_intent("what can you answer")
check("2. capability list returned", isinstance(r2, str) and "•" in (r2 or ""))
check("2. no stale dump", no_forbidden(r2))

# 3. what is the system health
cat3 = classify_conversational_intent("what is the system health")
check("3. 'what is the system health' → system_health", cat3 == CATEGORY_SYSTEM_HEALTH)
r3 = route_conversational_intent("what is the system health")
check("3. health response returned", isinstance(r3, str) and len(r3) > 10)
check("3. no stale dump", no_forbidden(r3))

# 4. what is the best money making opportunity right now
cat4 = classify_conversational_intent("what is the best money making opportunity right now")
check("4. monetization intent", cat4 == CATEGORY_MONETIZATION)
r4 = route_conversational_intent("what is the best money making opportunity right now")
check("4. monetization response", isinstance(r4, str) and len(r4) > 10)
check("4. no stale dump", no_forbidden(r4))

# 5. what is the weather today → external info gap
with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        cat5 = classify_conversational_intent("what is the weather today")
        check("5. 'what is the weather today' → external_info", cat5 == CATEGORY_EXTERNAL_INFO)
        r5 = route_conversational_intent("what is the weather today")
        check("5. weather response no hallucination", "connected" in (r5 or "").lower() or "not" in (r5 or "").lower())
        check("5. no stale dump", no_forbidden(r5))
        gaps = kgl.load_recent_knowledge_gaps(limit=5)
        check("5. gap was logged", len(gaps) > 0)

# 6. show memory sources
cat6 = classify_conversational_intent("show memory sources")
check("6. 'show memory sources' → memory_source", cat6 == CATEGORY_MEMORY_SOURCE)
r6 = route_conversational_intent("show memory sources")
check("6. memory sources response has header", "HERMES MEMORY SOURCES" in (r6 or ""))
check("6. no stale dump", no_forbidden(r6))

# 7. where did that answer come from
r7 = run_command("where did that answer come from", source="telegram")
check("7. answer source response has header", "ANSWER SOURCE" in r7)
check("7. no stale dump", no_forbidden(r7))

# 8. random unsupported question → logs gap
with tempfile.TemporaryDirectory() as tmp:
    gap_dir = Path(tmp) / "gaps"
    gap_jsonl = gap_dir / "hermes_knowledge_gaps.jsonl"
    with patch.object(kgl, "GAP_DIR", gap_dir), patch.object(kgl, "GAP_JSONL", gap_jsonl):
        from lib.hermes_knowledge_gap_logger import log_knowledge_gap
        from lib.hermes_language_pack import CATEGORY_UNKNOWN, GAP_MISSING_ROUTE
        log_knowledge_gap("totally random unsupported question xyz", CATEGORY_UNKNOWN, GAP_MISSING_ROUTE)
        gaps = kgl.load_recent_knowledge_gaps(limit=5)
        check("8. unknown question gap logged", len(gaps) > 0)

# 9. show knowledge gaps
r9 = run_command("show knowledge gaps", source="telegram")
check("9. gap review command runs", isinstance(r9, str))
check("9. no stale dump", no_forbidden(r9))

# 10. create better answers for gaps
r10 = run_command("create better answers for gaps", source="telegram")
check("10. gap research command runs", isinstance(r10, str))
check("10. no stale dump", no_forbidden(r10))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
