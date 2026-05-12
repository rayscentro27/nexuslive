"""Tests for knowledge_quality.py"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from datetime import datetime, timezone, timedelta
from lib.knowledge_quality import (
    score_knowledge_record, freshness_status,
    QUALITY_HIGH, QUALITY_MEDIUM, QUALITY_LOW, QUALITY_REJECT,
)


def test_high_quality_grant():
    content = (
        "SBIR Phase I grant from NSF. Award: $275,000. "
        "Eligibility: US for-profit small business <500 employees. "
        "Deadline: rolling. Apply at https://www.sbir.gov. "
        "Required: technical proposal, budget, PI credentials."
    )
    qs = score_knowledge_record(
        content=content,
        domain="grants",
        source_url="https://www.sbir.gov",
        created_at=datetime.now(timezone.utc) - timedelta(days=5),
    )
    assert qs.quality_score >= 70, f"Expected high score, got {qs.quality_score}"
    assert qs.quality_label == QUALITY_HIGH
    assert qs.recommended_action == "approve"
    print(f"✓ test_high_quality_grant: score={qs.quality_score}, label={qs.quality_label}")


def test_stale_trading_strategy():
    content = "London breakout strategy. Entry on 15m candle break. SL 20 pips. TP 40 pips."
    qs = score_knowledge_record(
        content=content,
        domain="trading",
        source_url="https://example.com/strategy",
        created_at=datetime.now(timezone.utc) - timedelta(days=60),  # 60 days old, threshold=14
    )
    # Should be penalized for staleness
    assert qs.freshness <= 5, f"Expected stale score, got freshness={qs.freshness}"
    print(f"✓ test_stale_trading_strategy: score={qs.quality_score}, freshness={qs.freshness}")


def test_hallucination_rejection():
    content = "This grant is 100% guaranteed approval! Get $50k instantly — no credit check required."
    qs = score_knowledge_record(content=content, domain="grants")
    assert qs.hallucination_risk_penalty >= 6, f"Expected high penalty, got {qs.hallucination_risk_penalty}"
    assert qs.quality_label in (QUALITY_LOW, QUALITY_REJECT)
    print(f"✓ test_hallucination_rejection: score={qs.quality_score}, label={qs.quality_label}")


def test_empty_content():
    qs = score_knowledge_record(content="", domain="trading")
    assert qs.quality_label == QUALITY_REJECT
    assert qs.recommended_action == "reject"
    print(f"✓ test_empty_content: score={qs.quality_score}")


def test_trusted_gov_source():
    content = "SBA 7(a) loan program. Award up to $5 million. Apply at sba.gov. Eligibility: US small business."
    qs = score_knowledge_record(content=content, domain="funding", source_url="https://www.sba.gov/loans")
    assert qs.source_reliability == 25
    print(f"✓ test_trusted_gov_source: source_reliability={qs.source_reliability}")


def test_freshness_status():
    now = datetime.now(timezone.utc)
    assert freshness_status("trading", now - timedelta(days=2)) == "fresh"
    assert freshness_status("trading", now - timedelta(days=10)) == "acceptable"
    assert freshness_status("trading", now - timedelta(days=20)) == "stale"
    assert freshness_status("trading", now - timedelta(days=60)) == "expired"
    assert freshness_status("grants", now - timedelta(days=30)) == "acceptable"  # grants threshold=60d; 30d > 60//4=15d
    print("✓ test_freshness_status: all domain thresholds correct")


def test_duplicate_detection():
    content = "Amber Grant for women — $10,000 monthly. Apply at ambergrantsforwomen.com"
    import hashlib
    h = hashlib.md5(content.strip().lower().encode()).hexdigest()
    qs = score_knowledge_record(content=content, domain="grants", existing_hashes=[h])
    assert qs.duplicate_risk_penalty == 5
    print(f"✓ test_duplicate_detection: penalty={qs.duplicate_risk_penalty}")


if __name__ == "__main__":
    tests = [
        test_high_quality_grant,
        test_stale_trading_strategy,
        test_hallucination_rejection,
        test_empty_content,
        test_trusted_gov_source,
        test_freshness_status,
        test_duplicate_detection,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
            failed += 1
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
