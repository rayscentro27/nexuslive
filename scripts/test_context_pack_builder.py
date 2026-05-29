"""
test_context_pack_builder.py
Verifies context pack builder classifies questions, retrieves evidence,
and returns well-formed ContextPack objects.
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

print("=== test_context_pack_builder ===")

from lib.hermes_context_pack_builder import (
    classify_question, build_context_pack, ContextPack,
    estimate_text_tokens, truncate_safely, TOKEN_BUDGET
)

# 1. Intent classification
CASES = [
    ("good morning hermes", "greeting"),
    ("what should I work on today", "today_recommendation"),
    ("what did claude code work on", "claude_code_work"),
    ("what trading strategy do you recommend", "trading_recommendation"),
    ("30 day goals", "thirty_day_goals"),
    ("what is nexus", "nexus_project"),
    ("where do you get your information", "information_sources"),
    ("youtube status", "youtube_status"),
    ("show provider mode", "provider_status"),
]
for msg, expected in CASES:
    intent = classify_question(msg)
    check(f"classify '{msg[:40]}' → {expected}", intent == expected)

# 2. ContextPack is returned for any question
pack = build_context_pack("what should I work on today", max_tokens=2500)
check("build_context_pack returns ContextPack", isinstance(pack, ContextPack))
check("context pack has question field", pack.question == "what should I work on today")
check("context pack has intent field", bool(pack.intent))
check("context pack has token_estimate", pack.token_estimate > 0)

# 3. as_prompt_text renders text
text = pack.as_prompt_text()
check("as_prompt_text returns non-empty string", len(text) > 10)
check("as_prompt_text contains CONTEXT PACK", "CONTEXT PACK" in text)

# 4. Token budget constants
check("TOKEN_BUDGET has local_ollama", "local_ollama" in TOKEN_BUDGET)
check("TOKEN_BUDGET local_ollama <= 2500", TOKEN_BUDGET["local_ollama"] <= 2500)
check("TOKEN_BUDGET has hermes_gateway", "hermes_gateway" in TOKEN_BUDGET)
check("TOKEN_BUDGET has evidence_only", "evidence_only" in TOKEN_BUDGET)

# 5. Token estimation
check("estimate_text_tokens returns positive int", estimate_text_tokens("hello world test") > 0)
check("estimate_text_tokens empty returns 1", estimate_text_tokens("") >= 1)

# 6. Truncate safely
long_text = "A" * 10000
truncated = truncate_safely(long_text, max_tokens=100)
check("truncate_safely reduces length", len(truncated) < len(long_text))
check("truncate_safely adds truncated marker", "truncated" in truncated.lower())

# 7. Pack size stays within budget
pack_small = build_context_pack("good morning", max_tokens=100)
check("pack respects small token budget", pack_small.token_estimate <= 200)  # small buffer allowed

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
