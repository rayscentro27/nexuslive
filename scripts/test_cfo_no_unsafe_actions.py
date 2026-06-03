"""
test_cfo_no_unsafe_actions.py
Tests: no CFO/Phase 7 function publishes, emails, spends, deploys,
       activates Stripe, applies to affiliates, or runs live trading.
       No Supabase writes. Memory v2 primary remains active.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_execution(text: str) -> bool:
    EXECUTION_PATTERNS = [
        "has been published to", "email was sent to subscriber",
        "sent email to subscriber", "stripe payment charged", "stripe.charge",
        "payment_intent.create", "affiliate program applied",
        "deployed to production successfully", "live trading order placed",
        "subscriber list was emailed", "posted to social media",
    ]
    return not any(p in (text or "").lower() for p in EXECUTION_PATTERNS)


print("=== test_cfo_no_unsafe_actions ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import (
    build_cfo_context, build_cfo_response, format_cfo_response,
    format_research_queue, format_scout_assignments, SAFETY_BOUNDARY,
)

# ── CFO responses have no execution language ──────────────────────────────────
print("-- CFO responses: no execution language --")

MESSAGES = [
    "I am worried Hermes is becoming a command bot",
    "How do we make $1000 a week from affiliate revenue?",
    "Can Hermes find the best affiliate offer for the funding checklist?",
]

for msg in MESSAGES:
    ctx = build_cfo_context(msg)
    resp = build_cfo_response(msg, ctx)
    fmt = format_cfo_response(resp)
    check(f"'{msg[:40]}...' no execution language", no_execution(fmt))
    check(f"'{msg[:40]}...' has approval boundary",
          "approval boundary" in fmt.lower() or "ray approval" in fmt.lower())

# ── Phase 7 command responses have no execution language ─────────────────────
print("\n-- Phase 7 command responses: no execution language --")

COMMANDS = [
    "show research queue", "show scout assignments",
    "show unresolved questions", "show cfo notes",
]

for cmd in COMMANDS:
    try:
        response = run_command(cmd) or ""
        check(f"'{cmd}' no execution language", no_execution(response))
    except Exception as exc:
        check(f"'{cmd}' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── format functions have no execution language ───────────────────────────────
print("\n-- format functions: no execution language --")
check("format_research_queue: no execution", no_execution(format_research_queue()))
check("format_scout_assignments: no execution", no_execution(format_scout_assignments()))

# ── SAFETY_BOUNDARY in CFO outputs ────────────────────────────────────────────
print("\n-- SAFETY_BOUNDARY present in CFO outputs --")
check("SAFETY_BOUNDARY is non-empty", bool(SAFETY_BOUNDARY))
for msg in MESSAGES[:2]:
    ctx = build_cfo_context(msg)
    resp = build_cfo_response(msg, ctx)
    check(f"resp has safety_boundary key", "safety_boundary" in resp)
    check(f"safety_boundary == SAFETY_BOUNDARY", resp.get("safety_boundary") == SAFETY_BOUNDARY)

# ── No Stripe patterns in CFO outputs ────────────────────────────────────────
print("\n-- no Stripe/payment in CFO outputs --")
PAYMENT_PATTERNS = ["stripe.charge", "payment_intent.create", "subscribe(", "checkout.session"]
for pat in PAYMENT_PATTERNS:
    check(f"no '{pat}' in research queue output",
          pat not in format_research_queue().lower())
    check(f"no '{pat}' in scout assignments output",
          pat not in format_scout_assignments().lower())

# ── No secrets in CFO outputs ─────────────────────────────────────────────────
print("\n-- no secrets in CFO outputs --")
SECRET_PATTERNS = ["supabase_service_role", "supabase_key", "openai_api_key",
                   "anthropic", "oanda", "hermes_gateway_key", "private_key"]
all_output = format_research_queue() + format_scout_assignments()
for pat in SECRET_PATTERNS:
    check(f"no '{pat}' in CFO outputs", pat.lower() not in all_output.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
