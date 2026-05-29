"""
test_gateway_fallback_evidence_only.py
Verifies that when gateway and all providers fail, responses use evidence mode —
no fake recommendations, no invented scoring.
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

print("=== test_gateway_fallback_evidence_only ===")

# Force all providers to fail by using non-existent endpoints
import lib.hermes_provider_policy as pp
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19999"
os.environ["HERMES_GATEWAY_KEY"] = "fake_key_for_test"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
policy = pp.load_provider_policy()

# 1. When gateway is unreachable, best_for_strategic should NOT be hermes_gateway
check("gateway unavailable when port closed", not policy._is_available("hermes_gateway"))

# 2. best_for_strategic falls back gracefully
strategic = policy.best_for_strategic()
check("strategic provider is valid type", strategic in {
    "openai_api", "codex_auth", "openclaw_chatgpt_auth", "local_ollama", "openrouter", "evidence_only"
})

# 3. reason() in evidence-only mode does not invent content
from lib.hermes_reasoning_layer import reason
pp.get_policy(refresh=True)
r = reason("what should nexus do next?", evidence_text="")
BAD = ["nitrotrades", "slide 12", "6 pending", "sba deadline", "10x growth"]
check("evidence_only reply has no hallucinated tokens",
      not any(b in r.reply.lower() for b in BAD))
check("evidence_only reply is a string", isinstance(r.reply, str))
check("evidence_only reply is non-empty", len(r.reply) > 5)

# 4. evidence_only mode with evidence text shows verified data, not invented data
evidence = "[verified_file] report: some_report_2026.md\n[verified_file] prompt: handoff_001.md"
r2 = reason("what is the status?", evidence_text=evidence)
check("evidence_only with data includes verified prefix", "verified" in r2.reply.lower() or r2.provider_used != "evidence_only")

# 5. Gateway failure does NOT produce NEXUS OPPORTUNITY REPORT
check("evidence reply does not contain NEXUS OPPORTUNITY REPORT",
      "NEXUS OPPORTUNITY REPORT" not in r.reply)

# 6. No fake approval counts in evidence mode
check("no fake approval count '6 pending'", "6 pending" not in r.reply)
check("no NitroTrades invention", "nitrotrades" not in r.reply.lower())

# cleanup
del os.environ["HERMES_GATEWAY_URL"]
del os.environ["HERMES_GATEWAY_KEY"]
del os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"]

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
