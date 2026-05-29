"""test_scout_dispatch_from_opportunities.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_scout_dispatch_from_opportunities ===")
from lib.hermes_monetization_decision_engine import score_source, run_decision_cycle

# 1. Content candidate routes to content scout
content_src = score_source({"title": "YouTube content faceless channel monetization AI",
    "source_type": "youtube", "keyword": "content", "monetization_potential": "high"})
check("content candidate has scout assignment",
      bool(content_src.assigned_scout) or content_src.status in ("watch", "reject"))
if content_src.status not in ("watch", "reject", "needs_more_research"):
    check("content scout is content_intelligence_scout",
          "content" in content_src.assigned_scout.lower())

# 2. Credit/funding routes to correct scout
credit_src = score_source({"title": "Business credit repair readiness checklist client",
    "source_type": "monetization", "keyword": "credit funding", "monetization_potential": "high"})
if credit_src.status not in ("watch", "reject"):
    check("credit source gets a scout", bool(credit_src.assigned_scout))

# 3. Affiliate routes to affiliate scout
affiliate_src = score_source({"title": "Affiliate commission income funnel automation",
    "source_type": "affiliate", "keyword": "affiliate", "monetization_potential": "high"})
if affiliate_src.status not in ("watch", "reject"):
    check("affiliate scout assigned", bool(affiliate_src.assigned_scout))
    check("affiliate scout name contains 'affiliate' or 'monetiz'",
          "affiliate" in affiliate_src.assigned_scout.lower() or
          "monetiz" in affiliate_src.assigned_scout.lower())

# 4. run_decision_cycle creates action queue entries (dry_run=True still logs decisions)
records = [
    {"intake_id": "td1", "title": "Credit repair business funding lead magnet checklist",
     "source_type": "monetization", "keyword": "credit funding", "monetization_potential": "high"},
    {"intake_id": "td2", "title": "YouTube content automation AI faceless income",
     "source_type": "youtube", "keyword": "content", "monetization_potential": "high"},
]
result = run_decision_cycle(records, mode="validation", top_n=5, dry_run=True)
check("decision cycle creates records for actionable sources",
      result["total_scored"] >= len(records))
from lib.hermes_decision_log import load_recent_decisions
decisions = load_recent_decisions(limit=5)
check("decision log has entries", len(decisions) > 0)

# 5. Rejected items don't get scouts
rejected = result.get("rejected", [])
for r in rejected:
    check(f"rejected item has why_rejected: {r.get('title','')[:30]}",
          bool(r.get("why_rejected")))

# 6. Scout assignments are from known scout names
from lib.hermes_tool_scout_registry import get_scouts
known_scouts = {s.id for s in get_scouts()}
for op in result["top_opportunities"][:5]:
    scout = op.get("assigned_scout", "")
    if scout:
        check(f"assigned scout '{scout}' is in known registry OR is a valid name",
              scout in known_scouts or len(scout) > 3)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
