"""
test_relevant_evidence_retrieval.py
Verifies that the context pack retrieves evidence relevant to the intent.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_relevant_evidence_retrieval ===")

from lib.hermes_context_pack_builder import (
    build_context_pack, retrieve_relevant_evidence
)

# 1. Trading intent retrieves trading evidence
ev = retrieve_relevant_evidence("what trading strategy do you recommend", "trading_recommendation")
check("trading intent has 'trading' key in evidence", "trading" in ev)
check("trading intent does not have unrelated 'intake' key", "intake" not in ev)

# 2. Claude code work intent retrieves handoffs
ev2 = retrieve_relevant_evidence("what did claude code work on", "claude_code_work")
check("claude_code_work intent has 'handoffs' key", "handoffs" in ev2)
check("claude_code_work intent does not have unrelated 'trading' key", "trading" not in ev2)

# 3. 30-day goals retrieves revenue plan
ev3 = retrieve_relevant_evidence("30 day goals", "thirty_day_goals")
check("thirty_day_goals intent has 'revenue_plan' key", "revenue_plan" in ev3)

# 4. Nexus project retrieves nexus brief
ev4 = retrieve_relevant_evidence("what is nexus", "nexus_project")
check("nexus_project intent has 'nexus_brief' key", "nexus_brief" in ev4)

# 5. YouTube status retrieves intake
ev5 = retrieve_relevant_evidence("youtube status", "youtube_status")
check("youtube_status intent has 'intake' key", "intake" in ev5)

# 6. Pack for trading has trading in artifact paths or evidence items
pack_trading = build_context_pack("what trading strategy do you recommend")
check("trading pack intent is trading_recommendation", pack_trading.intent == "trading_recommendation")
# Should have at least one evidence item (even if files don't exist → missing_evidence)
has_evidence = bool(pack_trading.evidence_items) or bool(pack_trading.missing_evidence)
check("trading pack has evidence items or missing evidence", has_evidence)

# 7. Pack for claude_code_work is focused
pack_handoffs = build_context_pack("what did claude code work on")
check("claude_code_work pack intent correct", pack_handoffs.intent == "claude_code_work")

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
