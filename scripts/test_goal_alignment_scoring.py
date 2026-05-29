"""test_goal_alignment_scoring.py — opportunities must align with Nexus goals."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_goal_alignment_scoring ===")
from lib.hermes_monetization_decision_engine import score_source
from lib.hermes_goal_registry import load_goals

# 1. Goals load
goals = load_goals()
check("goals loaded", len(goals) >= 3)

goal_titles = {g.title.lower() for g in goals}
# Revenue goal
check("30-day revenue goal exists", any("revenue" in t or "30" in t for t in goal_titles))
# Content goal
check("content goal exists", any("content" in t for t in goal_titles))

# 2. Credit/funding sources align with goals
credit_src = score_source({
    "title": "Business credit building and funding readiness checklist",
    "keyword": "business credit funding grant",
    "source_type": "monetization",
    "monetization_potential": "high"
})
check("credit/funding source has goal_alignment_score > 0", credit_src.goal_alignment_score > 0)
check("credit source has goal_supported field", bool(credit_src.goal_supported))
check("credit source status is not reject",
      credit_src.status not in ("reject",) or credit_src.monetization_score < 25)

# 3. Revenue-generating sources align with 30-day goal
revenue_src = score_source({
    "title": "Affiliate program for business funding credit repair make money",
    "keyword": "affiliate income revenue",
    "source_type": "affiliate",
    "monetization_potential": "high"
})
check("revenue source goal mentions revenue goal", "revenue" in revenue_src.goal_supported.lower()
      or "30-day" in revenue_src.goal_supported.lower() or "affiliate" in revenue_src.goal_supported.lower())

# 4. Recommended actions must have goal context
for src in [credit_src, revenue_src]:
    check(f"opportunity has recommended_action ({src.title[:30]})", bool(src.recommended_action))
    check(f"opportunity has goal_supported ({src.title[:30]})", bool(src.goal_supported))

# 5. Live trading without approval is blocked
live_trading = score_source({
    "title": "Live trading real money forex oanda",
    "keyword": "live trading real money",
    "source_type": "trading",
    "monetization_potential": "medium",
})
check("live trading requires approval", live_trading.requires_ray_approval)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
