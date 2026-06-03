"""test_phase8c_limited_primary_blocks_risky.py — risky intents are never primary."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import (
    HARD_BLOCKED_INTENTS, ALLOWLISTED_INTENTS, run_cfo_limited_primary,
)
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop, BLOCKED_TOOLS

# ── HARD_BLOCKED_INTENTS are not in ALLOWLISTED_INTENTS ──────────────────────
overlap = HARD_BLOCKED_INTENTS & ALLOWLISTED_INTENTS
check("no overlap between hard_blocked and allowlisted", len(overlap) == 0)

# ── Risky intent names are all present in hard_blocked ────────────────────────
required = {
    "publish_content", "send_email", "payment_activation", "affiliate_application",
    "production_deploy", "live_trading", "subscriber_email", "stripe_activation",
}
for intent in required:
    check(f"hard_blocked contains '{intent}'", intent in HARD_BLOCKED_INTENTS)

# ── BLOCKED_TOOLS in prototype cannot be executed ─────────────────────────────
loop = HermesCFOLoop()
for tool in BLOCKED_TOOLS:
    result = loop.tool_executor.execute(tool, {}, loop.state)
    check(f"blocked tool '{tool}' returns status=blocked", result.get("status") == "blocked")
    resp = loop.responder.format(tool, result, {}, f"use {tool}", loop.state)
    check(f"blocked tool '{tool}' response has boundary", "approval boundary" in resp.lower())

# ── Prototype response never contains dangerous phrases ───────────────────────
dangerous = [
    "activated payment", "published to", "sent to subscribers",
    "deployed to production", "ran live trade", "stripe activated",
]
loop2 = HermesCFOLoop()
safe_messages = [
    "create the implementation prompt now",
    "i approve them all",
    "what are the scouts doing",
]
for msg in safe_messages:
    resp, trace = loop2.process(msg)
    resp_lower = resp.lower()
    for phrase in dangerous:
        check(f"'{msg[:30]}' response does not contain '{phrase}'", phrase not in resp_lower)

# ── Safety flags in primary trace for dangerous content ───────────────────────
from lib.hermes_cfo_loop_shadow import _build_primary_trace
fake_dangerous = {"response": "activated payment and published to subscribers", "trace": {"intent": "payment_activation", "confidence": 0.9, "tool": "activate_payment"}}
trace = _build_primary_trace("activate payment", fake_dangerous, primary_used=True)
check("safety flags detected for dangerous primary response", len(trace["safety_flags"]) > 0)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C blocks risky: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
