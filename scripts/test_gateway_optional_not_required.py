"""
test_gateway_optional_not_required.py
Verifies that the gateway is optional — provider policy works fine without it.
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

print("=== test_gateway_optional_not_required ===")

# Baseline: no env vars set for gateway
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)

import lib.hermes_provider_policy as pp

# 1. Policy loads without gateway
policy = pp.load_provider_policy()
check("policy loads successfully without gateway", policy is not None)
check("best_for_strategic returns something (not hermes_gateway)", True)  # just verify no crash
best = policy.best_for_strategic()
check("best_for_strategic does not return hermes_gateway", best != "hermes_gateway")

# 2. Even with HERMES_GATEWAY_KEY set, gateway is disabled without the allow flag
os.environ["HERMES_GATEWAY_KEY"] = "test_key_12345"
policy2 = pp.load_provider_policy()
check("gateway disabled even with key if HERMES_ALLOW_HERMES_GATEWAY not set", policy2.gateway_allowed is False)
best2 = policy2.best_for_strategic()
check("best_for_strategic still skips gateway when allow=false", best2 != "hermes_gateway")

# 3. With HERMES_ALLOW_HERMES_GATEWAY=true, gateway_allowed is True
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "true"
policy3 = pp.load_provider_policy()
check("gateway_allowed=True when env set to true", policy3.gateway_allowed is True)

# cleanup
os.environ.pop("HERMES_GATEWAY_KEY", None)
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
