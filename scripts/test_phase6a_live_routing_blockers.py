"""
test_phase6a_live_routing_blockers.py
Tests: daily_blockers intent routes correctly including apostrophe-free variants.
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


print("=== test_phase6a_live_routing_blockers ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

BLOCKER_PHRASES = [
    "show today's blockers",
    "show blockers",
    "what is blocked",
    "what is stopping us",
    "show current blockers",
    "what are the blockers",
    "today's blockers",
    "current blockers",
    "what's blocked",
    "blockers today",
    "todays blockers",
]

print("-- classify_intent: all blocker phrases → daily_blockers --")
for phrase in BLOCKER_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:55])}) == daily_blockers",
          intent == "daily_blockers")

print("\n-- run_command: blockers output structure --")
for phrase in ["show today's blockers", "what is blocked", "blockers today", "todays blockers"]:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase[:45]}': non-empty", bool(resp))
    check(f"'{phrase[:45]}': TODAY'S BLOCKERS", "TODAY'S BLOCKERS" in resp)
    check(f"'{phrase[:45]}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"'{phrase[:45]}': no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
