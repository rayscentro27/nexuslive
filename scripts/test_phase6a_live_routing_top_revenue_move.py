"""
test_phase6a_live_routing_top_revenue_move.py
Tests: daily_top_revenue_move intent routes correctly including new money phrases.
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


print("=== test_phase6a_live_routing_top_revenue_move ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

REVENUE_PHRASES = [
    "show today's top revenue move",
    "show today's top money move",
    "top revenue move",
    "top money move today",
    "best revenue move today",
    "what is the top revenue move",
    "today's top money move",
    "today's top revenue move",
    "show top money move",
    "show revenue move",
    "what can make money today",
    "how do we make money today",
    "todays top revenue move",
    "todays top money move",
]

print("-- classify_intent: all revenue phrases → daily_top_revenue_move --")
for phrase in REVENUE_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:55])}) == daily_top_revenue_move",
          intent == "daily_top_revenue_move")

print("\n-- run_command: revenue output structure --")
for phrase in ["show today's top revenue move", "what can make money today", "top revenue move"]:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:45]}': non-empty", bool(resp))
    check(f"'{phrase[:45]}': TODAY'S TOP MONEY MOVE", "TODAY'S TOP MONEY MOVE" in resp)
    check(f"'{phrase[:45]}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"'{phrase[:45]}': no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
