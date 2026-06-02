"""
test_30_day_revenue_plan_no_generic_money_plan.py
Tests:
  - 30-day phrases do NOT route to daily_top_revenue_move (TODAY'S MONEY PLAN)
  - "how do we make money today" still routes to daily_top_revenue_move
  - 30-day plan is NOT the same as today's money move
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


print("=== test_30_day_revenue_plan_no_generic_money_plan ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── 30-day phrases must NOT route to daily_top_revenue_move ───────────────────
print("-- 30-day phrases do NOT route to daily_top_revenue_move --")
THIRTY_DAY_PHRASES = [
    "30 day revenue plan",
    "30-day revenue plan",
    "plan to make money this month",
    "how do we make money this month",
    "make money in the next 30 days",
    "get to 1000 a week",
]
for phrase in THIRTY_DAY_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:50]}': intent != daily_top_revenue_move",
          intent != "daily_top_revenue_move")
    check(f"'{phrase[:50]}': intent == thirty_day_revenue_plan",
          intent == "thirty_day_revenue_plan")

# ── "how do we make money today" still routes to daily_top_revenue_move ────────
print("\n-- 'today' money phrases still route to daily_top_revenue_move --")
TODAY_PHRASES = [
    "how do we make money today",
    "what can make money today",
    "show today's top revenue move",
    "top revenue move",
    "top money move today",
]
for phrase in TODAY_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:50]}': intent == daily_top_revenue_move",
          intent == "daily_top_revenue_move")

# ── Response headers differ between 30-day and today ─────────────────────────
print("\n-- 30-day plan header different from today's money plan --")
resp_30 = run_command("30 day revenue plan", source="cli")
resp_today = run_command("how do we make money today", source="cli")

check("30-day starts with '30-DAY NEXUS REVENUE PLAN'",
      resp_30.startswith("30-DAY NEXUS REVENUE PLAN"))
check("today's plan starts with 'TODAY'S TOP MONEY MOVE'",
      resp_today.startswith("TODAY'S TOP MONEY MOVE"))
check("30-day does NOT start with 'TODAY'S'", not resp_30.startswith("TODAY'S"))
check("today's does NOT start with '30-DAY'", not resp_today.startswith("30-DAY"))

# ── 30-day plan has week structure; today's does not need it ─────────────────
check("30-day has 'Week 1'", "Week 1" in resp_30)
check("30-day has 'Week 4'", "Week 4" in resp_30)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
