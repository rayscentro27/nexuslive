#!/usr/bin/env python3
"""
test_5_synthetic_users.py — 5 Synthetic Profile Validation for Nexus.

Simulates 5 realistic client scenarios and validates the full loop:
  readiness scoring → task generation → funding recommendations
  → strategy generation → Hermes brief

ALL DATA IS SYNTHETIC. No real users, no real DB writes, no emails, no Telegram.
Runs entirely in offline mode — all Supabase calls are patched with in-memory fakes.

Run:
    python3 scripts/test_5_synthetic_users.py
"""
from __future__ import annotations

import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Terminal colours ──────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
PASS   = f"{GREEN}PASS{RESET}"
FAIL   = f"{RED}FAIL{RESET}"
WARN   = f"{YELLOW}WARN{RESET}"

# ── Imports after path fix ────────────────────────────────────────────────────
from readiness_engine.profile_completion import (
    banking_setup_completion, business_foundation_completion,
    credit_profile_completion, grant_eligibility_completion,
    overall_profile_completion, trading_eligibility_completion,
)
from readiness_engine.readiness_scores import (
    calculate_overall_readiness_score, is_grant_ready, is_trading_eligible,
    score_banking_setup, score_business_foundation, score_credit_profile,
    score_grant_eligibility, score_trading_eligibility,
)
from readiness_engine.task_generation import generate_all_tasks, get_next_best_action
from readiness_engine.hermes_readiness_brief import build_readiness_brief_section
from funding_engine.strategy_engine import (
    build_funding_strategy, build_hermes_strategy_brief, STRATEGY_DISCLAIMER,
)
from funding_engine.recommendations import generate_recommendations
from funding_engine.business_readiness_score import calculate_business_readiness_score
from funding_engine.relationship_scoring import score_relationship
from funding_engine.capital_ladder import evaluate_tier_progress
from funding_engine.constants import DISCLAIMER

# ── Synthetic fixed IDs ───────────────────────────────────────────────────────
SYNTHETIC_TENANT = "00000000-0000-0000-0000-000000000001"
SYNTHETIC_IDS = {
    "strong":  "00000000-0000-0000-0000-000000000011",
    "medium":  "00000000-0000-0000-0000-000000000012",
    "weak":    "00000000-0000-0000-0000-000000000013",
    "grant":   "00000000-0000-0000-0000-000000000014",
    "trading": "00000000-0000-0000-0000-000000000015",
}

# ── Shared synthetic institutions + patterns ──────────────────────────────────
SYNTHETIC_INSTITUTIONS = [
    {
        "institution_name": "American Express",
        "institution_type": "bank",
        "product_types": ["business_credit_card"],
        "min_score": 680,
        "business_checking_available": False,
        "business_credit_card_available": True,
        "membership_required": False,
    },
    {
        "institution_name": "Chase",
        "institution_type": "bank",
        "product_types": ["business_credit_card"],
        "min_score": 670,
        "business_checking_available": True,
        "business_credit_card_available": True,
        "membership_required": False,
    },
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
        "min_score": 640,
        "business_checking_available": False,
        "sba_available": True,
    },
]

SYNTHETIC_PATTERNS = [
    {
        "card_name": "Amex Business Platinum",
        "bank_name": "American Express",
        "product_type": "business_credit_card",
        "approval_rate": 0.64,
        "sample_size": 18,
        "avg_limit": 18000,
        "max_limit": 50000,
        "confidence_score": 0.70,
    },
    {
        "card_name": "Chase Ink Business Cash",
        "bank_name": "Chase",
        "product_type": "business_credit_card",
        "approval_rate": 0.61,
        "sample_size": 22,
        "avg_limit": 12000,
        "max_limit": 30000,
        "confidence_score": 0.68,
    },
    {
        "card_name": "Desert Valley Business Card",
        "bank_name": "Desert Valley CU",
        "product_type": "credit_union_business_credit_card",
        "approval_rate": 0.71,
        "sample_size": 15,
        "avg_limit": 9000,
        "max_limit": 20000,
        "confidence_score": 0.72,
    },
]

# ── Synthetic profile definitions ─────────────────────────────────────────────

def _profile_strong() -> dict:
    return {
        "name": "Strong Profile",
        "user_id": SYNTHETIC_IDS["strong"],
        "tenant_id": SYNTHETIC_TENANT,
        "foundation": {
            "legal_business_name": "Apex Ventures LLC",
            "entity_type": "LLC",
            "state_formed": "AZ",
            "ein_status": "active",
            "business_address_status": "active",
            "business_phone_status": "active",
            "business_email_domain_status": "active",
            "website_status": "active",
            "naics_code": "541511",
            "industry": "Technology",
            "time_in_business_months": 36,
            "monthly_revenue": 18000,
            "employee_count": 5,
            "business_bank_account_status": "active",
        },
        "credit": {
            "personal_credit_score_estimate": 735,
            "experian_score": 732,
            "equifax_score": 738,
            "transunion_score": 731,
            "credit_utilization": 0.09,
            "inquiries_count": 1,
            "negative_items_count": 0,
            "age_of_credit_history": 120,
            "credit_report_uploaded": True,
            "credit_report_file_url": "https://example.com/report.pdf",
            "duns_status": "active",
            "paydex_score": 85,
            "business_tradelines_count": 5,
        },
        "banking": {
            "current_business_bank": "Chase",
            "account_age_months": 18,
            "average_balance": 14000,
            "monthly_deposits": 18000,
            "nsf_count": 0,
            "verification_status": "verified",
        },
        "grants": {
            "business_location_state": "AZ",
            "business_location_city": "Phoenix",
            "industry": "Technology",
            "revenue_range": "100k-500k",
            "employee_count": 5,
            "business_stage": "growth",
            "use_of_funds": "expansion",
            "certifications": ["WOSB"],
            "grant_documents_uploaded": True,
        },
        "trading": {
            "capital_reserve": 10000,
            "risk_tolerance": "moderate",
            "education_video_completed": True,
            "disclaimer_accepted": True,
            "paper_trading_completed": True,
            "eligibility_status": "eligible",
        },
        "relationships": [
            {
                "institution_name": "Chase",
                "account_age_days": 540,
                "average_balance": 14000,
                "monthly_deposits": 18000,
                "deposit_consistency": "consistent",
                "prior_products": ["business checking", "savings"],
                "verification_status": "verified",
                "proof_url": "https://example.com/chase.pdf",
                "relationship_score": 19,
            },
            {
                "institution_name": "American Express",
                "account_age_days": 365,
                "average_balance": 0,
                "monthly_deposits": 0,
                "deposit_consistency": "n/a",
                "prior_products": ["personal card"],
                "verification_status": "unverified",
                "relationship_score": 6,
            },
        ],
        "business_score_inputs": {
            "duns_status": "active",
            "paydex_score": 85,
            "experian_business_score": 78,
            "equifax_business_score": 76,
            "reporting_tradelines_count": 5,
            "business_bank_account_age_months": 18,
            "monthly_deposits": 18000,
            "average_balance": 14000,
            "nsf_count": 0,
            "revenue_consistency": "consistent",
        },
        "user_profile_extra": {
            "personal_credit_score": 735,
            "monthly_deposits": 18000,
            "average_balance": 14000,
            "deposit_consistency": "consistent",
            "high_utilization": False,
            "recent_late_payments": False,
            "low_inquiry_velocity": True,
            "business_registered": True,
            "ein_present": True,
            "business_address_present": True,
            "professional_email_present": True,
            "website_present": True,
            "phone_listed": True,
            "prior_products": ["business checking"],
            "verification_status": "verified",
            "onboarding_complete": True,
            "completed_tier_1_actions": 4,
            "relationship_prep_completed": True,
        },
        "expected": {
            "min_readiness_score": 70,
            "has_recommendations": True,
            "strategy_phase_not": ["readiness"],
            "has_prequal": True,
            "funding_range_min": 5000,
            "grant_ready": True,
            "trading_eligible": True,
            "no_pending_trading_tasks": True,
        },
    }


def _profile_medium() -> dict:
    return {
        "name": "Medium Profile",
        "user_id": SYNTHETIC_IDS["medium"],
        "tenant_id": SYNTHETIC_TENANT,
        "foundation": {
            "legal_business_name": "MidPoint Consulting LLC",
            "entity_type": "LLC",
            "state_formed": "TX",
            "ein_status": "active",
            "business_address_status": "active",
            "business_phone_status": "active",
            "business_email_domain_status": "missing",
            "website_status": "missing",
            "naics_code": "541611",
            "industry": "Consulting",
            "time_in_business_months": 14,
            "monthly_revenue": 6000,
            "employee_count": 1,
            "business_bank_account_status": "active",
        },
        "credit": {
            "personal_credit_score_estimate": 692,
            "credit_utilization": 0.33,
            "inquiries_count": 3,
            "negative_items_count": 0,
            "age_of_credit_history": 60,
            "credit_report_uploaded": False,
            "duns_status": "missing",
            "paydex_score": None,
            "business_tradelines_count": 0,
        },
        "banking": {
            "current_business_bank": "Desert Valley CU",
            "account_age_months": 6,
            "average_balance": 3200,
            "monthly_deposits": 5800,
            "nsf_count": 1,
            "verification_status": "unverified",
        },
        "grants": {
            "business_location_state": "TX",
            "industry": "Consulting",
        },
        "trading": {
            "capital_reserve": 1500,
            "risk_tolerance": "moderate",
            "education_video_completed": False,
            "disclaimer_accepted": False,
            "paper_trading_completed": False,
        },
        "relationships": [
            {
                "institution_name": "Desert Valley CU",
                "account_age_days": 180,
                "average_balance": 3200,
                "monthly_deposits": 5800,
                "deposit_consistency": "irregular",
                "prior_products": ["business checking"],
                "verification_status": "unverified",
                "relationship_score": 8,
            }
        ],
        "business_score_inputs": {
            "duns_status": "missing",
            "business_bank_account_age_months": 6,
            "monthly_deposits": 5800,
            "average_balance": 3200,
            "nsf_count": 1,
            "revenue_consistency": "irregular",
        },
        "user_profile_extra": {
            "personal_credit_score": 692,
            "monthly_deposits": 5800,
            "average_balance": 3200,
            "deposit_consistency": "irregular",
            "high_utilization": True,
            "recent_late_payments": False,
            "business_registered": True,
            "ein_present": True,
            "business_address_present": True,
            "professional_email_present": False,
            "website_present": False,
            "phone_listed": True,
            "prior_products": ["business checking"],
            "verification_status": "unverified",
            "onboarding_complete": True,
            "completed_tier_1_actions": 1,
        },
        "expected": {
            "has_tasks": True,
            "has_credit_report_upload_task": True,
            "has_duns_task": True,
            "has_relationship_building": True,
            "has_recommendations": True,
            "trading_eligible": False,
        },
    }


def _profile_weak() -> dict:
    return {
        "name": "Weak Profile",
        "user_id": SYNTHETIC_IDS["weak"],
        "tenant_id": SYNTHETIC_TENANT,
        "foundation": {
            "legal_business_name": "",
            "entity_type": "sole_proprietor",
            "ein_status": "missing",
            "business_address_status": "missing",
            "business_phone_status": "missing",
            "business_email_domain_status": "missing",
            "website_status": "missing",
            "business_bank_account_status": "missing",
        },
        "credit": {
            "personal_credit_score_estimate": 588,
            "credit_utilization": 0.58,
            "inquiries_count": 7,
            "negative_items_count": 3,
            "credit_report_uploaded": False,
            "duns_status": "missing",
        },
        "banking": {},
        "grants": {},
        "trading": {
            "education_video_completed": False,
            "disclaimer_accepted": False,
            "paper_trading_completed": False,
        },
        "relationships": [],
        "business_score_inputs": {},
        "user_profile_extra": {
            "personal_credit_score": 588,
            "high_utilization": True,
            "recent_late_payments": True,
            "business_registered": False,
            "ein_present": False,
            "business_address_present": False,
            "professional_email_present": False,
            "website_present": False,
            "phone_listed": False,
            "onboarding_complete": False,
            "completed_tier_1_actions": 0,
        },
        "expected": {
            "max_readiness_score": 35,
            "next_best_action_phase": "readiness",
            "has_high_priority_tasks": True,
            "has_llc_task": True,
            "has_ein_task": True,
            "no_high_confidence_recs": True,
            "trading_eligible": False,
            "grant_ready": False,
        },
    }


def _profile_grant() -> dict:
    return {
        "name": "Grant-Oriented Profile",
        "user_id": SYNTHETIC_IDS["grant"],
        "tenant_id": SYNTHETIC_TENANT,
        "foundation": {
            "legal_business_name": "Green Path Community LLC",
            "entity_type": "LLC",
            "state_formed": "GA",
            "ein_status": "active",
            "business_address_status": "active",
            "business_phone_status": "active",
            "business_email_domain_status": "active",
            "website_status": "active",
            "naics_code": "813319",
            "industry": "Non-Profit / Community Services",
            "time_in_business_months": 20,
            "monthly_revenue": 3500,
            "employee_count": 2,
            "business_bank_account_status": "active",
        },
        "credit": {
            "personal_credit_score_estimate": 662,
            "credit_utilization": 0.28,
            "inquiries_count": 2,
            "negative_items_count": 1,
            "credit_report_uploaded": True,
            "duns_status": "active",
            "paydex_score": 72,
        },
        "banking": {
            "current_business_bank": "Local Community Bank",
            "account_age_months": 20,
            "average_balance": 4200,
            "monthly_deposits": 4000,
            "nsf_count": 0,
            "verification_status": "verified",
        },
        "grants": {
            "business_location_state": "GA",
            "business_location_city": "Atlanta",
            "industry": "Non-Profit / Community Services",
            "revenue_range": "0-50k",
            "employee_count": 2,
            "business_stage": "startup",
            "use_of_funds": "operations",
            "certifications": ["WBE", "MBE"],
            # optional_eligibility_tags are user-provided and optional
            "optional_eligibility_tags": [],
            "grant_documents_uploaded": True,
            "notes": "Actively seeking community development grants.",
        },
        "trading": {
            "capital_reserve": 200,
            "education_video_completed": False,
            "disclaimer_accepted": False,
            "paper_trading_completed": False,
        },
        "relationships": [
            {
                "institution_name": "Local Community Bank",
                "account_age_days": 600,
                "average_balance": 4200,
                "monthly_deposits": 4000,
                "deposit_consistency": "consistent",
                "verification_status": "verified",
                "relationship_score": 12,
            }
        ],
        "business_score_inputs": {
            "duns_status": "active",
            "paydex_score": 72,
            "business_bank_account_age_months": 20,
            "monthly_deposits": 4000,
            "average_balance": 4200,
            "nsf_count": 0,
            "revenue_consistency": "consistent",
        },
        "user_profile_extra": {
            "personal_credit_score": 662,
            "monthly_deposits": 4000,
            "average_balance": 4200,
            "deposit_consistency": "consistent",
            "high_utilization": False,
            "business_registered": True,
            "ein_present": True,
            "business_address_present": True,
            "professional_email_present": True,
            "website_present": True,
            "onboarding_complete": True,
            "completed_tier_1_actions": 2,
        },
        "expected": {
            "grant_ready": True,
            "trading_eligible": False,
            "has_trading_tasks": True,
            "strategy_cautious": True,  # funding strategy should not push apps hard
        },
    }


def _profile_trading_locked() -> dict:
    return {
        "name": "Trading-Locked Profile",
        "user_id": SYNTHETIC_IDS["trading"],
        "tenant_id": SYNTHETIC_TENANT,
        "foundation": {
            "legal_business_name": "CapStack Holdings LLC",
            "entity_type": "LLC",
            "state_formed": "NV",
            "ein_status": "active",
            "business_address_status": "active",
            "business_phone_status": "active",
            "business_email_domain_status": "active",
            "website_status": "active",
            "naics_code": "523130",
            "industry": "Finance / Investment",
            "time_in_business_months": 28,
            "monthly_revenue": 11000,
            "employee_count": 2,
            "business_bank_account_status": "active",
        },
        "credit": {
            "personal_credit_score_estimate": 722,
            "credit_utilization": 0.14,
            "inquiries_count": 2,
            "negative_items_count": 0,
            "age_of_credit_history": 96,
            "credit_report_uploaded": True,
            "duns_status": "active",
            "paydex_score": 80,
        },
        "banking": {
            "current_business_bank": "Desert Valley CU",
            "account_age_months": 15,
            "average_balance": 9500,
            "monthly_deposits": 10500,
            "nsf_count": 0,
            "verification_status": "verified",
        },
        "grants": {
            "business_location_state": "NV",
            "industry": "Finance / Investment",
            "revenue_range": "100k-500k",
        },
        "trading": {
            "capital_reserve": 8000,
            "risk_tolerance": "aggressive",
            "education_video_completed": False,  # NOT completed
            "disclaimer_accepted": False,          # NOT accepted
            "paper_trading_completed": False,      # NOT completed
            "eligibility_status": "locked",
        },
        "relationships": [
            {
                "institution_name": "Desert Valley CU",
                "account_age_days": 450,
                "average_balance": 9500,
                "monthly_deposits": 10500,
                "deposit_consistency": "consistent",
                "prior_products": ["business checking"],
                "verification_status": "verified",
                "relationship_score": 17,
            }
        ],
        "business_score_inputs": {
            "duns_status": "active",
            "paydex_score": 80,
            "business_bank_account_age_months": 15,
            "monthly_deposits": 10500,
            "average_balance": 9500,
            "nsf_count": 0,
            "revenue_consistency": "consistent",
        },
        "user_profile_extra": {
            "personal_credit_score": 722,
            "monthly_deposits": 10500,
            "average_balance": 9500,
            "deposit_consistency": "consistent",
            "high_utilization": False,
            "business_registered": True,
            "ein_present": True,
            "business_address_present": True,
            "professional_email_present": True,
            "website_present": True,
            "phone_listed": True,
            "prior_products": ["business checking"],
            "verification_status": "verified",
            "onboarding_complete": True,
            "completed_tier_1_actions": 3,
            "relationship_prep_scheduled": True,
        },
        "expected": {
            "trading_eligible": False,
            "has_trading_tasks": True,
            "has_disclaimer_task": True,
            "min_readiness_score": 65,  # non-trading readiness is good
            "has_recommendations": True,
        },
    }


# ── In-memory store ───────────────────────────────────────────────────────────

class _Store:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}
        self.strategies: dict[str, dict] = {}

    def insert(self, table: str, body: dict) -> dict:
        row = {"id": str(uuid.uuid4()), **body}
        self.rows.setdefault(table, []).append(row)
        return {"ok": True, "rows": [row]}

    def patch(self, path: str, body: dict) -> dict:
        table = path.split("?")[0]
        rows = self.rows.get(table, [])
        for row in rows:
            row.update(body)
        return {"ok": True, "rows": rows[:1]}

    def select(self, table: str) -> list[dict]:
        return list(self.rows.get(table, []))


# ── Context manager: install per-profile patches ─────────────────────────────

@contextmanager
def _synthetic_context(profile: dict, store: _Store):
    """
    Patches all DB-touching functions to use the synthetic profile data
    and an in-memory store. Restores originals on exit.
    """
    import readiness_engine.service as rsvc
    import funding_engine.service as fsvc
    import funding_engine.strategy_engine as strat
    import lib.growth_support as gs

    foundation = profile["foundation"]
    credit     = profile["credit"]
    banking    = profile["banking"]
    grants     = profile["grants"]
    trading    = profile["trading"]
    rels       = profile["relationships"]
    biz_inputs = profile["business_score_inputs"]
    uprofile   = {**profile["user_profile_extra"], "id": profile["user_id"]}

    # ── Stash originals ───
    orig = {
        "rsvc_foundation":  rsvc.get_business_foundation,
        "rsvc_credit":      rsvc.get_credit_profile,
        "rsvc_banking":     rsvc.get_banking_profile,
        "rsvc_grant":       rsvc.get_grant_profile,
        "rsvc_trading":     rsvc.get_trading_profile,
        "rsvc_readiness":   rsvc.get_readiness_profile,
        "rsvc_upsert":      rsvc._upsert_readiness_profile,
        "rsvc_tasks":       rsvc._persist_tasks,
        "rsvc_trigger_f":   rsvc._trigger_funding_refresh,
        "rsvc_trigger_r":   rsvc._trigger_relationship_refresh,
        "fsvc_profile":     fsvc.get_user_profile,
        "fsvc_biz":         fsvc.get_user_business_score_input,
        "fsvc_rels":        fsvc.get_banking_relationships,
        "fsvc_tier":        fsvc.get_user_tier_progress,
        "fsvc_institutions":fsvc.get_lending_institutions,
        "fsvc_patterns":    fsvc.get_approval_patterns,
        "fsvc_active_recs": fsvc.get_active_recommendations,
        "fsvc_safe_insert": fsvc.safe_insert,
        "fsvc_safe_patch":  fsvc.safe_patch,
        "fsvc_safe_select": fsvc._safe_select,
        "fsvc_log":         fsvc._log_recommendation_run,
        "fsvc_col":         fsvc._column_supported,
        "strat_get":        strat.get_active_strategy,
        "strat_table":      strat.table_exists,
        "strat_insert":     strat.safe_insert,
        "strat_patch":      strat.safe_patch,
        "strat_archive":    strat._archive_old_strategies,
        "gs_insert":        gs.safe_insert,
        "gs_patch":         gs.safe_patch,
    }

    # ── Install fakes ───
    rsvc.get_business_foundation  = lambda *a, **k: dict(foundation)
    rsvc.get_credit_profile       = lambda *a, **k: dict(credit)
    rsvc.get_banking_profile      = lambda *a, **k: dict(banking) if banking else None
    rsvc.get_grant_profile        = lambda *a, **k: dict(grants) if grants else None
    rsvc.get_trading_profile      = lambda *a, **k: dict(trading) if trading else None
    rsvc.get_readiness_profile    = lambda *a, **k: None
    rsvc._upsert_readiness_profile = lambda *a, **k: store.insert("client_readiness_profiles", {"user_id": profile["user_id"]})
    rsvc._persist_tasks           = lambda uid, tid, tasks: store.insert("readiness_tasks", {"count": len(tasks), "user_id": uid}) or {"ok": True, "saved": len(tasks)}
    rsvc._trigger_funding_refresh = lambda *a, **k: None
    rsvc._trigger_relationship_refresh = lambda *a, **k: None

    fsvc.get_user_profile              = lambda *a, **k: dict(uprofile)
    fsvc.get_user_business_score_input = lambda *a, **k: dict(biz_inputs) if biz_inputs else None
    fsvc.get_banking_relationships     = lambda *a, **k: [dict(r) for r in rels]
    fsvc.get_user_tier_progress        = lambda *a, **k: {}
    fsvc.get_lending_institutions      = lambda *a, **k: SYNTHETIC_INSTITUTIONS
    fsvc.get_approval_patterns         = lambda *a, **k: SYNTHETIC_PATTERNS
    fsvc.get_active_recommendations    = lambda *a, **k: store.select("funding_recommendations")

    def fake_fsvc_insert(table, body, **_):
        return store.insert(table, body)

    def fake_fsvc_patch(path, body):
        return store.patch(path, body)

    def fake_safe_select(path):
        if "funding_recommendations" in path and "dismissed" in path:
            return []
        if "funding_recommendations" in path:
            return store.select("funding_recommendations")
        if "funding_recommendation_jobs" in path:
            return []
        return []

    fsvc.safe_insert          = fake_fsvc_insert
    fsvc.safe_patch           = fake_fsvc_patch
    fsvc._safe_select         = fake_safe_select
    fsvc._log_recommendation_run = lambda **kw: {"ok": True}
    fsvc._column_supported    = lambda t, c: True

    strat_store: dict[str, dict] = {}

    def fake_strat_insert(table, body, **_):
        row = {"id": str(uuid.uuid4()), "strategy_status": "active", **body}
        strat_store[profile["user_id"]] = row
        return {"ok": True, "rows": [row]}

    def fake_strat_patch(path, body):
        uid = profile["user_id"]
        if uid in strat_store:
            strat_store[uid].update(body)
        return {"ok": True, "rows": [strat_store.get(uid, {})]}

    strat.get_active_strategy  = lambda uid, tid=None: strat_store.get(uid)
    strat.table_exists         = lambda t: True
    strat.safe_insert          = fake_strat_insert
    strat.safe_patch           = fake_strat_patch
    strat._archive_old_strategies = lambda *a, **k: None

    gs.safe_insert = fake_fsvc_insert
    gs.safe_patch  = fake_fsvc_patch

    try:
        yield strat_store
    finally:
        rsvc.get_business_foundation       = orig["rsvc_foundation"]
        rsvc.get_credit_profile            = orig["rsvc_credit"]
        rsvc.get_banking_profile           = orig["rsvc_banking"]
        rsvc.get_grant_profile             = orig["rsvc_grant"]
        rsvc.get_trading_profile           = orig["rsvc_trading"]
        rsvc.get_readiness_profile         = orig["rsvc_readiness"]
        rsvc._upsert_readiness_profile     = orig["rsvc_upsert"]
        rsvc._persist_tasks                = orig["rsvc_tasks"]
        rsvc._trigger_funding_refresh      = orig["rsvc_trigger_f"]
        rsvc._trigger_relationship_refresh = orig["rsvc_trigger_r"]
        fsvc.get_user_profile              = orig["fsvc_profile"]
        fsvc.get_user_business_score_input = orig["fsvc_biz"]
        fsvc.get_banking_relationships     = orig["fsvc_rels"]
        fsvc.get_user_tier_progress        = orig["fsvc_tier"]
        fsvc.get_lending_institutions      = orig["fsvc_institutions"]
        fsvc.get_approval_patterns         = orig["fsvc_patterns"]
        fsvc.get_active_recommendations    = orig["fsvc_active_recs"]
        fsvc.safe_insert                   = orig["fsvc_safe_insert"]
        fsvc.safe_patch                    = orig["fsvc_safe_patch"]
        fsvc._safe_select                  = orig["fsvc_safe_select"]
        fsvc._log_recommendation_run       = orig["fsvc_log"]
        fsvc._column_supported             = orig["fsvc_col"]
        strat.get_active_strategy          = orig["strat_get"]
        strat.table_exists                 = orig["strat_table"]
        strat.safe_insert                  = orig["strat_insert"]
        strat.safe_patch                   = orig["strat_patch"]
        strat._archive_old_strategies      = orig["strat_archive"]
        gs.safe_insert                     = orig["gs_insert"]
        gs.safe_patch                      = orig["gs_patch"]


# ── Per-profile runner ────────────────────────────────────────────────────────

def _run_profile(profile: dict) -> dict:
    """
    Run the full loop for one synthetic profile and collect results.
    Returns a result dict with all computed values and check outcomes.
    """
    import readiness_engine.service as rsvc
    import funding_engine.service as fsvc
    import funding_engine.strategy_engine as strat

    store = _Store()
    errors: list[str] = []
    checks: list[tuple[str, bool]] = []

    def check(label: str, condition: bool, note: str = "") -> None:
        checks.append((label, condition))
        if not condition:
            errors.append(f"{label}" + (f" ({note})" if note else ""))

    uid = profile["user_id"]
    tid = profile["tenant_id"]

    with _synthetic_context(profile, store) as strat_store:

        # ── Step 1: Readiness snapshot ────────────────────────────────────
        try:
            readiness_snap = rsvc.build_readiness_snapshot(uid, tid)
        except Exception as exc:
            errors.append(f"build_readiness_snapshot failed: {exc}")
            return {"profile": profile["name"], "errors": errors, "checks": checks, "passed": False}

        readiness_score = readiness_snap.get("overall_score", 0)
        tasks = readiness_snap.get("tasks") or []
        pending_tasks = [t for t in tasks if t.get("status") == "pending"]
        high_tasks = [t for t in pending_tasks if t.get("priority") == "high"]
        task_types = [t.get("task_type") for t in pending_tasks]
        next_readiness_action = readiness_snap.get("next_best_action") or {}
        grant_ready = readiness_snap.get("grant_ready", False)
        trading_eligible = readiness_snap.get("trading_eligible", False)

        # ── Step 2: Funding recommendations ──────────────────────────────
        try:
            rec_data = fsvc.generate_user_recommendations(user_id=uid, tenant_id=tid)
            recommendations = rec_data.get("recommendations") or []
        except Exception as exc:
            errors.append(f"generate_user_recommendations failed: {exc}")
            recommendations = []

        rec_count = len([r for r in recommendations if r.get("recommendation_type") == "funding_product"])
        high_conf_recs = [
            r for r in recommendations
            if r.get("confidence_level") in {"high", "medium"} and r.get("approval_score", 0) >= 60
        ]

        # Persist to in-memory store to simulate create_or_refresh flow
        funding_snap = rec_data.get("snapshot") or {}

        # ── Step 3: Strategy generation ───────────────────────────────────
        try:
            strategy = build_funding_strategy(
                user_profile=funding_snap.get("user_profile") or profile["user_profile_extra"],
                readiness_profile=funding_snap.get("readiness") or {"score": readiness_score},
                recommendations=recommendations,
                relationships=profile["relationships"],
            )
            strat_result = strat.persist_funding_strategy(uid, tid, strategy, force=False)
            strategy_persisted = strat_result.get("ok", False)
        except Exception as exc:
            errors.append(f"build_funding_strategy failed: {exc}")
            strategy = {}
            strategy_persisted = False

        next_action = strategy.get("next_best_action") or {}
        strategy_phase = next_action.get("phase", "unknown")
        app_seq = strategy.get("application_sequence") or []
        prequal_opps = (strategy.get("prequalification_phase") or {}).get("opportunities") or []
        rel_actions = (strategy.get("relationship_building_phase") or {}).get("institution_actions") or []
        est_low = strategy.get("estimated_funding_low", 0)
        est_high = strategy.get("estimated_funding_high", 0)

        # ── Step 4: Hermes readiness brief ────────────────────────────────
        try:
            readiness_brief = build_readiness_brief_section(readiness_snap)
        except Exception as exc:
            errors.append(f"build_readiness_brief_section failed: {exc}")
            readiness_brief = {}

        # ── Step 5: Hermes strategy brief ─────────────────────────────────
        try:
            persisted_strat = strat.get_active_strategy(uid, tid)
            strategy_brief = build_hermes_strategy_brief(uid, tid, strategy=persisted_strat)
        except Exception as exc:
            errors.append(f"build_hermes_strategy_brief failed: {exc}")
            strategy_brief = {}

        brief_text = strategy_brief.get("brief_text") or readiness_brief.get("brief_text") or ""

        # ── Duplicate active recommendations check ────────────────────────
        rec_keys: dict[tuple, int] = {}
        for r in recommendations:
            key = (r.get("tier"), r.get("recommendation_type"), (r.get("institution_name") or "").lower(), (r.get("product_type") or "").lower())
            rec_keys[key] = rec_keys.get(key, 0) + 1
        has_dup_recs = any(v > 1 for v in rec_keys.values())

        # ── Universal checks (all profiles) ──────────────────────────────
        check("readiness snapshot returned", bool(readiness_snap))
        check("readiness score is 0-100", 0 <= readiness_score <= 100, f"score={readiness_score}")
        check("strategy returned dict", isinstance(strategy, dict))
        check("strategy has disclaimer", "not guaranteed" in (strategy.get("disclaimer") or "").lower())
        check("strategy has next_best_action", isinstance(next_action, dict))
        check("Hermes brief has brief_text", bool(brief_text))
        check("Hermes brief contains disclaimer", STRATEGY_DISCLAIMER[:40].lower() in brief_text.lower() or "not guaranteed" in brief_text.lower())
        check("no duplicate active recommendations", not has_dup_recs, f"duplicates={[k for k,v in rec_keys.items() if v>1]}")
        check("no approval guarantee language in strategy",
            not any(p in (strategy.get("strategy_summary") or "").lower()
                    for p in ["will be approved", "guarantee approval", "guaranteed funding"]))
        check("no approval guarantee language in brief",
            "not guaranteed" in brief_text.lower() or "results vary" in brief_text.lower())

        # ── Profile-specific checks ───────────────────────────────────────
        exp = profile.get("expected") or {}

        if "min_readiness_score" in exp:
            check(f"readiness score >= {exp['min_readiness_score']}",
                readiness_score >= exp["min_readiness_score"], f"actual={readiness_score:.1f}")

        if "max_readiness_score" in exp:
            check(f"readiness score <= {exp['max_readiness_score']}",
                readiness_score <= exp["max_readiness_score"], f"actual={readiness_score:.1f}")

        if exp.get("has_recommendations"):
            check("funding recommendations generated", rec_count > 0, f"count={rec_count}")

        if exp.get("has_tasks"):
            check("readiness tasks generated", len(pending_tasks) > 0, f"count={len(pending_tasks)}")

        if exp.get("has_high_priority_tasks"):
            check("high-priority tasks present", len(high_tasks) > 0, f"high={len(high_tasks)}")

        if exp.get("has_credit_report_upload_task"):
            check("credit_report_upload task generated",
                "credit_report_upload" in task_types, f"types={task_types}")

        if exp.get("has_duns_task"):
            check("duns_setup task generated",
                "duns_setup" in task_types, f"types={task_types}")

        if exp.get("has_llc_task"):
            check("llc_formation task generated",
                "llc_formation" in task_types, f"types={task_types}")

        if exp.get("has_ein_task"):
            check("ein_setup task generated",
                "ein_setup" in task_types, f"types={task_types}")

        if exp.get("has_prequal"):
            check("prequal opportunities identified", len(prequal_opps) > 0, f"count={len(prequal_opps)}")

        if exp.get("has_relationship_building"):
            check("relationship-building phase has actions", len(rel_actions) > 0, f"count={len(rel_actions)}")

        if "next_best_action_phase" in exp:
            check(f"next best action phase == {exp['next_best_action_phase']}",
                strategy_phase == exp["next_best_action_phase"],
                f"actual={strategy_phase}")

        if exp.get("strategy_phase_not"):
            for forbidden_phase in exp["strategy_phase_not"]:
                check(f"strategy phase is not '{forbidden_phase}'",
                    strategy_phase != forbidden_phase, f"actual={strategy_phase}")

        if "funding_range_min" in exp:
            check(f"estimated funding range > ${exp['funding_range_min']:,}",
                est_high > exp["funding_range_min"], f"high={est_high}")

        if "grant_ready" in exp:
            check(f"grant_ready == {exp['grant_ready']}",
                grant_ready == exp["grant_ready"], f"actual={grant_ready}")

        if "trading_eligible" in exp:
            check(f"trading_eligible == {exp['trading_eligible']}",
                trading_eligible == exp["trading_eligible"], f"actual={trading_eligible}")

        if exp.get("has_trading_tasks"):
            trading_task_types = {"trading_disclaimer", "paper_trading_setup"}
            check("trading tasks generated",
                bool(trading_task_types & set(task_types)), f"types={task_types}")

        if exp.get("has_disclaimer_task"):
            check("trading_disclaimer task generated",
                "trading_disclaimer" in task_types, f"types={task_types}")

        if exp.get("no_pending_trading_tasks"):
            trading_pending = [t for t in pending_tasks if t.get("category") == "trading_eligibility"]
            check("no pending trading tasks (complete)", len(trading_pending) == 0, f"count={len(trading_pending)}")

        if exp.get("no_high_confidence_recs"):
            check("no high-confidence recommendations for weak profile",
                len(high_conf_recs) == 0, f"found={len(high_conf_recs)}")

        if exp.get("strategy_cautious"):
            check("strategy phase does not push immediate applications",
                strategy_phase in {"readiness", "relationship_building", "prequalification"},
                f"actual={strategy_phase}")

    passed = len(errors) == 0
    return {
        "profile": profile["name"],
        "user_id": profile["user_id"],
        "readiness_score": readiness_score,
        "rec_count": rec_count,
        "task_count": len(pending_tasks),
        "strategy_phase": strategy_phase,
        "next_best_action": next_action.get("action", "")[:60],
        "est_funding_low": est_low,
        "est_funding_high": est_high,
        "grant_ready": grant_ready,
        "trading_eligible": trading_eligible,
        "app_seq_count": len(app_seq),
        "checks": checks,
        "errors": errors,
        "passed": passed,
    }


# ── Results table ─────────────────────────────────────────────────────────────

def _print_table(results: list[dict]) -> None:
    print(f"\n{BOLD}{'─' * 90}{RESET}")
    print(f"{BOLD}  NEXUS — 5 SYNTHETIC PROFILE VALIDATION RESULTS{RESET}")
    print(f"{BOLD}{'─' * 90}{RESET}")
    header = f"  {'Profile':<28}  {'Score':>5}  {'Recs':>4}  {'Tasks':>5}  {'Phase':<18}  {'Result':>6}"
    print(f"{BOLD}{header}{RESET}")
    print("  " + "─" * 86)
    for r in results:
        result_str = f"{GREEN}PASS{RESET}" if r["passed"] else f"{RED}FAIL{RESET}"
        phase = (r.get("strategy_phase") or "")[:18]
        print(f"  {r['profile']:<28}  {r['readiness_score']:>5.1f}  {r['rec_count']:>4}  "
              f"{r['task_count']:>5}  {phase:<18}  {result_str}")

    print(f"\n{BOLD}  Detail — Next Best Actions{RESET}")
    print("  " + "─" * 86)
    for r in results:
        print(f"  {r['profile']:<28}  {r['next_best_action']}")

    print(f"\n{BOLD}  Detail — Funding Estimates{RESET}")
    print("  " + "─" * 86)
    for r in results:
        low = r.get("est_funding_low", 0)
        high = r.get("est_funding_high", 0)
        grant = "YES" if r.get("grant_ready") else "no"
        trade = "YES" if r.get("trading_eligible") else "locked"
        print(f"  {r['profile']:<28}  ${low:>9,.0f} – ${high:>9,.0f}  |  grant={grant}  trading={trade}")

    print(f"\n{BOLD}  Check Detail{RESET}")
    print("  " + "─" * 86)
    total_checks = 0
    total_passed = 0
    for r in results:
        failed_checks = [(label, ok) for label, ok in r["checks"] if not ok]
        status = f"{GREEN}ALL PASS{RESET}" if not failed_checks else f"{RED}{len(failed_checks)} FAIL{RESET}"
        total_checks += len(r["checks"])
        total_passed += sum(1 for _, ok in r["checks"] if ok)
        print(f"\n  {BOLD}{r['profile']}{RESET}  [{status}]")
        if failed_checks:
            for label, _ in failed_checks:
                print(f"    {RED}✗{RESET} {label}")
        if r.get("errors"):
            for err in r["errors"]:
                print(f"    {YELLOW}⚠{RESET}  {err}")
        if not failed_checks and not r.get("errors"):
            print(f"    {GREEN}✓{RESET} All {len(r['checks'])} checks passed")

    print(f"\n{BOLD}{'─' * 90}{RESET}")
    all_pass = all(r["passed"] for r in results)
    summary_color = GREEN if all_pass else RED
    print(f"  {BOLD}Summary: {total_passed}/{total_checks} checks passed across 5 profiles{RESET}")
    print(f"  {summary_color}{BOLD}{'ALL PROFILES PASSED' if all_pass else 'SOME PROFILES FAILED'}{RESET}")
    print(f"{BOLD}{'─' * 90}{RESET}\n")
    print(f"  {YELLOW}Note: All data is synthetic. No real users, Supabase writes, emails, or Telegram sends occurred.{RESET}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print(f"\n{BOLD}{CYAN}Nexus — 5 Synthetic Profile Validation{RESET}")
    print(f"{CYAN}Running full loop: readiness → recommendations → strategy → Hermes brief{RESET}")
    print(f"{YELLOW}All data is synthetic. No production writes.{RESET}\n")

    profiles = [
        _profile_strong(),
        _profile_medium(),
        _profile_weak(),
        _profile_grant(),
        _profile_trading_locked(),
    ]

    results = []
    for profile in profiles:
        print(f"  Running: {profile['name']} ...", end=" ", flush=True)
        result = _run_profile(profile)
        status = f"{GREEN}PASS{RESET}" if result["passed"] else f"{RED}FAIL{RESET}"
        print(status)
        results.append(result)

    _print_table(results)

    failed = [r for r in results if not r["passed"]]
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
