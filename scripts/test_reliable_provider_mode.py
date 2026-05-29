"""
test_reliable_provider_mode.py
Verifies that reliable mode (gateway disabled by default) is the default.
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

print("=== test_reliable_provider_mode ===")

# Ensure gateway is NOT enabled by default
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
os.environ.pop("HERMES_GATEWAY_URL", None)

import lib.hermes_provider_policy as pp
policy = pp.load_provider_policy()

check("gateway_allowed is False by default", policy.gateway_allowed is False)
check("best_for_strategic does not return hermes_gateway by default",
      policy.best_for_strategic() != "hermes_gateway")
check("telegram_report shows active mode reliable",
      "reliable" in policy.telegram_report().lower())
check("gateway detection shows disabled",
      any("HERMES_ALLOW_HERMES_GATEWAY not enabled" in s.reason
          for s in policy.statuses if s.provider == "hermes_gateway"))

# Verify gateway unavailable in status
gw_status = next((s for s in policy.statuses if s.provider == "hermes_gateway"), None)
check("hermes_gateway status present", gw_status is not None)
if gw_status:
    check("hermes_gateway available=False (not enabled)", gw_status.available is False)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
