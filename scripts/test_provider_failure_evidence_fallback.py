"""
test_provider_failure_evidence_fallback.py
Verifies that when all LLM providers fail, reasoning layer returns a clean
evidence response — NOT "No conversational LLM is available right now."
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

print("=== test_provider_failure_evidence_fallback ===")

# Force all providers offline
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "false"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:19993"  # unreachable
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("CODEX_AUTH_TOKEN", None)
os.environ.pop("OPENCLAW_CHATGPT_AUTH", None)

import lib.hermes_provider_policy as pp
pp._policy = None
pp.get_policy(refresh=True)

from lib.hermes_reasoning_layer import reason

# 1. Evidence_only fallback should not say "No conversational LLM"
result = reason("what should I work on today", evidence_text="", ops_context="")
check("evidence_only result is not None", result is not None)
check("provider_used is evidence_only", result.provider_used == "evidence_only")
check("is_evidence_only is True", result.is_evidence_only is True)
check("reply does not say 'No conversational LLM is available right now'",
      "No conversational LLM is available right now" not in result.reply)
check("reply does not say 'Command timed out'", "Command timed out" not in result.reply)
check("reply does not say 'Try again in a moment'", "Try again in a moment" not in result.reply)
check("reply has meaningful content (>20 chars)", len(result.reply) > 20)

# 2. With evidence text, should include it cleanly
result2 = reason("what should I work on today",
                 evidence_text="[verified] handoffs: 54 files found",
                 ops_context="")
check("evidence_only with text result not None", result2 is not None)
check("reply with evidence not 'No conversational LLM'",
      "No conversational LLM is available right now" not in result2.reply)

# 3. Clean format check
check("reply starts with meaningful text",
      len(result.reply.strip()) > 10 and not result.reply.startswith("None"))

# cleanup
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_ALLOW_OPENROUTER_FALLBACK", None)
os.environ.pop("OLLAMA_HOST", None)
pp._policy = None

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
