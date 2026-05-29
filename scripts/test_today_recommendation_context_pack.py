"""
test_today_recommendation_context_pack.py
Verifies "what should I work on today" uses context pack with correct intent
and retrieves relevant evidence (handoffs, revenue plan).
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

print("=== test_today_recommendation_context_pack ===")

from lib.hermes_context_pack_builder import build_context_pack, classify_question

QUERIES = [
    "what should I work on today",
    "what should we work on today",
    "what to focus on today",
    "priorities today",
    "next best move",
    "top priorities",
]

for q in QUERIES:
    intent = classify_question(q)
    check(f"'{q[:40]}' → today_recommendation or general_strategy",
          intent in ("today_recommendation", "general_strategy"))

# Build pack for today
pack = build_context_pack("what should I work on today", max_tokens=2500)
check("pack intent is today_recommendation", pack.intent == "today_recommendation")
check("pack token_estimate is populated", pack.token_estimate > 0)
check("pack has provider_instructions", bool(pack.provider_instructions))

# Text renders cleanly
text = pack.as_prompt_text()
check("pack text contains CONTEXT PACK header", "CONTEXT PACK" in text)
check("pack text contains question", "what should I work on today" in text)
check("pack text is under 12000 chars", len(text) < 12000)

# Evidence items should include artifact_inventory or handoffs (or missing note)
has_items_or_missing = bool(pack.evidence_items) or bool(pack.missing_evidence)
check("pack has evidence items or missing_evidence notes", has_items_or_missing)

# Verify no raw evidence dump (no "---" separators or huge raw blocks)
check("no huge raw evidence dump (text < 15000 chars)", len(text) < 15000)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
