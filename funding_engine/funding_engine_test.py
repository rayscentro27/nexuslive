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


def test_no_duplicate_invoices_or_referral_earnings():
    original_safe_insert = billing_events.safe_insert
    original_referral = billing_events.create_referral_earning_if_eligible
    import funding_engine.service as service_module
    original_refresh = service_module.create_or_refresh_user_recommendations

    insert_calls: list[str] = []

    def fake_safe_insert(table, body, **_):
        insert_calls.append(table)
        if table == "application_results":
            return {"ok": True, "rows": [{"id": "app-dup-1", **body}]}
        if table == "success_fee_invoices":
            return {"ok": True, "rows": [{"id": "inv-dup-1", **body}]}
        return {"ok": True, "rows": [{"id": "row-x", **body}]}

    # Simulate the duplicate guard: _exists returns True for both tables.
    original_exists = billing_events._exists

    def fake_exists_true(table, filter_qs):
        return True  # both invoice and referral earning already exist

    billing_events.safe_insert = fake_safe_insert
    billing_events._exists = fake_exists_true
    billing_events.create_referral_earning_if_eligible = lambda **kwargs: {"earning": {"id": "ref-1"}}
    service_module.create_or_refresh_user_recommendations = lambda user_id, tenant_id, reason, force=False: {"refresh": {"created": 0}}
    try:
        result = billing_events.record_application_result(
            tenant_id="tenant-1",
            user_id="user-dup",
            recommendation_id=None,
            result_status="approved",
            approved_amount=10000,
        )
    finally:
        billing_events.safe_insert = original_safe_insert
        billing_events._exists = original_exists
        billing_events.create_referral_earning_if_eligible = original_referral
        service_module.create_or_refresh_user_recommendations = original_refresh

    check("duplicate invoice is skipped when guard fires", "success_fee_invoices" not in insert_calls, f"insert_calls={insert_calls}")
    check("invoice_skipped flag set on duplicate", result.get("invoice_skipped") == "duplicate_guard", f"result keys={list(result.keys())}")
    check("duplicate referral earning is skipped when guard fires", result.get("referral_earning_skipped") == "duplicate_guard", f"result={result}")


def test_dismissed_recommendations_not_recreated():
    original_generate = service.generate_user_recommendations
    original_get_active = service.get_active_recommendations
    original_safe_insert = service.safe_insert
    original_safe_patch = service.safe_patch
    original_log = service._log_recommendation_run
    original_column_supported = service._column_supported
    original_safe_select = service._safe_select

    inserted_keys: list[tuple] = []

    dismissed_rec = {
        "tier": 1,
        "recommendation_type": "funding_product",
        "institution_name": "Desert Valley CU",
        "product_name": "Desert Valley CU Credit union business credit card",
        "product_type": "credit_union_business_credit_card",
        "status": "dismissed",
    }

    def fake_safe_select(path: str):
        # Return dismissed rec when querying historical statuses.
        if "status=in.(dismissed,completed,invoiced)" in path:
            return [dismissed_rec]
        return []

    def fake_generate(*, user_id, tenant_id=None, user_profile=None, tier=None):
        return {
            "snapshot": {
                "user_profile": {"id": user_id, "onboarding_complete": True, "personal_credit_score": 700},
                "business_score_input": sample_business_inputs(),
                "banking_relationships": [sample_relationship()],
                "readiness": {"score": 70},
                "tier_progress": {"current_tier": 1, "tier_2_status": "locked"},
                "relationship_score": 10,
                "missing_inputs": [],
            },
            "recommendations": [
                {
                    "tier": 1,
                    "recommendation_type": "funding_product",
                    "institution_name": "Desert Valley CU",
                    "product_name": "Desert Valley CU Credit union business credit card",
                    "product_type": "credit_union_business_credit_card",
                    "approval_score": 80,
                    "approval_score_without_relationship": 72,
                    "relationship_boost": 8,
                    "expected_limit_low": 5000,
                    "expected_limit_high": 10000,
                    "confidence_level": "medium",
                    "reason": "Results vary. Approval is determined by the lender and is not guaranteed.",
                    "prep_steps": [],
                    "evidence_summary": {},
                    "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
                    "status": "recommended",
                }
            ],
        }

    def fake_safe_insert(table, body, **_):
        if table == "funding_recommendations":
            inserted_keys.append(service._recommendation_key(body))
            return {"ok": True, "rows": [{"id": "rec-new", **body}]}
        if table == "funding_recommendation_runs":
            return {"ok": True, "rows": [{"id": "run-1", **body}]}
        return {"ok": True, "rows": [{"id": "other", **body}]}

    service.generate_user_recommendations = fake_generate
    service.get_active_recommendations = lambda user_id, tenant_id=None: []
    service._safe_select = fake_safe_select
    service.safe_insert = fake_safe_insert
    service.safe_patch = lambda path, body: {"ok": True, "rows": []}
    service._log_recommendation_run = lambda **kwargs: {"ok": True, "rows": [kwargs]}
    service._column_supported = lambda table, column: True
    try:
        result = service.create_or_refresh_user_recommendations("user-dm", "tenant-1", "test_dismissed", force=False)
    finally:
        service.generate_user_recommendations = original_generate
        service.get_active_recommendations = original_get_active
        service._safe_select = original_safe_select
        service.safe_insert = original_safe_insert
        service.safe_patch = original_safe_patch
        service._log_recommendation_run = original_log
        service._column_supported = original_column_supported

    check("dismissed recommendation is not re-inserted", len(inserted_keys) == 0, f"inserted_keys={inserted_keys}")
    check("refresh result shows 0 created for dismissed-only run", result["refresh"]["created"] == 0, f"refresh={result['refresh']}")


def test_process_pending_jobs_returns_processed_pairs():
    original_safe_select = service._safe_select
    original_refresh = service.create_or_refresh_user_recommendations
    original_safe_patch = service.safe_patch

    fake_jobs = [
        {"id": "job-1", "user_id": "user-a", "tenant_id": "tenant-1", "reason": "test", "force": False},
        {"id": "job-2", "user_id": "user-b", "tenant_id": None, "reason": "test", "force": False},
    ]

    def fake_safe_select(path: str):
        if "funding_recommendation_jobs" in path:
            return fake_jobs
        return []

    service._safe_select = fake_safe_select
    service.create_or_refresh_user_recommendations = lambda user_id, tenant_id, reason, force=False: {"refresh": {"created": 1, "updated": 0, "skipped": False}}
    service.safe_patch = lambda path, body: {"ok": True, "rows": []}
    try:
        result = service.process_pending_recommendation_jobs(limit=10)
    finally:
        service._safe_select = original_safe_select
        service.create_or_refresh_user_recommendations = original_refresh
        service.safe_patch = original_safe_patch

    pairs = result.get("processed_pairs") or set()
    check("process_pending_jobs returns processed_pairs", isinstance(pairs, set), f"type={type(pairs)}")
    check("processed_pairs contains correct user/tenant tuples", ("tenant-1", "user-a") in pairs and (None, "user-b") in pairs, f"pairs={pairs}")
    check("processed count matches jobs", result["processed"] == 2, f"result={result}")


def test_no_approval_guarantee_language():
    from funding_engine.constants import DISCLAIMER
    lower = DISCLAIMER.lower()
    check("disclaimer does not guarantee approval", "guaranteed" not in lower or "not guaranteed" in lower, DISCLAIMER)
    check("disclaimer mentions lender determines approval", "lender" in lower, DISCLAIMER)

    recs = generate_recommendations(
        user_profile=sample_profile(),
        readiness_score=74,
        institutions=sample_institutions(),
        approval_patterns=sample_patterns(),
    )
    for rec in recs:
        check(
            f"rec '{rec.get('product_name','?')}' disclaimer does not guarantee approval",
            "not guaranteed" in rec.get("disclaimer", "").lower(),
            rec.get("disclaimer", ""),
        )


def sample_recommendations_for_strategy() -> list[dict]:
    return [
        {
            "id": "rec-amex-1",
            "tier": 1,
            "recommendation_type": "funding_product",
            "institution_name": "American Express",
            "product_name": "American Express Business Platinum",
            "product_type": "business_credit_card",
            "approval_score": 78.0,
            "approval_score_without_relationship": 72.0,
            "relationship_boost": 6.0,
            "expected_limit_low": 8000.0,
            "expected_limit_high": 25000.0,
            "confidence_level": "medium",
            "reason": "Internal readiness score: 74.0/100; Relationship strength: 16.0/20. Results vary. Approval is determined by the lender and is not guaranteed.",
            "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
            "status": "recommended",
        },
        {
            "id": "rec-cu-1",
            "tier": 1,
            "recommendation_type": "funding_product",
            "institution_name": "Desert Valley CU",
            "product_name": "Desert Valley CU Credit union business credit card",
            "product_type": "credit_union_business_credit_card",
            "approval_score": 88.0,
            "approval_score_without_relationship": 79.0,
            "relationship_boost": 9.0,
            "expected_limit_low": 5000.0,
            "expected_limit_high": 12000.0,
            "confidence_level": "medium",
            "reason": "Internal readiness score: 74.0/100. Results vary. Approval is determined by the lender and is not guaranteed.",
            "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
            "status": "recommended",
        },
        {
            "id": "rec-sba-1",
            "tier": 2,
            "recommendation_type": "funding_product",
            "institution_name": "Community SBA Partner",
            "product_name": "Community SBA Partner Working Capital Loan",
            "product_type": "working_capital_loan",
            "approval_score": 65.0,
            "approval_score_without_relationship": 60.0,
            "relationship_boost": 5.0,
            "expected_limit_low": 10000.0,
            "expected_limit_high": 50000.0,
            "confidence_level": "low",
            "reason": "Internal readiness score: 74.0/100. Results vary. Approval is determined by the lender and is not guaranteed.",
            "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
            "status": "recommended",
        },
    ]


def sample_relationships_for_strategy() -> list[dict]:
    return [
        {
            "institution_name": "Desert Valley CU",
            "account_age_days": 95,
            "average_balance": 6200,
            "monthly_deposits": 8500,
            "deposit_consistency": "consistent",
            "prior_products": ["business checking"],
            "verification_status": "verified",
            "proof_url": "https://example.com/proof.pdf",
            "relationship_score": 16,
        }
    ]


def sample_readiness_profile() -> dict:
    return {"score": 74.0, "overall_score": 74.0}


def test_strategy_builds_correctly():
    from funding_engine.strategy_engine import build_funding_strategy, STRATEGY_DISCLAIMER

    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=sample_recommendations_for_strategy(),
        relationships=sample_relationships_for_strategy(),
    )

    check("strategy has strategy_summary", bool(strategy.get("strategy_summary")), "missing strategy_summary")
    check("strategy has prequalification_phase", isinstance(strategy.get("prequalification_phase"), dict), "not a dict")
    check("strategy has relationship_building_phase", isinstance(strategy.get("relationship_building_phase"), dict), "not a dict")
    check("strategy has application_sequence", isinstance(strategy.get("application_sequence"), list), "not a list")
    check("strategy has optimization_notes", isinstance(strategy.get("optimization_notes"), dict), "not a dict")
    check("strategy has estimated_funding_low", isinstance(strategy.get("estimated_funding_low"), (int, float)), str(strategy.get("estimated_funding_low")))
    check("strategy has estimated_funding_high", isinstance(strategy.get("estimated_funding_high"), (int, float)), str(strategy.get("estimated_funding_high")))
    check("strategy funding range is non-negative", strategy["estimated_funding_low"] >= 0 and strategy["estimated_funding_high"] >= 0, str((strategy["estimated_funding_low"], strategy["estimated_funding_high"])))
    check("strategy high >= low", strategy["estimated_funding_high"] >= strategy["estimated_funding_low"], str((strategy["estimated_funding_low"], strategy["estimated_funding_high"])))
    check("strategy has next_best_action", isinstance(strategy.get("next_best_action"), dict), "not a dict")
    check("strategy has linked_recommendation_ids", isinstance(strategy.get("linked_recommendation_ids"), list), "not a list")
    check("strategy has disclaimer", bool(strategy.get("disclaimer")), "missing disclaimer")
    check("strategy disclaimer contains not guaranteed", "not guaranteed" in strategy["disclaimer"].lower(), strategy["disclaimer"][:80])
    check("strategy has source_snapshot", isinstance(strategy.get("source_snapshot"), dict), "not a dict")
    check("strategy has generated_at", bool(strategy.get("generated_at")), "missing generated_at")


def test_strategy_handles_missing_data():
    from funding_engine.strategy_engine import build_funding_strategy

    strategy = build_funding_strategy(
        user_profile={},
        readiness_profile={},
        recommendations=[],
        relationships=[],
    )
    check("empty profile produces strategy without error", isinstance(strategy, dict), str(type(strategy)))
    check("empty profile strategy has all required keys",
        all(k in strategy for k in ["strategy_summary", "prequalification_phase", "relationship_building_phase",
                                     "application_sequence", "optimization_notes", "estimated_funding_low",
                                     "estimated_funding_high", "next_best_action", "disclaimer"]),
        str(list(strategy.keys())))
    check("empty profile application_sequence is empty list", strategy["application_sequence"] == [], str(strategy["application_sequence"]))
    check("empty profile next_best_action has readiness phase",
        strategy["next_best_action"].get("phase") == "readiness",
        str(strategy["next_best_action"]))


def test_strategy_relationship_steps_included():
    from funding_engine.strategy_engine import build_funding_strategy

    recs_no_rel = [
        {
            "id": "rec-chase-1",
            "tier": 1,
            "recommendation_type": "funding_product",
            "institution_name": "Chase",
            "product_name": "Chase Ink Business Cash",
            "product_type": "business_credit_card",
            "approval_score": 75.0,
            "approval_score_without_relationship": 70.0,
            "relationship_boost": 5.0,
            "expected_limit_low": 5000.0,
            "expected_limit_high": 20000.0,
            "confidence_level": "medium",
            "reason": "Results vary. Approval is determined by the lender and is not guaranteed.",
            "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
            "status": "recommended",
        }
    ]

    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=recs_no_rel,
        relationships=[],  # No existing relationship with Chase
    )
    rel_actions = (strategy.get("relationship_building_phase") or {}).get("institution_actions") or []
    chase_action = next((a for a in rel_actions if "chase" in str(a.get("institution_name") or "").lower()), None)
    check("missing relationship generates relationship step", chase_action is not None, str([a.get("institution_name") for a in rel_actions]))
    check("relationship step has no_relationship status", chase_action and chase_action.get("status") == "no_relationship", str(chase_action))
    check("relationship step includes deposit recommendation", chase_action and bool(chase_action.get("deposit_recommendation")), str(chase_action))
    check("relationship step includes wait_period", chase_action and bool(chase_action.get("wait_period")), str(chase_action))


def test_strategy_application_sequence_ordering():
    from funding_engine.strategy_engine import build_funding_strategy

    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=sample_recommendations_for_strategy(),
        relationships=sample_relationships_for_strategy(),
    )
    seq = strategy.get("application_sequence") or []
    check("application sequence has at least 2 steps", len(seq) >= 2, f"count={len(seq)}")
    check("application sequence steps are numbered", all(s.get("step") == i + 1 for i, s in enumerate(seq)), str([s.get("step") for s in seq]))

    # Desert Valley CU has an existing relationship — should be sequenced before or early
    institutions = [s.get("institution_name") for s in seq if s.get("tier") == 1]
    check("Tier 1 institutions appear in sequence", len(institutions) > 0, str(institutions))

    # All steps after the first should have wait_before_days >= 14
    check("inquiry spacing applied after first step",
        all(s.get("wait_before_days", 0) >= 14 for s in seq[1:]),
        str([(s.get("institution_name"), s.get("wait_before_days")) for s in seq[1:]]))


def test_strategy_soft_pull_prequal():
    from funding_engine.strategy_engine import build_funding_strategy

    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=sample_recommendations_for_strategy(),
        relationships=sample_relationships_for_strategy(),
    )
    prequal = strategy.get("prequalification_phase") or {}
    opps = prequal.get("opportunities") or []
    amex_opp = next((o for o in opps if "amex" in str(o.get("institution_name") or "").lower() or "american express" in str(o.get("institution_name") or "").lower()), None)
    check("Amex appears in soft-pull opportunities", amex_opp is not None, str([o.get("institution_name") for o in opps]))


def test_strategy_no_guarantee_language():
    from funding_engine.strategy_engine import build_funding_strategy, STRATEGY_DISCLAIMER

    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=sample_recommendations_for_strategy(),
        relationships=sample_relationships_for_strategy(),
    )

    prohibited = [
        "will be approved",
        "will get funded",
        "guarantee approval",
        "guaranteed funding",
        "guarantee credit",
        "promises funding",
    ]
    full_text = " ".join([
        str(strategy.get("strategy_summary") or ""),
        str((strategy.get("next_best_action") or {}).get("action") or ""),
        str((strategy.get("next_best_action") or {}).get("detail") or ""),
    ]).lower()
    for phrase in prohibited:
        check(f"strategy does not contain '{phrase}'", phrase not in full_text, f"Found in strategy text")

    disc = STRATEGY_DISCLAIMER.lower()
    check("STRATEGY_DISCLAIMER contains not guaranteed", "not guaranteed" in disc, STRATEGY_DISCLAIMER[:80])
    check("STRATEGY_DISCLAIMER mentions lender", "lender" in disc, STRATEGY_DISCLAIMER[:80])
    check("STRATEGY_DISCLAIMER is educational only", "educational" in disc, STRATEGY_DISCLAIMER[:80])


def test_strategy_only_one_active_per_user():
    from funding_engine.strategy_engine import persist_funding_strategy, get_active_strategy
    import funding_engine.strategy_engine as strategy_mod

    inserted: list[dict] = []
    patched: list[dict] = []
    archived: list[int] = []

    def fake_safe_insert(table, body, **_):
        if table == "funding_strategies":
            row = {"id": f"strat-{len(inserted)+1}", "strategy_status": "active", **body}
            inserted.append(row)
            return {"ok": True, "rows": [row]}
        return {"ok": True, "rows": [{"id": "row-x"}]}

    def fake_safe_patch(path, body):
        patched.append((path, body))
        return {"ok": True, "rows": [{"id": "strat-1", **body}]}

    def fake_table_exists(table):
        return True

    def fake_archive(*a, **k):
        archived.append(1)

    original_insert = strategy_mod.safe_insert
    original_patch = strategy_mod.safe_patch
    original_table_exists = strategy_mod.table_exists
    original_archive = strategy_mod._archive_old_strategies

    strategy_mod.safe_insert = fake_safe_insert
    strategy_mod.safe_patch = fake_safe_patch
    strategy_mod.table_exists = fake_table_exists
    strategy_mod._archive_old_strategies = fake_archive

    sample_strat = {
        "strategy_summary": "Test strategy",
        "prequalification_phase": {},
        "relationship_building_phase": {},
        "application_sequence": [],
        "optimization_notes": {},
        "estimated_funding_low": 5000.0,
        "estimated_funding_high": 25000.0,
        "next_best_action": {"phase": "application"},
        "linked_recommendation_ids": [],
        "source_snapshot": {},
        "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
        "generated_at": "2026-04-29T20:00:00+00:00",
    }

    try:
        # First persist: no existing — should INSERT
        strategy_mod.get_active_strategy = lambda uid, tid=None: None
        r1 = persist_funding_strategy("user-s1", "tenant-1", sample_strat, force=False)
        check("first strategy persist is created", r1.get("action") == "created", str(r1))
        check("first strategy inserts to DB", len(inserted) == 1, f"inserted={len(inserted)}")

        # Second persist: existing active — should UPDATE (patch)
        strategy_mod.get_active_strategy = lambda uid, tid=None: {"id": "strat-1", "strategy_status": "active"}
        r2 = persist_funding_strategy("user-s1", "tenant-1", sample_strat, force=False)
        check("second persist updates existing strategy", r2.get("action") == "updated", str(r2))
        check("update uses patch not insert", len(inserted) == 1, f"inserted={len(inserted)}")
        check("patch was called for update", len(patched) >= 1, f"patched={len(patched)}")

        # Force=True: should archive old + create new
        strategy_mod.get_active_strategy = lambda uid, tid=None: {"id": "strat-1", "strategy_status": "active"}
        prev_inserted = len(inserted)
        r3 = persist_funding_strategy("user-s1", "tenant-1", sample_strat, force=True)
        check("force persist archives old and creates new", r3.get("action") == "created", str(r3))
        check("force persist calls archive", len(archived) >= 1, f"archived={len(archived)}")
        check("force persist inserts new row", len(inserted) == prev_inserted + 1, f"inserted={len(inserted)}")
    finally:
        strategy_mod.safe_insert = original_insert
        strategy_mod.safe_patch = original_patch
        strategy_mod.table_exists = original_table_exists
        strategy_mod._archive_old_strategies = original_archive
        strategy_mod.get_active_strategy = get_active_strategy


def test_hermes_reads_persisted_strategy():
    from funding_engine.strategy_engine import build_hermes_strategy_brief, STRATEGY_DISCLAIMER

    # Build a mock persisted strategy
    persisted = {
        "strategy_status": "active",
        "strategy_summary": "Funding Strategy Overview:\nStep 1: Check Amex prequal.\nStep 2: Apply for Desert Valley CU card.",
        "next_best_action": {"phase": "prequalification", "action": "Check Amex prequalification.", "priority": "medium"},
        "application_sequence": [
            {"step": 1, "institution_name": "American Express", "product_name": "Amex Business Platinum",
             "tier": 1, "approval_score": 78.0, "expected_limit_low": 8000.0, "expected_limit_high": 25000.0,
             "wait_before_days": 0, "action": "Apply for Amex Business Platinum."},
            {"step": 2, "institution_name": "Desert Valley CU", "product_name": "Desert Valley CU CU card",
             "tier": 1, "approval_score": 88.0, "expected_limit_low": 5000.0, "expected_limit_high": 12000.0,
             "wait_before_days": 14, "action": "Wait 14 days, then apply for Desert Valley CU CU card."},
        ],
        "estimated_funding_low": 13000.0,
        "estimated_funding_high": 37000.0,
        "relationship_building_phase": {"institution_actions": []},
        "optimization_notes": {"notes": ["Keep utilization below 30% before applications."]},
        "disclaimer": STRATEGY_DISCLAIMER,
    }

    brief = build_hermes_strategy_brief("user-h1", "tenant-1", strategy=persisted)
    check("Hermes strategy brief has brief_text", bool(brief.get("brief_text")), "missing brief_text")
    check("Hermes brief contains funding range", "13,000" in brief["brief_text"] or "37,000" in brief["brief_text"], brief["brief_text"][:200])
    check("Hermes brief contains application step", "American Express" in brief["brief_text"] or "Amex" in brief["brief_text"], brief["brief_text"][:200])
    check("Hermes brief contains disclaimer", "not guaranteed" in brief["brief_text"].lower(), brief["brief_text"][-100:])
    check("Hermes brief has next_best_action", isinstance(brief.get("next_best_action"), dict), str(brief.get("next_best_action")))
    check("Hermes brief has estimated_funding_low", brief.get("estimated_funding_low") == 13000.0, str(brief.get("estimated_funding_low")))
    check("Hermes brief has estimated_funding_high", brief.get("estimated_funding_high") == 37000.0, str(brief.get("estimated_funding_high")))
    check("Hermes brief has current_phase", bool(brief.get("current_phase")), str(brief.get("current_phase")))

    # When no strategy exists
    no_strat_brief = build_hermes_strategy_brief("user-none", "tenant-1", strategy=None)
    check("Hermes brief handles missing strategy gracefully", bool(no_strat_brief.get("brief_text")), "empty brief_text")
    check("Hermes brief includes disclaimer even with no strategy", bool(no_strat_brief.get("disclaimer")), "missing disclaimer")


def test_strategy_integrated_into_recommendation_refresh():
    original_generate = service.generate_user_recommendations
    original_get_active = service.get_active_recommendations
    original_safe_insert = service.safe_insert
    original_safe_patch = service.safe_patch
    original_log = service._log_recommendation_run
    original_col = service._column_supported

    import funding_engine.strategy_engine as strategy_mod
    original_bap = strategy_mod.build_and_persist_strategy
    original_table_exists = strategy_mod.table_exists

    strategy_calls: list[dict] = []
    storage: dict = {"existing": [], "inserted": []}

    def fake_generate(**kwargs):
        snap = {
            "user_profile": {"id": "user-int", "onboarding_complete": True, "personal_credit_score": 705},
            "business_score_input": sample_business_inputs(),
            "banking_relationships": [sample_relationship()],
            "readiness": {"score": 74},
            "tier_progress": {"current_tier": 1, "tier_2_status": "locked"},
            "relationship_score": 16,
            "missing_inputs": [],
        }
        return {"snapshot": snap, "recommendations": [
            {
                "tier": 1, "recommendation_type": "funding_product",
                "institution_name": "Desert Valley CU",
                "product_name": "Desert Valley CU Credit union business credit card",
                "product_type": "credit_union_business_credit_card",
                "approval_score": 88, "approval_score_without_relationship": 79,
                "relationship_boost": 9, "expected_limit_low": 5000, "expected_limit_high": 12000,
                "confidence_level": "medium",
                "reason": "Results vary. Approval is determined by the lender and is not guaranteed.",
                "prep_steps": [], "evidence_summary": {},
                "disclaimer": "Results vary. Approval is determined by the lender and is not guaranteed.",
                "status": "recommended",
            }
        ]}

    def fake_bap(user_id, tenant_id, user_profile, readiness_profile, recommendations, relationships, force=False):
        strategy_calls.append({"user_id": user_id, "tenant_id": tenant_id})
        return {"strategy": {}, "persisted": True, "action": "created"}

    service.generate_user_recommendations = fake_generate
    service.get_active_recommendations = lambda *a, **k: storage["existing"]
    service.safe_insert = lambda t, b, **_: (storage["inserted"].append(b) or {"ok": True, "rows": [{"id": "r1", **b}]})
    service.safe_patch = lambda p, b: {"ok": True, "rows": [{"id": "r1", **b}]}
    service._log_recommendation_run = lambda **kw: {"ok": True}
    service._column_supported = lambda t, c: True
    strategy_mod.build_and_persist_strategy = fake_bap
    strategy_mod.table_exists = lambda t: True

    try:
        result = service.create_or_refresh_user_recommendations("user-int", "tenant-1", "test_integration")
    finally:
        service.generate_user_recommendations = original_generate
        service.get_active_recommendations = original_get_active
        service.safe_insert = original_safe_insert
        service.safe_patch = original_safe_patch
        service._log_recommendation_run = original_log
        service._column_supported = original_col
        strategy_mod.build_and_persist_strategy = original_bap
        strategy_mod.table_exists = original_table_exists

    check("recommendation refresh triggers strategy build", len(strategy_calls) == 1, str(strategy_calls))
    check("strategy is included in refresh result", "strategy" in result, str(list(result.keys())))


def test_current_phase_determination():
    from funding_engine.strategy_engine import _determine_current_phase, build_funding_strategy

    # readiness_score < 40 → "readiness"
    phase = _determine_current_phase(35.0, {"institution_actions": []}, {"opportunities": []}, [])
    check("phase=readiness when score<40", phase == "readiness", f"got={phase}")

    # no relationship + score<65 → "relationship_building"
    rel_phase_no_rel = {"institution_actions": [{"status": "no_relationship", "institution_name": "Chase"}]}
    phase = _determine_current_phase(55.0, rel_phase_no_rel, {"opportunities": []}, [])
    check("phase=relationship_building when no_rel and score<65", phase == "relationship_building", f"got={phase}")

    # prequal available → "prequalification"
    prequal_phase = {"opportunities": [{"institution_name": "American Express"}]}
    phase = _determine_current_phase(75.0, {"institution_actions": []}, prequal_phase, [])
    check("phase=prequalification when prequal available", phase == "prequalification", f"got={phase}")

    # app_sequence present, no prequal → "application"
    phase = _determine_current_phase(75.0, {"institution_actions": []}, {"opportunities": []}, [{"step": 1}])
    check("phase=application when sequence exists and no prequal", phase == "application", f"got={phase}")

    # nothing → "optimization"
    phase = _determine_current_phase(80.0, {"institution_actions": []}, {"opportunities": []}, [])
    check("phase=optimization when all else clear", phase == "optimization", f"got={phase}")

    # high score with relationship actions still present → prequal takes precedence
    phase = _determine_current_phase(75.0, rel_phase_no_rel, prequal_phase, [])
    check("prequalification takes precedence over rel_building at high score", phase == "prequalification", f"got={phase}")

    # build_funding_strategy always includes current_phase key
    strategy = build_funding_strategy(
        user_profile=sample_profile(),
        readiness_profile=sample_readiness_profile(),
        recommendations=sample_recommendations_for_strategy(),
        relationships=sample_relationships_for_strategy(),
    )
    check("build_funding_strategy includes current_phase key", "current_phase" in strategy, str(list(strategy.keys())))
    check("current_phase is non-empty string", isinstance(strategy.get("current_phase"), str) and bool(strategy["current_phase"]), str(strategy.get("current_phase")))
    valid_phases = {"readiness", "relationship_building", "prequalification", "application", "optimization"}
    check("current_phase is a valid phase value", strategy["current_phase"] in valid_phases, str(strategy.get("current_phase")))

    # Weak profile → readiness phase
    weak_strategy = build_funding_strategy(
        user_profile={},
        readiness_profile={"score": 10.0},
        recommendations=[],
        relationships=[],
    )
    check("weak profile produces readiness phase", weak_strategy.get("current_phase") == "readiness", str(weak_strategy.get("current_phase")))


def test_hermes_brief_includes_phase_text():
    from funding_engine.strategy_engine import build_hermes_strategy_brief, STRATEGY_DISCLAIMER

    persisted_rel_building = {
        "strategy_status": "active",
        "strategy_summary": "Funding Strategy Overview:",
        "current_phase": "relationship_building",
        "next_best_action": {"phase": "relationship_building", "action": "Open a business account at Chase.", "priority": "high"},
        "application_sequence": [],
        "estimated_funding_low": 5000.0,
        "estimated_funding_high": 20000.0,
        "relationship_building_phase": {"institution_actions": [{"status": "no_relationship", "institution_name": "Chase", "deposit_recommendation": "$2,000–$5,000", "wait_period": "30–60 days"}]},
        "optimization_notes": {"notes": []},
        "disclaimer": STRATEGY_DISCLAIMER,
    }

    brief = build_hermes_strategy_brief("user-phase-1", "tenant-1", strategy=persisted_rel_building)
    check("phase brief has current_phase key", "current_phase" in brief, str(list(brief.keys())))
    check("current_phase value matches persisted", brief["current_phase"] == "relationship_building", str(brief.get("current_phase")))
    check("brief_text contains phase label", "Relationship Building" in brief["brief_text"], brief["brief_text"][:300])
    check("brief_text contains phase explanation", "banking relationship" in brief["brief_text"].lower() or "relationship" in brief["brief_text"].lower(), brief["brief_text"][:300])
    check("hermes brief has phase_label", bool(brief.get("phase_label")), str(brief.get("phase_label")))
    check("hermes brief has phase_note", bool(brief.get("phase_note")), str(brief.get("phase_note")))

    # Prequalification phase
    persisted_prequal = {
        "strategy_status": "active",
        "strategy_summary": "Funding Strategy Overview:",
        "current_phase": "prequalification",
        "next_best_action": {"phase": "prequalification", "action": "Check prequalification at American Express.", "priority": "medium"},
        "application_sequence": [
            {"step": 1, "institution_name": "American Express", "product_name": "Amex Business Platinum",
             "tier": 1, "approval_score": 78.0, "expected_limit_low": 8000.0, "expected_limit_high": 25000.0,
             "wait_before_days": 0, "action": "Apply for Amex Business Platinum."},
        ],
        "estimated_funding_low": 8000.0,
        "estimated_funding_high": 25000.0,
        "relationship_building_phase": {"institution_actions": []},
        "optimization_notes": {"notes": []},
        "disclaimer": STRATEGY_DISCLAIMER,
    }
    brief_pre = build_hermes_strategy_brief("user-phase-2", "tenant-1", strategy=persisted_prequal)
    check("prequal phase brief has current_phase=prequalification", brief_pre["current_phase"] == "prequalification", str(brief_pre.get("current_phase")))
    check("prequal brief_text mentions soft-pull or prequalification", "prequalification" in brief_pre["brief_text"].lower() or "soft-pull" in brief_pre["brief_text"].lower(), brief_pre["brief_text"][:300])


def test_current_phase_persisted_in_strategy():
    from funding_engine.strategy_engine import persist_funding_strategy
    import funding_engine.strategy_engine as strategy_mod

    persisted_payloads: list[dict] = []

    def fake_safe_insert(table, body, **_):
        if table == "funding_strategies":
            persisted_payloads.append(body)
            return {"ok": True, "rows": [{"id": "strat-phase-1", **body}]}
        return {"ok": True, "rows": [{"id": "row-x"}]}

    original_insert = strategy_mod.safe_insert
    original_table_exists = strategy_mod.table_exists
    original_get_active = strategy_mod.get_active_strategy

    strategy_mod.safe_insert = fake_safe_insert
    strategy_mod.table_exists = lambda t: True
    strategy_mod.get_active_strategy = lambda uid, tid=None: None

    sample_strat = {
        "strategy_summary": "Test",
        "prequalification_phase": {},
        "relationship_building_phase": {},
        "application_sequence": [],
        "optimization_notes": {},
        "estimated_funding_low": 5000.0,
        "estimated_funding_high": 25000.0,
        "next_best_action": {"phase": "application"},
        "current_phase": "application",
        "linked_recommendation_ids": [],
        "source_snapshot": {},
        "disclaimer": "Results vary.",
        "generated_at": "2026-04-29T20:00:00+00:00",
    }

    try:
        persist_funding_strategy("user-cp1", "tenant-1", sample_strat)
        check("current_phase is included in persisted payload", len(persisted_payloads) == 1 and "current_phase" in persisted_payloads[0], str(persisted_payloads[0].keys() if persisted_payloads else "no payload"))
        check("persisted current_phase matches strategy value", persisted_payloads[0].get("current_phase") == "application", str(persisted_payloads[0].get("current_phase")))
    finally:
        strategy_mod.safe_insert = original_insert
        strategy_mod.table_exists = original_table_exists
        strategy_mod.get_active_strategy = original_get_active


def main() -> int:
    test_business_readiness_score()
    test_relationship_scoring()
    test_approval_scoring()
    test_recommendations()
    test_billing_and_referrals()
    test_recommendation_refresh_create_update_force_skip_and_hermes()
    test_application_result_submission_triggers_refresh()
    test_no_duplicate_invoices_or_referral_earnings()
    test_dismissed_recommendations_not_recreated()
    test_process_pending_jobs_returns_processed_pairs()
    test_no_approval_guarantee_language()
    test_strategy_builds_correctly()
    test_strategy_handles_missing_data()
    test_strategy_relationship_steps_included()
    test_strategy_application_sequence_ordering()
    test_strategy_soft_pull_prequal()
    test_strategy_no_guarantee_language()
    test_strategy_only_one_active_per_user()
    test_hermes_reads_persisted_strategy()
    test_strategy_integrated_into_recommendation_refresh()
    test_current_phase_determination()
    test_hermes_brief_includes_phase_text()
    test_current_phase_persisted_in_strategy()

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
