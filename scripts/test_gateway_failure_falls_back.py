"""
test_gateway_failure_falls_back.py
Verifies gateway failures are cached (10-min cooldown) and policy falls back
to evidence_only without crashing.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_gateway_failure_falls_back ===")

import lib.hermes_provider_policy as pp

# 1. Simulate gateway enabled but unreachable (bad port)
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "true"
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19998"
os.environ["HERMES_GATEWAY_KEY"] = "fake_key_test"

t0 = time.monotonic()
status = pp._detect_hermes_gateway()
elapsed = time.monotonic() - t0

check("gateway detection completes in under 5s even when unreachable", elapsed < 5.0)
check("gateway status is unavailable when unreachable", status.available is False)
check("gateway reason mentions unreachable or failed",
      "unreachable" in status.reason.lower() or "fail" in status.reason.lower() or "cooldown" in status.reason.lower())

# 2. Second call should be cached
t1 = time.monotonic()
status2 = pp._detect_hermes_gateway()
elapsed2 = time.monotonic() - t1
check("second gateway detection returns quickly (cached)", elapsed2 < 0.5)
check("second status also unavailable (cache hit)", status2.available is False)

# 3. Policy with failed gateway should have evidence_only as best strategic
policy = pp.load_provider_policy()
best = policy.best_for_strategic()
check("best_for_strategic is not hermes_gateway after failure", best != "hermes_gateway")

# cleanup
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_URL", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
# Clear the failure cache
pp._GATEWAY_FAILURE_CACHE.clear()

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
