"""
test_youtube_quality_reviewer.py — Tests for lib/youtube_quality_reviewer.py
"""
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_youtube_quality_reviewer ===\n")

import lib.youtube_quality_reviewer as _mod

# Use temp dir for artifacts
with tempfile.TemporaryDirectory() as tmpdir:
    orig_reports_dir = _mod.REPORTS_DIR
    _mod.REPORTS_DIR = Path(tmpdir)

    from lib.youtube_quality_reviewer import YouTubeQualityReviewer, STATUSES

    reviewer = YouTubeQualityReviewer()

    # 1. Heuristic scoring — credit repair channel
    scores = reviewer._score_heuristic(
        url="https://youtube.com/@CreditRepairHero",
        channel_name="Credit Repair Hero",
        video_title="How to dispute collections and boost your credit score",
        description="Step by step guide to credit repair and FICO improvement",
        published_at="2025-01-15",
    )
    check("heuristic returns all 10 dimensions",
          set(scores.keys()) == set(_mod.DIMENSIONS))
    check("content_relevance > 5 for credit channel",
          scores["content_relevance"] > 5)

    # 2. Heuristic scoring — risky "guarantee" content
    risky_scores = reviewer._score_heuristic(
        url="https://youtube.com/watch?v=risky123",
        channel_name="Easy Credit Fix",
        video_title="Guaranteed credit score jump overnight with this secret method",
        description="100% success rate, instant credit repair loophole",
        published_at="2024-06-01",
    )
    check("guarantee language lowers compliance_safety",
          risky_scores["compliance_safety"] < 5)

    # 3. Classify status
    high_scores = {d: 8.0 for d in _mod.DIMENSIONS}
    check("status=high_value when all scores 8+",
          reviewer._classify_status(high_scores, "https://x.com", [], []) == "high_value")

    mid_scores = {d: 6.0 for d in _mod.DIMENSIONS}
    check("status=useful_but_needs_review when all scores 6",
          reviewer._classify_status(mid_scores, "https://x.com", [], []) == "useful_but_needs_review")

    # compliance_safety must be >= 4 to avoid "risky" classification
    low_scores = {d: 4.0 for d in _mod.DIMENSIONS}
    low_scores["compliance_safety"] = 6.0  # safe; overall ~4.2 → low_quality
    check("status=low_quality when overall < 5 and compliance_safety ok",
          reviewer._classify_status(low_scores, "https://x.com", [], []) == "low_quality")

    risky_s = dict(_mod.DIMENSIONS[i] if isinstance(_mod.DIMENSIONS[i], tuple) else (_mod.DIMENSIONS[i], 8.0) for i in range(10))
    risky_s2 = {d: 8.0 for d in _mod.DIMENSIONS}
    risky_s2["compliance_safety"] = 2.0
    check("status=risky when compliance_safety < 4",
          reviewer._classify_status(risky_s2, "https://x.com", [], []) == "risky")

    irrelevant_s = {d: 8.0 for d in _mod.DIMENSIONS}
    irrelevant_s["content_relevance"] = 2.0
    check("status=irrelevant when content_relevance < 3",
          reviewer._classify_status(irrelevant_s, "https://x.com", [], []) == "irrelevant")

    # Duplicate
    check("status=duplicate when url in known_duplicates",
          reviewer._classify_status(high_scores, "https://x.com", ["https://x.com"], []) == "duplicate")

    # 4. Full review (heuristic only, no LLM)
    review = reviewer.review(
        source_id="yt_test123456789",
        url="https://youtube.com/@CreditFixPro",
        channel_name="Credit Fix Pro",
        video_title="Dispute letters that actually work",
        description="Learn credit dispute strategies from a certified credit counselor",
    )
    check("review returns QualityReview",       hasattr(review, "quality_score"))
    check("quality_score is float",             isinstance(review.quality_score, float))
    check("status is a valid status",           review.status in STATUSES)
    check("artifact_path is set",               bool(review.artifact_path))
    check("artifact file exists",               Path(review.artifact_path).exists())

    _mod.REPORTS_DIR = orig_reports_dir

# 5. Status constants
check("7 status values defined", len(STATUSES) == 7)
check("high_value in STATUSES",  "high_value" in STATUSES)
check("risky in STATUSES",       "risky" in STATUSES)
check("duplicate in STATUSES",   "duplicate" in STATUSES)

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
