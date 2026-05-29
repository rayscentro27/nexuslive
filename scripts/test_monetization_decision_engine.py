"""test_monetization_decision_engine.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_monetization_decision_engine ===")
from lib.hermes_monetization_decision_engine import score_source, run_decision_cycle, OpportunityDecision

# 1. score_source returns OpportunityDecision
d = score_source({"intake_id": "test1", "source_type": "youtube",
    "title": "How to build business credit and get funding for your LLC",
    "keyword": "business credit", "monetization_potential": "high"})
check("score_source returns OpportunityDecision", isinstance(d, OpportunityDecision))
check("has monetization_score", isinstance(d.monetization_score, int))
check("score in 0-100", 0 <= d.monetization_score <= 100)
check("has status", bool(d.status))
check("has decision_id", bool(d.decision_id))
check("has decided_at", bool(d.decided_at))

# 2. High-potential sources score well
high_scores = [
    {"title": "Best affiliate programs for credit repair income",
     "source_type": "affiliate", "monetization_potential": "high"},
    {"title": "Lead magnet for business funding readiness checklist",
     "source_type": "monetization", "monetization_potential": "high"},
    {"title": "Make money with AI content funnel email newsletter",
     "source_type": "monetization", "monetization_potential": "high"},
]
for src in high_scores:
    d = score_source(src)
    check(f"high-potential source scores >= 40: {src['title'][:40]}", d.monetization_score >= 40)

# 3. Low-quality sources can be rejected
low_score = score_source({"title": "Random video about cooking", "source_type": "youtube",
    "keyword": "", "monetization_potential": "low"})
check("low-quality source has low score (< 40)", low_score.monetization_score < 40)

# 4. Fallback sources don't score too high (capped at 45)
fallback = score_source({"title": "Manual research task: google search keyword",
    "source_type": "google", "fallback": True, "monetization_potential": "high"})
check("fallback sources capped at 45", fallback.monetization_score <= 45)

# 5. Approval-gated sources detected
paid = score_source({"title": "Affiliate signup paid tool subscription",
    "source_type": "affiliate", "monetization_potential": "high"})
# Either requires approval OR has affiliate status
check("affiliate or paid source may require approval",
      paid.requires_ray_approval or paid.status in ("affiliate_candidate", "watch"))

# 6. run_decision_cycle
sample_records = [
    {"intake_id": "t1", "title": "Credit repair checklist lead magnet", "source_type": "monetization",
     "keyword": "credit", "monetization_potential": "high"},
    {"intake_id": "t2", "title": "YouTube faceless content AI automation income", "source_type": "youtube",
     "keyword": "content", "monetization_potential": "high"},
    {"intake_id": "t3", "title": "Random cooking video", "source_type": "youtube",
     "keyword": "food", "monetization_potential": "low"},
    {"intake_id": "t4", "title": "Live trading real money broker account", "source_type": "trading",
     "keyword": "live trading", "monetization_potential": "medium"},
]
result = run_decision_cycle(sample_records, mode="validation", top_n=5, dry_run=True)
check("run_decision_cycle returns dict", isinstance(result, dict))
check("has top_opportunities", isinstance(result.get("top_opportunities"), list))
check("has rejected", isinstance(result.get("rejected"), list))
check("has artifact_path", bool(result.get("artifact_path")))
check("total_scored == 4", result["total_scored"] == 4)

# 7. to_plain_english has no raw JSON
for op in result["top_opportunities"][:3]:
    from lib.hermes_monetization_decision_engine import OpportunityDecision
    d_obj = OpportunityDecision(**{k: v for k, v in op.items() if k in OpportunityDecision.__dataclass_fields__})
    pe = d_obj.to_plain_english()
    check("plain english no raw JSON braces", pe.count("{") < 3)
    check("plain english mentions score", "score" in pe.lower())

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
