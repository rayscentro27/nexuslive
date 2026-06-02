"""
test_daily_operating_cycle_continue_while_out.py
Tests: format_continue_while_out_plan lists only safe internal work.
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


print("=== test_daily_operating_cycle_continue_while_out ===\n")

from lib.hermes_daily_operating_cycle import format_continue_while_out_plan, SAFE_INTERNAL_WORK, BLOCKED_ACTIONS

# ── format_continue_while_out_plan: structure ─────────────────────────────
print("-- format_continue_while_out_plan: structure --")
resp = format_continue_while_out_plan()

check("non-empty",                                    bool(resp))
check("starts with CONTINUE WHILE YOU ARE OUT",       resp.startswith("CONTINUE WHILE YOU ARE OUT"))
check("contains 'I can safely continue internal'",    "safely continue internal" in resp.lower())
check("contains 'I will:' section",                   "I will:" in resp)
check("contains 'I will not:' section",               "I will not:" in resp)
check("contains next check-in instruction",           "check-in" in resp.lower() or "check in" in resp.lower()
                                                       or "Next check" in resp)

# ── safe actions are listed ───────────────────────────────────────────────
print("\n-- safe actions listed --")
for act in SAFE_INTERNAL_WORK:
    check(f"safe action: '{act[:40]}' in response", act[:40] in resp)

# ── blocked actions are listed ────────────────────────────────────────────
print("\n-- blocked actions listed --")
check("'publish' in blocked section",         "publish" in resp.lower())
check("'email' in blocked section",           "email" in resp.lower())
check("'spend money' in blocked section",     "spend money" in resp.lower())
check("'live trading' in blocked section",    "live trading" in resp.lower() or "live trade" in resp.lower())
check("'deploy' in blocked section",          "deploy" in resp.lower())

# ── BLOCKED_ACTIONS is defined ────────────────────────────────────────────
print("\n-- BLOCKED_ACTIONS constant --")
check("BLOCKED_ACTIONS is list",              isinstance(BLOCKED_ACTIONS, list))
check("BLOCKED_ACTIONS not empty",            len(BLOCKED_ACTIONS) > 0)
check("contains publish",                     any("publish" in a.lower() for a in BLOCKED_ACTIONS))
check("contains trading",                     any("trading" in a.lower() or "trade" in a.lower() for a in BLOCKED_ACTIONS))
check("contains spend",                       any("spend" in a.lower() for a in BLOCKED_ACTIONS))

# ── SAFE_INTERNAL_WORK is defined ────────────────────────────────────────
print("\n-- SAFE_INTERNAL_WORK constant --")
check("SAFE_INTERNAL_WORK is list",           isinstance(SAFE_INTERNAL_WORK, list))
check("SAFE_INTERNAL_WORK not empty",         len(SAFE_INTERNAL_WORK) > 0)
check("contains research or review",
      any("research" in a.lower() or "review" in a.lower() for a in SAFE_INTERNAL_WORK))

# ── no evidence dump ──────────────────────────────────────────────────────
print("\n-- no evidence dump --")
DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory",
                "I can answer from verified", "═══", "HERMES REPORT"]
check("no evidence dump",
      not any(m in resp for m in DUMP_MARKERS))

# ── routing ────────────────────────────────────────────────────────────────
print("\n-- routing: daily_continue_while_out intent --")
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

for phrase in [
    "continue while i am out",
    "keep working while i am out",
    "what can you do while i am gone",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == daily_continue_while_out", intent == "daily_continue_while_out")
    resp_r = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty",                         bool(resp_r))
    check(f"'{phrase}': CONTINUE WHILE YOU ARE OUT",        "CONTINUE WHILE YOU ARE OUT" in resp_r)
    # "publish" appears in the "I will not:" list — acceptable; check no command to actually do it
    check(f"'{phrase}': no command to publish",
          "i will publish" not in resp_r.lower() and "hermes will publish" not in resp_r.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
