"""
funding_engine_test.py — lightweight backend tests for the Nexus funding engine.

Run:
    python3 /Users/raymonddavis/nexus-ai/funding_engine/funding_engine_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import funding_engine.service as service
from funding_engine.approval_scoring import score_approval_recommendation
import funding_engine.billing_events as billing_events
from funding_engine.billing_events import build_success_fee_invoice
from funding_engine.business_readiness_score import calculate_business_readiness_score
from funding_engine.recommendations import generate_recommendations
from funding_engine.referral_rewards import calculate_referral_amount
from funding_engine.relationship_scoring import recommend_relationship_prep, score_relationship

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


def sample_profile() -> dict:
    return {
        "business_registered": True,
        "ein_present": True,
        "business_address_present": True,
        "professional_email_present": True,
        "website_present": True,
        "phone_listed": True,
        "personal_credit_score": 705,
        "high_utilization": False,
        "recent_late_payments": False,
        "low_inquiry_velocity": True,
        "monthly_deposits": 8500,
        "average_balance": 6200,
        "deposit_consistency": "consistent",
        "prior_products": ["business checking"],
        "verification_status": "verified",
        "completed_tier_1_actions": 3,
        "relationship_prep_scheduled": True,
    }


def sample_business_inputs() -> dict:
    return {
        "duns_status": "active",
        "paydex_score": 78,
        "experian_business_score": 74,
        "equifax_business_score": 72,
        "nav_grade": "B",
        "reporting_tradelines_count": 3,
        "business_bank_account_age_months": 7,
        "monthly_deposits": 8500,
        "average_balance": 6200,
        "nsf_count": 0,
        "revenue_consistency": "consistent",
    }


def sample_relationship() -> dict:
    return {
        "institution_name": "Desert Valley CU",
        "account_age_days": 95,
        "average_balance": 6200,
        "monthly_deposits": 8500,
        "deposit_consistency": "consistent",
        "prior_products": ["business checking"],
        "verification_status": "verified",
        "proof_url": "https://example.com/proof.pdf",
    }


def sample_institutions() -> list[dict]:
    return [
        {
            "institution_name": "Desert Valley CU",
            "institution_type": "credit_union",
            "product_types": ["credit_union_business_credit_card", "credit_union_loc"],
            "min_score": 660,
            "business_checking_available": True,
            "business_credit_card_available": True,
            "business_loc_available": True,
            "membership_required": True,
        },
        {
            "institution_name": "Community SBA Partner",
            "institution_type": "sba_lender",
            "product_types": ["sba_microloan", "working_capital_loan"],
            "min_score": 650,
            "business_checking_available": False,
            "sba_available": True,
        },
    ]


def sample_patterns() -> list[dict]:
    return [
        {
            "card_name": "Business Platinum",
            "bank_name": "Desert Valley CU",
            "product_type": "credit_union_business_credit_card",
            "approval_rate": 0.68,
            "sample_size": 21,
            "avg_limit": 12000,
            "max_limit": 25000,
            "confidence_score": 0.72,
        }
    ]


def test_business_readiness_score():
    report = calculate_business_readiness_score(
        profile=sample_profile(),
        business_score_inputs=sample_business_inputs(),
        relationships=[{"relationship_score": 16}],
        execution_history={"reported_results_count": 1, "verified_results_count": 1, "completed_actions_count": 3},
    )
    check("business readiness score is bounded 0-100", 0 <= report["score"] <= 100, f"score={report['score']}")
    check("business readiness score includes six sections", len(report["breakdown"]) == 6, f"breakdown={report['breakdown']}")
    check("business readiness note says internal score", "internal nexus" in report["note"].lower(), report["note"])


def test_relationship_scoring():
    scored = score_relationship(sample_relationship(), {"institution_name": "Desert Valley CU"})
    prep = recommend_relationship_prep(sample_profile(), {"institution_name": "Desert Valley CU", "business_checking_available": True, "membership_required": True})
    check("relationship score is capped at 20", 0 <= scored["relationship_score"] <= 20, f"score={scored['relationship_score']}")
    check("relationship scoring explains no guarantee", "not guarantee" in scored["note"].lower(), scored["note"])
    check("relationship prep mentions 30-90 days", "30-90" in prep["summary"], prep["summary"])


def test_approval_scoring():
    without_rel = score_approval_recommendation(
        product={"tier": 1, "min_score": 660, "product_type": "credit_union_business_credit_card"},
        user_profile=sample_profile(),
        readiness_score=72,
        relationship_score=0,
        approval_patterns=sample_patterns(),
    )
    with_rel = score_approval_recommendation(
        product={"tier": 1, "min_score": 660, "product_type": "credit_union_business_credit_card"},
        user_profile=sample_profile(),
        readiness_score=72,
        relationship_score=16,
        approval_patterns=sample_patterns(),
    )
    check("approval score increases with relationship boost", with_rel["approval_score"] > without_rel["approval_score"], f"without={without_rel['approval_score']} with={with_rel['approval_score']}")
    check("relationship boost is positive when relationship exists", with_rel["relationship_boost"] > 0, f"boost={with_rel['relationship_boost']}")
    check("approval reason includes disclaimer language", "not guaranteed" in with_rel["reason"].lower(), with_rel["reason"])


def test_recommendations():
    tier_1 = generate_recommendations(
        user_profile=sample_profile(),
        readiness_score=74,
        institutions=sample_institutions(),
        approval_patterns=sample_patterns(),
        tier=1,
    )
    tier_2 = generate_recommendations(
        user_profile=sample_profile(),
        readiness_score=74,
        institutions=sample_institutions(),
        approval_patterns=sample_patterns(),
        tier=2,
    )
    tier_1_types = {row["product_type"] for row in tier_1}
    tier_2_types = {row["product_type"] for row in tier_2}
    check("tier 1 includes credit union business cards", "credit_union_business_credit_card" in tier_1_types, f"types={tier_1_types}")
    check("tier 2 excludes credit union business cards", "credit_union_business_credit_card" not in tier_2_types, f"types={tier_2_types}")
    check("tier 2 includes LOC or SBA products", bool({"credit_union_loc", "sba_microloan", "working_capital_loan"} & tier_2_types), f"types={tier_2_types}")
    check("recommendations keep disclaimer", all("not guaranteed" in row["disclaimer"].lower() for row in tier_1[:3] + tier_2[:3]), "missing disclaimer")


def test_billing_and_referrals():
    invoice = build_success_fee_invoice(
        tenant_id="tenant-1",
        user_id="user-1",
        application_result_id="app-1",
        funding_amount=50000,
    )
    referral_amount = calculate_referral_amount(5000, 0.02)
    check("invoice generation uses 10 percent fee", invoice["invoice_amount"] == 5000.0, f"invoice={invoice}")
    check("referral payout uses 2 percent of platform fee", referral_amount == 100.0, f"amount={referral_amount}")


def test_recommendation_refresh_create_update_force_skip_and_hermes():
    original_generate = service.generate_user_recommendations
    original_get_active = service.get_active_recommendations
    original_refresh_fn = service.create_or_refresh_user_recommendations
    original_safe_insert = service.safe_insert
    original_safe_patch = service.safe_patch
    original_log = service._log_recommendation_run
    original_column_supported = service._column_supported

    storage = {"existing": [], "inserted": [], "patched": []}

    def fake_generate_user_recommendations(*, user_id, tenant_id=None, user_profile=None, tier=None):
        snapshot = {
            "user_profile": {"id": user_id, "onboarding_complete": True, "personal_credit_score": 705},
            "business_score_input": sample_business_inputs(),
            "banking_relationships": [sample_relationship()],
            "readiness": {"score": 74},
            "tier_progress": {"current_tier": 1, "tier_2_status": "locked"},
            "relationship_score": 16,
            "missing_inputs": [],
        }
        return {
            "snapshot": snapshot,
            "recommendations": [
                {
                    "tier": 1,
                    "recommendation_type": "funding_product",
                    "institution_name": "Desert Valley CU",
                    "product_name": "Desert Valley CU Credit union business credit card",
                    "product_type": "credit_union_business_credit_card",
                    "approval_score": 88,
                    "approval_score_without_relationship": 79,
                    "relationship_boost": 9,
                    "expected_limit_low": 5000,
                    "expected_limit_high": 12000,
                    "confidence_level": "medium",
                    "reason": "Results vary. Approval is determined by the lender and is not guaranteed.",
                    "prep_steps": ["Keep deposits consistent."],
                    "evidence_summary": {"kind": "test"},
                    "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
                    "status": "recommended",
                }
            ],
        }

    def fake_safe_insert(table, body, **_):
        if table == "funding_recommendations":
            storage["inserted"].append(body)
            row = {"id": f"rec-{len(storage['inserted'])}", **body}
            storage["existing"] = [row]
            return {"ok": True, "rows": [row]}
        if table == "funding_recommendation_runs":
            return {"ok": True, "rows": [{"id": "run-1", **body}]}
        return {"ok": True, "rows": [{"id": "other", **body}]}

    def fake_safe_patch(path, body):
        storage["patched"].append((path, body))
        return {"ok": True, "rows": [{"id": "rec-existing", **body}]}

    service.generate_user_recommendations = fake_generate_user_recommendations
    service.get_active_recommendations = lambda user_id, tenant_id=None: storage["existing"]
    service.safe_insert = fake_safe_insert
    service.safe_patch = fake_safe_patch
    service._log_recommendation_run = lambda **kwargs: {"ok": True, "rows": [kwargs]}
    service._column_supported = lambda table, column: True
    try:
        created = service.create_or_refresh_user_recommendations("user-1", "tenant-1", "manual_admin_refresh", force=False)
        check("recommendation refresh creates recommendations", created["refresh"]["created"] == 1, f"refresh={created['refresh']}")

        updated = service.create_or_refresh_user_recommendations("user-1", "tenant-1", "manual_admin_refresh", force=False)
        check("duplicate active recommendations are updated not duplicated", updated["refresh"]["updated"] == 1 and len(storage["inserted"]) == 1, f"inserted={len(storage['inserted'])} updated={updated['refresh']}")

        forced = service.create_or_refresh_user_recommendations("user-1", "tenant-1", "manual_admin_refresh", force=True)
        check("force refresh works", forced["refresh"]["updated"] == 1, f"refresh={forced['refresh']}")

        service.generate_user_recommendations = lambda **kwargs: {
            "snapshot": {
                "user_profile": {"id": "user-2", "onboarding_complete": False},
                "business_score_input": None,
                "banking_relationships": [],
                "readiness": {"score": 7},
                "tier_progress": {"current_tier": 1, "tier_2_status": "locked"},
                "relationship_score": 0,
                "missing_inputs": ["business score inputs", "banking relationship inputs"],
            },
            "recommendations": [],
        }
        skipped = service.create_or_refresh_user_recommendations("user-2", "tenant-1", "manual_admin_refresh", force=False)
        check("users with missing profile data are skipped safely", skipped["refresh"]["skipped"] is True, f"refresh={skipped['refresh']}")

        triggered = []
        service.get_active_recommendations = lambda user_id, tenant_id=None: []
        service.create_or_refresh_user_recommendations = lambda user_id, tenant_id, reason, force=False: triggered.append((user_id, reason, force)) or {"refresh": {"created": 1, "updated": 0, "skipped": False}}
        service.generate_user_recommendations = fake_generate_user_recommendations
        brief = service.build_hermes_funding_brief("user-3", "tenant-1")
        check("Hermes brief auto-generates if none exist", triggered and triggered[0][1] == "hermes_brief_auto_generate", f"triggered={triggered}")
        check("Hermes brief keeps disclaimer", "not guaranteed" in brief["brief_text"].lower(), brief["brief_text"])
    finally:
        service.generate_user_recommendations = original_generate
        service.get_active_recommendations = original_get_active
        service.create_or_refresh_user_recommendations = original_refresh_fn
        service.safe_insert = original_safe_insert
        service.safe_patch = original_safe_patch
        service._log_recommendation_run = original_log
        service._column_supported = original_column_supported


def test_application_result_submission_triggers_refresh():
    original_safe_insert = billing_events.safe_insert
    original_referral = billing_events.create_referral_earning_if_eligible
    original_refresh = None
    refresh_calls = []
    import funding_engine.service as service_module
    original_refresh = service_module.create_or_refresh_user_recommendations

    def fake_safe_insert(table, body, **_):
        if table == "application_results":
            return {"ok": True, "rows": [{"id": "app-1", **body}]}
        if table == "success_fee_invoices":
            return {"ok": True, "rows": [{"id": "inv-1", **body}]}
        return {"ok": True, "rows": [{"id": "row-1", **body}]}

    billing_events.safe_insert = fake_safe_insert
    billing_events.create_referral_earning_if_eligible = lambda **kwargs: {"earning": None}
    service_module.create_or_refresh_user_recommendations = lambda user_id, tenant_id, reason, force=False: refresh_calls.append((user_id, reason)) or {"refresh": {"created": 1}}
    try:
        result = billing_events.record_application_result(
            tenant_id="tenant-1",
            user_id="user-9",
            recommendation_id="rec-1",
            result_status="approved",
            approved_amount=25000,
            proof_url=None,
            verified=False,
        )
    finally:
        billing_events.safe_insert = original_safe_insert
        billing_events.create_referral_earning_if_eligible = original_referral
        service_module.create_or_refresh_user_recommendations = original_refresh
    check("application result submission triggers refresh", refresh_calls == [("user-9", "application_result_submitted")], f"calls={refresh_calls}")
    check("application result response keeps disclaimer", "not guaranteed" in result["disclaimer"].lower(), result["disclaimer"])


def main() -> int:
    test_business_readiness_score()
    test_relationship_scoring()
    test_approval_scoring()
    test_recommendations()
    test_billing_and_referrals()
    test_recommendation_refresh_create_update_force_skip_and_hermes()
    test_application_result_submission_triggers_refresh()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"{len(failed)} test(s) failed")
        for name in failed:
            print(f" - {name}")
        return 1
    print(f"All {len(_results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
