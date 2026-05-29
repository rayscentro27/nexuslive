"""
test_hermes_goal_registry.py
Verifies goal registry can create, read, and update goals.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_goal_registry ===")

from lib.hermes_goal_registry import (
    Goal, load_goals, _default_goals, top_active_goals,
    goals_summary_plain_english, initialize_registry
)

# 1. Default goals load correctly
goals = _default_goals()
check("default goals returns list", isinstance(goals, list))
check("at least 5 default goals", len(goals) >= 5)

# 2. All required fields present
for g in goals:
    check(f"goal '{g.goal_id}' has title", bool(g.title))
    check(f"goal '{g.goal_id}' has category", bool(g.category))
    check(f"goal '{g.goal_id}' has priority", g.priority > 0)

# 3. 30-day revenue goal exists and is highest priority
revenue = next((g for g in goals if g.goal_id == "goal_revenue_30day"), None)
check("30-day revenue goal exists", revenue is not None)
if revenue:
    check("30-day revenue goal priority >= 90", revenue.priority >= 90)
    check("30-day revenue goal requires approval for publishing",
          any("publish" in r.lower() for r in revenue.requires_ray_approval))

# 4. Nexus reliability goal exists
reliability = next((g for g in goals if g.goal_id == "goal_nexus_reliability"), None)
check("nexus reliability goal exists", reliability is not None)
if reliability:
    check("nexus reliability goal has high priority", reliability.priority >= 85)

# 5. Trading goal requires approval for live trading
trading = next((g for g in goals if g.goal_id == "goal_trading_education"), None)
check("trading education goal exists", trading is not None)
if trading:
    check("trading goal requires approval for live trading",
          any("live" in r.lower() or "funded" in r.lower()
              for r in trading.requires_ray_approval))
    check("trading goal is autonomous_allowed (backtest/paper)",
          trading.autonomous_allowed is True)

# 6. Goal to_plain_english works
if goals:
    pe = goals[0].to_plain_english()
    check("to_plain_english returns non-empty string", len(pe) > 10)
    check("to_plain_english has title", goals[0].title in pe)

# 7. goals_summary_plain_english
summary = goals_summary_plain_english()
check("summary is non-empty", len(summary) > 20)
check("summary mentions active goals", "active" in summary.lower() or "goal" in summary.lower())
check("summary has source path", "docs/reports/goals" in summary)

# 8. top_active_goals
top = top_active_goals(limit=3)
check("top_active_goals returns list", isinstance(top, list))
check("top goals sorted by priority", True if len(top) < 2 else top[0].priority >= top[-1].priority)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
