"""
test_hybrid_provider_mode.py
Verifies that provider policy correctly selects best available provider
across different configurations (gateway enabled/disabled, Ollama up/down).
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

print("=== test_hybrid_provider_mode ===")

import lib.hermes_provider_policy as pp

# 1. Default mode (gateway disabled, no providers): evidence_only
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
os.environ.pop("OPENAI_API_KEY", None)
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:19995"  # unreachable
pp._policy = None

policy = pp.load_provider_policy()
best = policy.best_for_strategic()
check("with all providers offline, best_for_strategic is evidence_only", best == "evidence_only")
check("gateway_allowed is False in default mode", policy.gateway_allowed is False)

# 2. With gateway allowed but unreachable: still falls through
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "true"
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19994"
os.environ["HERMES_GATEWAY_KEY"] = "fake_key"
pp._policy = None
pp._GATEWAY_FAILURE_CACHE.clear()

policy2 = pp.load_provider_policy()
check("gateway_allowed=True when env set", policy2.gateway_allowed is True)
best2 = policy2.best_for_strategic()
# Gateway is unreachable, Ollama is unreachable → evidence_only
check("with gateway unreachable, falls through to evidence_only", best2 == "evidence_only")

# 3. Verify telegram_report reflects active mode
report_reliable = pp.load_provider_policy()
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_URL", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
pp._policy = None
p_reliable = pp.load_provider_policy()
check("reliable mode telegram_report contains 'reliable'",
      "reliable" in p_reliable.telegram_report().lower())

os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "true"
os.environ["HERMES_GATEWAY_KEY"] = "fakekey"
pp._policy = None
pp._GATEWAY_FAILURE_CACHE.clear()
p_gw = pp.load_provider_policy()
check("gateway mode telegram_report contains 'gateway'",
      "gateway" in p_gw.telegram_report().lower())

# cleanup
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_URL", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
os.environ.pop("HERMES_ALLOW_OPENROUTER_FALLBACK", None)
os.environ.pop("OLLAMA_HOST", None)
pp._policy = None
pp._GATEWAY_FAILURE_CACHE.clear()

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
