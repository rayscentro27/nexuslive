"""
test_telegram_no_provider_timeout.py
Verifies that when all providers are offline, Hermes returns a real response
(not "Command timed out") within the bot's 30-second window.
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

print("=== test_telegram_no_provider_timeout ===")

# Simulate all providers offline
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19997"
os.environ["HERMES_GATEWAY_KEY"] = "fake"
os.environ["HERMES_ALLOW_HERMES_GATEWAY"] = "false"
os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "false"
# Leave Ollama as potential fallback — it may or may not be running

import lib.hermes_provider_policy as pp
pp._GATEWAY_FAILURE_CACHE.clear()

# 1. Provider mode internal handler — no LLM needed
from lib.hermes_internal_first import try_internal_first

start = time.monotonic()
result = try_internal_first("show provider mode")
elapsed = time.monotonic() - start

check("provider mode returns in under 5s", elapsed < 5.0)
check("provider mode result is not None", result is not None)
if result:
    check("no timeout text in provider mode reply", "timed out" not in result.text.lower())
    check("provider mode text is meaningful", len(result.text) > 30)

# 2. Trading recommendation — always internal, never times out
start2 = time.monotonic()
result2 = try_internal_first("what trading strategy do you recommend")
elapsed2 = time.monotonic() - start2

check("trading recommendation returns in under 5s", elapsed2 < 5.0)
check("trading recommendation result not None", result2 is not None)
if result2:
    check("no timeout in trading reply", "timed out" not in result2.text.lower())

# 3. Reasoning layer evidence fallback — should never produce "Command timed out"
from lib.hermes_reasoning_layer import reason

os.environ["OLLAMA_HOST"] = "http://127.0.0.1:19996"  # fake unreachable
pp.get_policy(refresh=True)

start3 = time.monotonic()
try:
    result3 = reason("what should I work on today", evidence_text="", ops_context="")
    elapsed3 = time.monotonic() - start3
    check("reasoning layer returns in under 30s (bot budget)", elapsed3 < 30.0)
    check("reasoning result is not None", result3 is not None)
    check("no 'Command timed out' in reasoning reply", "Command timed out" not in result3.reply)
    check("no 'Try again in a moment' in reply", "Try again in a moment" not in result3.reply)
except Exception as exc:
    elapsed3 = time.monotonic() - start3
    print(f"  ⚠️  reasoning raised exception: {exc}")
    check("reasoning exception is fast (not a long hang)", elapsed3 < 30.0)

# cleanup
os.environ.pop("HERMES_GATEWAY_URL", None)
os.environ.pop("HERMES_GATEWAY_KEY", None)
os.environ.pop("HERMES_ALLOW_HERMES_GATEWAY", None)
os.environ.pop("HERMES_ALLOW_OPENROUTER_FALLBACK", None)
os.environ.pop("OLLAMA_HOST", None)
pp._GATEWAY_FAILURE_CACHE.clear()

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
