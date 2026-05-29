"""
test_context_pack_size_limits.py
Verifies context packs stay within provider-specific token budgets.
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

print("=== test_context_pack_size_limits ===")

from lib.hermes_context_pack_builder import (
    build_context_pack, estimate_text_tokens, TOKEN_BUDGET
)

QUESTIONS = [
    "what should I work on today",
    "what trading strategy do you recommend",
    "what did claude code work on",
    "30 day goals",
    "what is nexus",
    "show source intake",
]

# 1. local_ollama budget (2500 tokens)
for q in QUESTIONS:
    pack = build_context_pack(q, max_tokens=TOKEN_BUDGET["local_ollama"])
    tokens = pack.token_estimate
    check(f"local_ollama pack for '{q[:35]}' within 2500 tokens", tokens <= 2500 + 50)  # small buffer

# 2. hermes_gateway budget (8000 tokens)
for q in QUESTIONS[:3]:
    pack = build_context_pack(q, max_tokens=TOKEN_BUDGET["hermes_gateway"])
    tokens = pack.token_estimate
    check(f"hermes_gateway pack for '{q[:35]}' within 8000 tokens", tokens <= 8000 + 100)

# 3. Very small budget forces truncation
pack_tight = build_context_pack("what trading strategy do you recommend", max_tokens=50)
check("very small budget pack still returns ContextPack", pack_tight is not None)
check("very small budget pack token estimate is reasonable",
      pack_tight.token_estimate <= 500)  # should trim aggressively

# 4. Pack text stays reasonable when rendered
pack_standard = build_context_pack("what should I work on today",
                                   max_tokens=TOKEN_BUDGET["local_ollama"])
text = pack_standard.as_prompt_text()
char_limit = TOKEN_BUDGET["local_ollama"] * 4 * 1.2  # 20% buffer
check("pack text chars within expected range", len(text) <= char_limit)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
