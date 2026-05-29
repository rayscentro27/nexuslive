"""
test_evidence_summary_formatter.py
Verifies the evidence summary formatter produces clean responses.
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

print("=== test_evidence_summary_formatter ===")

from lib.hermes_evidence_summary_formatter import (
    format_evidence_response, format_no_evidence_response, format_provider_fallback_response
)
from lib.hermes_context_pack_builder import build_context_pack, ContextPack

# 1. format_evidence_response does not say "No conversational LLM"
pack = build_context_pack("what should I work on today", max_tokens=2500)
response = format_evidence_response("today_recommendation", pack)
check("response does not say 'No conversational LLM'",
      "No conversational LLM" not in response)
check("response does not say 'Command timed out'",
      "Command timed out" not in response)
check("response starts with 'I can answer from verified artifacts'",
      response.startswith("I can answer from verified artifacts"))
check("response has meaningful content (>30 chars)", len(response) > 30)

# 2. format_no_evidence_response is clean
no_ev = format_no_evidence_response("trading_recommendation")
check("no-evidence response does not say 'No conversational LLM'",
      "No conversational LLM" not in no_ev)
check("no-evidence response mentions verified or artifacts",
      "artifact" in no_ev.lower() or "evidence" in no_ev.lower())

# 3. Each intent gets a proper header
INTENTS = [
    "greeting", "today_recommendation", "claude_code_work", "youtube_status",
    "thirty_day_goals", "trading_recommendation", "nexus_project", "information_sources",
    "provider_status", "monetization",
]
for intent in INTENTS:
    empty_pack = ContextPack(question="test", intent=intent)
    resp = format_evidence_response(intent, empty_pack)
    check(f"intent '{intent}' produces non-empty response", len(resp) > 10)
    check(f"intent '{intent}' no 'No conversational LLM'",
          "No conversational LLM" not in resp)

# 4. format_provider_fallback_response with pack
fallback = format_provider_fallback_response("test question", "evidence_only", pack)
check("fallback response not None", fallback is not None)
check("fallback response no 'Command timed out'", "Command timed out" not in fallback)

# 5. format_provider_fallback_response without pack
fallback2 = format_provider_fallback_response("test question", "evidence_only", None)
check("fallback no-pack response is non-empty", len(fallback2) > 20)
check("fallback no-pack mentions ask commands",
      "ask" in fallback2.lower() or "show" in fallback2.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
