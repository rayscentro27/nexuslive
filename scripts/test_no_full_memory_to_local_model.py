"""
test_no_full_memory_to_local_model.py
Verifies that when building context for local Ollama, the pack stays within
2500 tokens — not sending full Nexus memory to a weak model.
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

print("=== test_no_full_memory_to_local_model ===")

from lib.hermes_context_pack_builder import build_context_pack, estimate_text_tokens, TOKEN_BUDGET

QUESTIONS = [
    "what should I work on today",
    "what trading strategy do you recommend",
    "what did claude code work on",
    "what is nexus",
    "30 day goals",
    "show source intake",
    "what are your information sources",
]

MAX_TOKENS = TOKEN_BUDGET["local_ollama"]  # 2500

for q in QUESTIONS:
    pack = build_context_pack(q, max_tokens=MAX_TOKENS)
    text = pack.as_prompt_text()
    token_est = estimate_text_tokens(text)

    check(f"'{q[:40]}' — pack within {MAX_TOKENS} tokens",
          token_est <= MAX_TOKENS + 50)  # small buffer for system prompt tokens

    # Verify it doesn't include huge full memory dumps
    check(f"'{q[:40]}' — text under 12000 chars",
          len(text) <= 12000)

# Also verify TOKEN_BUDGET difference is meaningful
check("local_ollama budget smaller than hermes_gateway",
      TOKEN_BUDGET["local_ollama"] < TOKEN_BUDGET["hermes_gateway"])
check("hermes_gateway budget smaller than openai_api",
      TOKEN_BUDGET["hermes_gateway"] < TOKEN_BUDGET["openai_api"])

# Provider instructions should be in pack
pack = build_context_pack("what should I work on today", max_tokens=MAX_TOKENS)
check("pack has provider_instructions", bool(pack.provider_instructions))
check("provider_instructions mentions artifact paths",
      "artifact" in pack.provider_instructions.lower() or "path" in pack.provider_instructions.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
