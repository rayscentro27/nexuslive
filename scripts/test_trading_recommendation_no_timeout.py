"""
test_trading_recommendation_no_timeout.py
Verifies trading recommendation never times out — internal handler catches it
before any LLM call, and gateway timeout is reduced to 20s (within bot's 30s budget).
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

print("=== test_trading_recommendation_no_timeout ===")

# 1. Internal handler responds in well under 5 seconds (no LLM call needed)
from lib.hermes_internal_first import try_internal_first

start = time.monotonic()
result = try_internal_first("what trading strategy do you recommend")
elapsed = time.monotonic() - start

check("trading recommendation returns in under 5 seconds", elapsed < 5.0)
check("result is not None", result is not None)
if result:
    check("no timeout text in reply", "Command timed out" not in result.text)
    check("no 'try again in a moment' in reply", "Try again in a moment" not in result.text)
    check("reply has meaningful content", len(result.text) > 50)

# 2. With all providers offline, trading question still gets a real reply
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19999"
os.environ["HERMES_GATEWAY_KEY"] = "fake_timeout_test"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"

import lib.hermes_provider_policy as pp
pp.get_policy(refresh=True)

start2 = time.monotonic()
result2 = try_internal_first("what trading strategy do you recommend")
elapsed2 = time.monotonic() - start2

check("trading result with no providers still in under 5s", elapsed2 < 5.0)
check("trading result with no providers is not None", result2 is not None)
if result2:
    check("no 'Command timed out' in no-provider reply", "Command timed out" not in result2.text)
    check("reply mentions trading or evidence", "trading" in result2.text.lower() or "evidence" in result2.text.lower())

# 3. Verify gateway timeout constant in reasoning layer
import ast
from pathlib import Path
src = Path(__file__).resolve().parent.parent / "lib" / "hermes_reasoning_layer.py"
code = src.read_text()
check("gateway call uses timeout=20", "timeout=20" in code)

# cleanup
del os.environ["HERMES_GATEWAY_URL"]
del os.environ["HERMES_GATEWAY_KEY"]
del os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"]

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
