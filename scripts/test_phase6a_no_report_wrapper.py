"""
test_phase6a_no_report_wrapper.py
Tests: all Phase 6A commands return plain text, never wrapped in HERMES REPORT.
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


print("=== test_phase6a_no_report_wrapper ===\n")

from hermes_command_router.router import run_command

PHASE6A_COMMANDS = {
    "daily plan":                      "TODAY'S NEXUS PLAN",
    "what should i work on today":     "TODAY'S NEXUS PLAN",
    "show today's nexus plan":         "TODAY'S NEXUS PLAN",
    "what needs my approval":          "APPROVAL NEEDED",
    "show approval queue":             "APPROVAL NEEDED",
    "pending approvals":               "APPROVAL NEEDED",
    "continue while i am out":         "CONTINUE WHILE YOU ARE OUT",
    "keep working while i am out":     "CONTINUE WHILE YOU ARE OUT",
    "show today's top revenue move":   "TODAY'S TOP MONEY MOVE",
    "what can make money today":       "TODAY'S TOP MONEY MOVE",
    "show today's blockers":           "TODAY'S BLOCKERS",
    "what is blocked":                 "TODAY'S BLOCKERS",
    "blockers today":                  "TODAY'S BLOCKERS",
}

REPORT_MARKERS = ["HERMES REPORT", "═══", "Evidence:", "artifact_inventory"]

print("-- no HERMES REPORT wrapper on any Phase 6A command --")
for cmd, expected_header in PHASE6A_COMMANDS.items():
    resp = run_command(cmd, source="cli")
    check(f"'{cmd[:45]}': non-empty", bool(resp))
    check(f"'{cmd[:45]}': starts with {expected_header!r}", resp.startswith(expected_header))
    check(f"'{cmd[:45]}': no HERMES REPORT wrapper",
          not resp.strip().startswith("HERMES REPORT"))
    check(f"'{cmd[:45]}': no ═══", "═══" not in resp)

print("\n-- Phase 6A intents in _PLAIN_INTENTS (not _INTENT_HANDLERS) --")
from hermes_command_router.router import _PLAIN_INTENTS, _INTENT_HANDLERS
PHASE6A_INTENTS = [
    "daily_operating_cycle", "daily_approval_needed",
    "daily_continue_while_out", "daily_top_revenue_move", "daily_blockers",
]
for intent in PHASE6A_INTENTS:
    check(f"'{intent}' in _PLAIN_INTENTS", intent in _PLAIN_INTENTS)
    check(f"'{intent}' not in _INTENT_HANDLERS", intent not in _INTENT_HANDLERS)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
