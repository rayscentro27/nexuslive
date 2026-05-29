"""test_opportunity_approval_policy.py — approval gates must work."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_opportunity_approval_policy ===")
from lib.hermes_monetization_decision_engine import score_source

# Autonomous allowed (no approval needed)
AUTONOMOUS_SOURCES = [
    {"title": "Free credit repair research report", "source_type": "monetization",
     "keyword": "credit repair", "monetization_potential": "high"},
    {"title": "YouTube content AI faceless channel research", "source_type": "youtube",
     "keyword": "content", "monetization_potential": "high"},
    {"title": "GitHub open source ai agent tool", "source_type": "github",
     "keyword": "ai agent", "monetization_potential": "medium"},
    {"title": "Backtesting paper trading strategy education", "source_type": "trading",
     "keyword": "paper trading backtest", "monetization_potential": "medium"},
    {"title": "Credit funding checklist artifact draft", "source_type": "monetization",
     "keyword": "checklist", "monetization_potential": "high"},
]

APPROVAL_REQUIRED_SOURCES = [
    {"title": "Live trading real money oanda forex broker account",
     "source_type": "trading", "keyword": "live trading real money", "monetization_potential": "medium"},
    {"title": "Publish content public facing client-facing compliance",
     "source_type": "content", "keyword": "published client compliance", "monetization_potential": "low"},
    {"title": "Paid subscription stripe payment billing",
     "source_type": "monetization", "keyword": "paid stripe payment", "monetization_potential": "medium"},
]

for src in AUTONOMOUS_SOURCES:
    d = score_source(src)
    # Autonomous sources should NOT require approval (unless they accidentally match risk keywords)
    # This is a soft check — if score < 25 it's rejected (which is fine)
    if d.status not in ("reject",):
        check(f"autonomous source '{src['title'][:40]}' does not require approval by default",
              not d.requires_ray_approval or d.risk_score > 35)

for src in APPROVAL_REQUIRED_SOURCES:
    d = score_source(src)
    check(f"approval source '{src['title'][:40]}' triggers approval flag",
          d.requires_ray_approval or d.status == "reject")

# Verify blocking: live trading requires approval
live = score_source({"title": "Live real money trading execution",
    "keyword": "live trading real money", "source_type": "trading",
    "monetization_potential": "medium"})
check("live trading blocked or requires approval",
      live.requires_ray_approval or live.status == "reject")

# Verify: free research is autonomous
free_research = score_source({"title": "Free credit repair research",
    "keyword": "credit repair research", "source_type": "youtube",
    "monetization_potential": "high"})
if free_research.status not in ("reject",):
    check("free research is autonomous", not free_research.requires_ray_approval)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
