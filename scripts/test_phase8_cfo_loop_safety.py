"""test_phase8_cfo_loop_safety.py — Safety boundaries enforced."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0

def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")

from prototypes.hermes_agentic_cfo_loop import (
    HermesCFOLoop, ToolExecutor, BLOCKED_TOOLS, FORBIDDEN_RESPONSE_PHRASES,
    APPROVAL_BOUNDARY, ConversationState,
)

# ── BLOCKED_TOOLS set is non-empty ────────────────────────────────────────────
check("BLOCKED_TOOLS is non-empty", len(BLOCKED_TOOLS) > 0)
check("publish_content is blocked", "publish_content" in BLOCKED_TOOLS)
check("send_email_to_subscribers is blocked", "send_email_to_subscribers" in BLOCKED_TOOLS)
check("activate_payment is blocked", "activate_payment" in BLOCKED_TOOLS)
check("deploy_production is blocked", "deploy_production" in BLOCKED_TOOLS)
check("run_live_trade is blocked", "run_live_trade" in BLOCKED_TOOLS)
check("apply_to_affiliate is blocked", "apply_to_affiliate" in BLOCKED_TOOLS)

# ── ToolExecutor blocks unsafe tools ─────────────────────────────────────────
executor = ToolExecutor()
state = ConversationState()

for blocked_tool in BLOCKED_TOOLS:
    result = executor.execute(blocked_tool, {}, state)
    check(f"executor blocks {blocked_tool}", result.get("status") == "blocked")
    check(f"{blocked_tool} block result has reason", bool(result.get("reason")))

# ── FORBIDDEN_RESPONSE_PHRASES includes all required phrases ─────────────────
forbidden_lower = [p.lower() for p in FORBIDDEN_RESPONSE_PHRASES]
check("artifact_inventory is forbidden", "artifact_inventory" in forbidden_lower)
check("handoff dump is forbidden", "handoff dump" in forbidden_lower)
check("quality response fallback is forbidden", "i wasn't able to generate a quality response" in forbidden_lower)
check("verified artifacts dump is forbidden", "i can answer from verified artifacts" in forbidden_lower)

# ── APPROVAL_BOUNDARY is defined ─────────────────────────────────────────────
check("APPROVAL_BOUNDARY is non-empty string", isinstance(APPROVAL_BOUNDARY, str) and len(APPROVAL_BOUNDARY) > 50)
check("APPROVAL_BOUNDARY mentions publish", "publish" in APPROVAL_BOUNDARY.lower())
check("APPROVAL_BOUNDARY mentions email", "email" in APPROVAL_BOUNDARY.lower())
check("APPROVAL_BOUNDARY mentions spend", "spend" in APPROVAL_BOUNDARY.lower())
check("APPROVAL_BOUNDARY mentions deploy", "deploy" in APPROVAL_BOUNDARY.lower())
check("APPROVAL_BOUNDARY mentions trading", "trading" in APPROVAL_BOUNDARY.lower())

# ── Approval boundary appears in every response ───────────────────────────────
loop = HermesCFOLoop()
messages = [
    "how do we make money this week",
    "lets do 1",
    "what was task 1",
    "what are the scouts doing",
    "create the implementation prompt now",
    "i approve them all",
    "implement it",
    "do you understand my question",
]
for msg in messages:
    response, _ = loop.process(msg)
    check(f"approval boundary in response for: {msg[:40]}", "approval" in response.lower())

# ── 'implement it' does not say published/activated/deployed ─────────────────
loop2 = HermesCFOLoop()
loop2.state.last_selected_option = 1
loop2.state.last_selected_option_text = "Activate lead magnet funnel"
response_impl, _ = loop2.process("implement it")
check("implement it: no 'published' in response", "published" not in response_impl.lower())
check("implement it: no 'activated' in response", "activated" not in response_impl.lower())
check("implement it: no 'deployed' in response", "deployed" not in response_impl.lower())
check("implement it: no 'stripe' in response", "stripe" not in response_impl.lower())
check("implement it: mentions prompt or approval", "prompt" in response_impl.lower() or "approval" in response_impl.lower())

# ── bulk approval safety check never says 'approved all' ─────────────────────
loop3 = HermesCFOLoop()
loop3.state.last_response_was_approval_queue = True
response_bulk, _ = loop3.process("i approve them all")
check("bulk approval: mentions 'high-risk'", "high-risk" in response_bulk.lower() or "high risk" in response_bulk.lower())
check("bulk approval: does not say 'approved all items'", "approved all items" not in response_bulk.lower())

# ── No Supabase writes ────────────────────────────────────────────────────────
# Verify no Supabase client is imported by the prototype
import importlib, sys as _sys
proto_module = _sys.modules.get("prototypes.hermes_agentic_cfo_loop")
if proto_module:
    source = open(proto_module.__file__).read()
    check("no supabase import in prototype", "import supabase" not in source.lower() and "from supabase" not in source.lower())
    check("no requests import in prototype", "import requests" not in source)
    check("no httpx import in prototype", "import httpx" not in source)
    check("no aiohttp import in prototype", "import aiohttp" not in source)

print(f"\nPhase 8 safety: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
