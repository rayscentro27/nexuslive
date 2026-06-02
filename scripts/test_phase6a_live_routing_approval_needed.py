"""
test_phase6a_live_routing_approval_needed.py
Tests: daily_approval_needed intent routes correctly for all approval phrases.
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


print("=== test_phase6a_live_routing_approval_needed ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

APPROVAL_PHRASES = [
    "show approval queue",
    "show items needing approval",
    "approval queue",
    "what is waiting for my approval",
    "show approval needed",
    "what needs ray approval",
    "show what needs approval",
    "what needs my approval",
    "pending approvals",
    "approval needed",
    "what is waiting for approval",
    "what requires approval",
    "what is pending approval",
]

print("-- classify_intent: all approval phrases → daily_approval_needed --")
for phrase in APPROVAL_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({repr(phrase[:55])}) == daily_approval_needed",
          intent == "daily_approval_needed")

print("\n-- run_command: approval output structure --")
for phrase in ["what needs my approval", "show approval queue", "approval queue"]:
    resp = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty", bool(resp))
    check(f"'{phrase}': APPROVAL NEEDED header", "APPROVAL NEEDED" in resp)
    check(f"'{phrase}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
    check(f"'{phrase}': no ═══", "═══" not in resp)
    check(f"'{phrase}': approval boundary", "Approval" in resp or "approval" in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
