"""
readiness_engine_test.py — Backend tests for the Nexus Client Readiness Engine.

Run:
    python3 /Users/raymonddavis/nexus-ai/readiness_engine/readiness_engine_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from readiness_engine.guidance_generator import (
    SAFETY_DISCLAIMER,
    get_guidance,
    list_supported_task_types,
)
from readiness_engine.hermes_readiness_brief import build_readiness_brief_section
from readiness_engine.profile_completion import (
    banking_setup_completion,
    business_foundation_completion,
    credit_profile_completion,
    grant_eligibility_completion,
    overall_profile_completion,
    trading_eligibility_completion,
)
from readiness_engine.readiness_scores import (
    calculate_overall_readiness_score,
    is_grant_ready,
    is_trading_eligible,
    score_banking_setup,
    score_business_foundation,
    score_credit_profile,
    score_grant_eligibility,
    score_trading_eligibility,
)
from readiness_engine.task_generation import (
    generate_all_tasks,
    generate_business_foundation_tasks,
    generate_credit_profile_tasks,
    generate_trading_tasks,
    get_next_best_action,
)
import readiness_engine.service as svc

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


# ── Sample data ───────────────────────────────────────────────────────────────

def complete_foundation() -> dict:
    return {
        "legal_business_name": "Nexus Holdings LLC",
        "entity_type": "LLC",
        "state_formed": "AZ",
        "ein_status": "active",
        "business_address_status": "active",
        "business_phone_status": "active",
        "business_email_domain_status": "active",
        "website_status": "active",
        "naics_code": "541511",
        "industry": "Technology",
        "time_in_business_months": 24,
        "monthly_revenue": 12000,
        "employee_count": 3,
        "business_bank_account_status": "active",
    }


def incomplete_foundation() -> dict:
    return {
        "legal_business_name": "Nexus Holdings LLC",
        "entity_type": "sole_proprietor",
        "ein_status": "missing",
        "business_email_domain_status": "missing",
        "website_status": "missing",
        "business_bank_account_status": "missing",
    }


def complete_credit() -> dict:
    return {
        "personal_credit_score_estimate": 720,
        "experian_score": 718,
        "equifax_score": 722,
        "transunion_score": 715,
        "credit_utilization": 0.12,
        "inquiries_count": 1,
        "negative_items_count": 0,
        "age_of_credit_history": 96,
        "credit_report_uploaded": True,
        "credit_report_file_url": "https://example.com/report.pdf",
        "duns_status": "active",
        "paydex_score": 82,
        "business_tradelines_count": 3,
    }


def incomplete_credit() -> dict:
    return {
        "personal_credit_score_estimate": 640,
        "credit_utilization": 0.45,
        "inquiries_count": 5,
        "negative_items_count": 2,
        "credit_report_uploaded": False,
        "duns_status": "missing",
    }


def complete_banking() -> dict:
    return {
        "current_business_bank": "Desert Valley CU",
        "account_age_months": 14,
        "average_balance": 8500,
        "monthly_deposits": 11000,
        "nsf_count": 0,
        "verification_status": "verified",
    }


def incomplete_banking() -> dict:
    return {}


def complete_grants() -> dict:
    return {
        "business_location_state": "AZ",
        "business_location_city": "Phoenix",
        "industry": "Technology",
        "revenue_range": "50k-200k",
        "employee_count": 3,
        "business_stage": "growth",
        "use_of_funds": "equipment",
        "certifications": ["WOSB"],
        "grant_documents_uploaded": True,
    }


def incomplete_grants() -> dict:
    return {
        "business_location_state": "AZ",
        "industry": "Technology",
    }


def complete_trading() -> dict:
    return {
        "capital_reserve": 5000,
        "risk_tolerance": "moderate",
        "education_video_completed": True,
        "disclaimer_accepted": True,
        "paper_trading_completed": True,
        "eligibility_status": "eligible",
    }


def incomplete_trading() -> dict:
    return {
        "capital_reserve": 500,
        "risk_tolerance": "moderate",
        "education_video_completed": False,
        "disclaimer_accepted": False,
        "paper_trading_completed": False,
    }


# ── Profile completion tests ──────────────────────────────────────────────────

def test_profile_completion():
    full = business_foundation_completion(complete_foundation())
    check("complete foundation has 100% completion", full["pct"] == 1.0, f"pct={full['pct']}")
    check("complete foundation has no missing fields", len(full["missing_fields"]) == 0, str(full["missing_fields"]))

    partial = business_foundation_completion(incomplete_foundation())
    check("incomplete foundation has < 100% completion", partial["pct"] < 1.0, f"pct={partial['pct']}")
    check("incomplete foundation reports missing fields", len(partial["missing_fields"]) > 0, str(partial["missing_fields"]))

    empty = business_foundation_completion({})
    check("empty foundation has 0% completion", empty["pct"] == 0.0, f"pct={empty['pct']}")

    overall = overall_profile_completion(
        business_foundation_completion(complete_foundation()),
        credit_profile_completion(complete_credit()),
        banking_setup_completion(complete_banking()),
        grant_eligibility_completion(complete_grants()),
        trading_eligibility_completion(complete_trading()),
    )
    check("overall completion is 0.0–1.0 range", 0.0 <= overall["overall_pct"] <= 1.0, f"pct={overall['overall_pct']}")
    check("overall completion has section breakdown", "business_foundation" in overall["sections"], str(list(overall["sections"].keys())))

    trading_full = trading_eligibility_completion(complete_trading())
    check("complete trading profile has 100% completion", trading_full["pct"] == 1.0, f"pct={trading_full['pct']}")

    credit_full = credit_profile_completion(complete_credit())
    check("complete credit profile has 100% completion", credit_full["pct"] == 1.0, f"pct={credit_full['pct']}")


# ── Readiness score tests ─────────────────────────────────────────────────────

def test_readiness_scores():
    f_score = score_business_foundation(complete_foundation())
    check("foundation score 0-100", 0 <= f_score["score"] <= 100, f"score={f_score['score']}")
    check("complete foundation scores > 70", f_score["score"] > 70, f"score={f_score['score']}")
    check("foundation score has SCORE_NOTE", "internal nexus" in f_score["note"].lower(), f_score["note"])

    low_f = score_business_foundation({})
    check("empty foundation scores 0", low_f["score"] == 0.0, f"score={low_f['score']}")

    c_score = score_credit_profile(complete_credit())
    check("credit score 0-100", 0 <= c_score["score"] <= 100, f"score={c_score['score']}")
    check("complete credit scores > 60", c_score["score"] > 60, f"score={c_score['score']}")

    b_score = score_banking_setup(complete_banking())
    check("banking score 0-100", 0 <= b_score["score"] <= 100, f"score={b_score['score']}")
    check("complete banking scores > 70", b_score["score"] > 70, f"score={b_score['score']}")

    g_score = score_grant_eligibility(complete_grants())
    check("grant score 0-100", 0 <= g_score["score"] <= 100, f"score={g_score['score']}")
    check("complete grants scores > 60", g_score["score"] > 60, f"score={g_score['score']}")

    t_score = score_trading_eligibility(complete_trading())
    check("trading score 0-100", 0 <= t_score["score"] <= 100, f"score={t_score['score']}")
    check("complete trading scores > 70", t_score["score"] > 70, f"score={t_score['score']}")

    low_t = score_trading_eligibility(incomplete_trading())
    check("incomplete trading scores < complete", low_t["score"] < t_score["score"], f"incomplete={low_t['score']} complete={t_score['score']}")

    overall = calculate_overall_readiness_score(80, 70, 85, 65, 90)
    check("overall score 0-100", 0 <= overall["score"] <= 100, f"score={overall['score']}")
    check("overall score has 5-section breakdown", len(overall["breakdown"]) == 5, str(list(overall["breakdown"].keys())))
    check("overall score has safety note", "internal nexus" in overall["note"].lower(), overall["note"])


def test_trading_and_grant_locks():
    check("complete trading profile is eligible", is_trading_eligible(complete_trading()), str(complete_trading()))
    check("incomplete trading profile is not eligible", not is_trading_eligible(incomplete_trading()), str(incomplete_trading()))
    check("trading locked until all three requirements complete",
        not is_trading_eligible({"education_video_completed": True, "disclaimer_accepted": True, "paper_trading_completed": False}),
        "paper_trading_completed=False")

    check("complete grant profile is grant ready", is_grant_ready(complete_grants()), str(complete_grants()))
    check("incomplete grant profile is not grant ready", not is_grant_ready(incomplete_grants()), str(incomplete_grants()))


# ── Task generation tests ─────────────────────────────────────────────────────

def test_task_generation():
    tasks = generate_business_foundation_tasks(incomplete_foundation())
    task_types = [t["task_type"] for t in tasks]
    check("missing EIN generates ein_setup task", "ein_setup" in task_types, str(task_types))
    check("missing entity generates llc_formation task", "llc_formation" in task_types, str(task_types))
    check("missing email generates business_email_domain_setup task", "business_email_domain_setup" in task_types, str(task_types))
    check("missing website generates website_setup task", "website_setup" in task_types, str(task_types))
    check("missing bank generates business_bank_account_setup task", "business_bank_account_setup" in task_types, str(task_types))

    no_tasks = generate_business_foundation_tasks(complete_foundation())
    check("complete foundation generates no tasks", len(no_tasks) == 0, str([t["task_type"] for t in no_tasks]))

    credit_tasks = generate_credit_profile_tasks(incomplete_credit())
    ct_types = [t["task_type"] for t in credit_tasks]
    check("missing credit report generates credit_report_upload task", "credit_report_upload" in ct_types, str(ct_types))
    check("negative items generates credit_dispute task", "credit_dispute" in ct_types, str(ct_types))
    check("missing DUNS generates duns_setup task", "duns_setup" in ct_types, str(ct_types))

    trading_tasks = generate_trading_tasks(incomplete_trading())
    tt_types = [t["task_type"] for t in trading_tasks]
    check("missing disclaimer generates trading_disclaimer task", "trading_disclaimer" in tt_types, str(tt_types))
    check("missing paper trading generates paper_trading_setup task", "paper_trading_setup" in tt_types, str(tt_types))

    all_tasks = generate_all_tasks(
        incomplete_foundation(), incomplete_credit(),
        incomplete_banking(), incomplete_grants(), incomplete_trading()
    )
    check("all tasks list is non-empty for incomplete profile", len(all_tasks) > 0, f"count={len(all_tasks)}")

    all_complete = generate_all_tasks(
        complete_foundation(), complete_credit(),
        complete_banking(), complete_grants(), complete_trading()
    )
    check("complete profile generates no tasks", len(all_complete) == 0, f"count={len(all_complete)}")

    next_action = get_next_best_action(all_tasks)
    check("next best action returns a task", next_action is not None, str(next_action))
    check("next best action is high priority when high tasks exist",
        next_action.get("priority") == "high" if any(t.get("priority") == "high" for t in all_tasks) else True,
        f"priority={next_action.get('priority') if next_action else 'none'}")

    check("tasks have guidance_content field", all(t.get("guidance_content") for t in all_tasks), "missing guidance_content")
    check("tasks have sort_order field", all("sort_order" in t for t in all_tasks), "missing sort_order")


# ── Guidance tests ────────────────────────────────────────────────────────────

def test_guidance_generator():
    supported = list_supported_task_types()
    check("all 11 task types have guidance", len(supported) == 11, f"count={len(supported)} types={supported}")

    for task_type in supported:
        guidance = get_guidance(task_type)
        check(f"guidance for {task_type} has why_it_matters", bool(guidance.get("why_it_matters")), task_type)
        check(f"guidance for {task_type} has free_low_cost_path", bool(guidance.get("free_low_cost_path")), task_type)
        check(f"guidance for {task_type} has disclaimer", bool(guidance.get("disclaimer")), task_type)

    llc = get_guidance("llc_formation")
    check("llc_formation mentions Secretary of State", "secretary of state" in llc["free_low_cost_path"].lower(), llc["free_low_cost_path"])
    check("llc_formation mentions Bizee as optional", "bizee" in (llc.get("convenience_paid_path") or "").lower(), llc.get("convenience_paid_path"))

    cr = get_guidance("credit_report_upload")
    check("credit_report_upload mentions AnnualCreditReport.com", "annualcreditreport.com" in cr["free_low_cost_path"].lower(), cr["free_low_cost_path"])
    check("credit_report_upload mentions SmartCredit as optional", "smartcredit" in (cr.get("convenience_paid_path") or "").lower(), cr.get("convenience_paid_path"))

    dispute = get_guidance("credit_dispute")
    check("credit_dispute mentions Docupost as optional service", "docupost" in (dispute.get("convenience_paid_path") or "").lower(), dispute.get("convenience_paid_path"))
    check("credit_dispute does not guarantee results", "not guaranteed" in (dispute.get("notes") or "").lower() or "not guarantee" in (dispute.get("notes") or "").lower(), dispute.get("notes"))


# ── Safety / prohibited language tests ───────────────────────────────────────

def test_no_prohibited_guarantee_language():
    prohibited_phrases = [
        "guarantee credit repair",
        "guarantee approval",
        "guarantee funding",
        "guarantee a grant",
        "guarantee profits",
        "will repair your credit",
        "will get you approved",
        "will be approved",
    ]

    from readiness_engine.guidance_generator import _GUIDANCE_MAP
    for task_type, guidance in _GUIDANCE_MAP.items():
        full_text = " ".join([
            str(guidance.get("why_it_matters") or ""),
            str(guidance.get("free_low_cost_path") or ""),
            str(guidance.get("convenience_paid_path") or ""),
            str(guidance.get("notes") or ""),
        ]).lower()
        for phrase in prohibited_phrases:
            check(
                f"guidance '{task_type}' does not contain '{phrase}'",
                phrase not in full_text,
                f"Found in guidance for {task_type}",
            )

    disclaimer_lower = SAFETY_DISCLAIMER.lower()
    check("SAFETY_DISCLAIMER covers credit repair", "credit repair" in disclaimer_lower, SAFETY_DISCLAIMER[:80])
    check("SAFETY_DISCLAIMER covers funding approval", "funding approval" in disclaimer_lower, SAFETY_DISCLAIMER[:80])
    check("SAFETY_DISCLAIMER covers grant awards", "grant" in disclaimer_lower, SAFETY_DISCLAIMER[:80])
    check("SAFETY_DISCLAIMER covers trading profits", "trading profits" in disclaimer_lower, SAFETY_DISCLAIMER[:80])


# ── Integration trigger tests ─────────────────────────────────────────────────

def test_credit_report_upload_triggers_funding_refresh():
    refresh_calls: list[tuple[str, str]] = []

    original_trigger = svc._trigger_funding_refresh

    def fake_trigger(user_id, tenant_id, reason):
        refresh_calls.append((user_id, reason))

    svc._trigger_funding_refresh = fake_trigger

    original_upsert = svc._upsert_section
    svc._upsert_section = lambda table, user_id, tenant_id, data, fetch_fn: {"ok": True, "rows": [{"id": "row-1"}]}

    try:
        svc.save_credit_profile("user-1", "tenant-1", complete_credit())
    finally:
        svc._trigger_funding_refresh = original_trigger
        svc._upsert_section = original_upsert

    check("credit profile update triggers funding refresh", len(refresh_calls) > 0, str(refresh_calls))
    check("funding refresh reason is credit_profile_updated",
        any("credit_profile" in r[1] for r in refresh_calls),
        str(refresh_calls))


def test_banking_update_triggers_funding_and_relationship_refresh():
    funding_calls: list[tuple[str, str]] = []
    relationship_calls: list[str] = []

    original_funding = svc._trigger_funding_refresh
    original_rel = svc._trigger_relationship_refresh

    def fake_funding(user_id, tenant_id, reason):
        funding_calls.append((user_id, reason))

    def fake_rel(user_id, tenant_id):
        relationship_calls.append(user_id)

    svc._trigger_funding_refresh = fake_funding
    svc._trigger_relationship_refresh = fake_rel
    original_upsert = svc._upsert_section
    svc._upsert_section = lambda table, user_id, tenant_id, data, fetch_fn: {"ok": True, "rows": [{"id": "row-1"}]}

    try:
        svc.save_banking_profile("user-2", "tenant-1", complete_banking())
    finally:
        svc._trigger_funding_refresh = original_funding
        svc._trigger_relationship_refresh = original_rel
        svc._upsert_section = original_upsert

    check("banking update triggers funding refresh", len(funding_calls) > 0, str(funding_calls))
    check("banking update triggers relationship refresh", len(relationship_calls) > 0, str(relationship_calls))


def test_grant_profile_marks_grant_ready():
    check("minimum grant fields mark user grant-ready", is_grant_ready(complete_grants()), str(complete_grants()))
    check("partial grant profile not grant-ready", not is_grant_ready(incomplete_grants()), str(incomplete_grants()))

    min_required = {
        "business_location_state": "AZ",
        "industry": "Tech",
        "revenue_range": "50k-200k",
        "business_stage": "growth",
        "use_of_funds": "equipment",
    }
    check("minimum required fields marks grant-ready", is_grant_ready(min_required), str(min_required))


def test_trading_locked_until_requirements_complete():
    check("trading locked without video", not is_trading_eligible({"education_video_completed": False, "disclaimer_accepted": True, "paper_trading_completed": True}), "video=False")
    check("trading locked without disclaimer", not is_trading_eligible({"education_video_completed": True, "disclaimer_accepted": False, "paper_trading_completed": True}), "disclaimer=False")
    check("trading locked without paper trading", not is_trading_eligible({"education_video_completed": True, "disclaimer_accepted": True, "paper_trading_completed": False}), "paper=False")
    check("trading unlocked when all three complete", is_trading_eligible({"education_video_completed": True, "disclaimer_accepted": True, "paper_trading_completed": True}), "all=True")


# ── Hermes brief tests ────────────────────────────────────────────────────────

def test_hermes_readiness_brief():
    tasks = generate_all_tasks(
        incomplete_foundation(), incomplete_credit(),
        incomplete_banking(), incomplete_grants(), incomplete_trading()
    )
    snapshot = {
        "overall_score": 42,
        "completion": {"overall_pct": 0.38},
        "tasks": tasks,
        "next_best_action": get_next_best_action(tasks),
        "grant_ready": False,
        "trading_eligible": False,
    }
    brief = build_readiness_brief_section(snapshot)
    check("Hermes brief has brief_text", bool(brief.get("brief_text")), "missing brief_text")
    check("Hermes brief includes score", "42" in brief["brief_text"], brief["brief_text"][:100])
    check("Hermes brief includes disclaimer", SAFETY_DISCLAIMER[:30] in brief["brief_text"], brief["brief_text"][-100:])
    check("Hermes brief has pending_task_count", isinstance(brief.get("pending_task_count"), int), str(brief.get("pending_task_count")))
    check("Hermes brief has next_best_action", brief.get("next_best_action") is not None, str(brief.get("next_best_action")))

    full_snapshot = {
        "overall_score": 95,
        "completion": {"overall_pct": 1.0},
        "tasks": [],
        "next_best_action": None,
        "grant_ready": True,
        "trading_eligible": True,
    }
    full_brief = build_readiness_brief_section(full_snapshot)
    check("complete profile brief shows 0 pending tasks", full_brief.get("pending_task_count") == 0, str(full_brief.get("pending_task_count")))


# ── Snapshot tests ────────────────────────────────────────────────────────────

def test_build_readiness_snapshot_offline():
    original_foundation = svc.get_business_foundation
    original_credit = svc.get_credit_profile
    original_banking = svc.get_banking_profile
    original_grant = svc.get_grant_profile
    original_trading = svc.get_trading_profile

    svc.get_business_foundation = lambda *a, **k: incomplete_foundation()
    svc.get_credit_profile = lambda *a, **k: incomplete_credit()
    svc.get_banking_profile = lambda *a, **k: incomplete_banking()
    svc.get_grant_profile = lambda *a, **k: incomplete_grants()
    svc.get_trading_profile = lambda *a, **k: incomplete_trading()

    try:
        snapshot = svc.build_readiness_snapshot("user-snap", "tenant-1")
    finally:
        svc.get_business_foundation = original_foundation
        svc.get_credit_profile = original_credit
        svc.get_banking_profile = original_banking
        svc.get_grant_profile = original_grant
        svc.get_trading_profile = original_trading

    check("snapshot has overall_score", isinstance(snapshot.get("overall_score"), (int, float)), str(snapshot.get("overall_score")))
    check("snapshot score is 0-100", 0 <= snapshot["overall_score"] <= 100, str(snapshot["overall_score"]))
    check("snapshot has tasks list", isinstance(snapshot.get("tasks"), list), str(type(snapshot.get("tasks"))))
    check("snapshot has completion dict", isinstance(snapshot.get("completion"), dict), str(type(snapshot.get("completion"))))
    check("snapshot has grant_ready flag", isinstance(snapshot.get("grant_ready"), bool), str(snapshot.get("grant_ready")))
    check("snapshot has trading_eligible flag", isinstance(snapshot.get("trading_eligible"), bool), str(snapshot.get("trading_eligible")))
    check("snapshot has note with safety language", "internal nexus" in snapshot.get("note", "").lower(), snapshot.get("note"))


# ── Example tasks output ──────────────────────────────────────────────────────

def print_example_tasks():
    print("\n── Example Generated Tasks ──────────────────────────────────────")
    tasks = generate_all_tasks(
        incomplete_foundation(), incomplete_credit(),
        {}, incomplete_grants(), incomplete_trading()
    )
    for t in tasks:
        guidance = t.get("guidance_content") or {}
        print(f"\n  [{t['priority'].upper()}] {t['task_title']} ({t['task_type']})")
        print(f"    Category: {t['category']}")
        print(f"    Unlocks: {t.get('unlocks_feature') or 'n/a'}")
        print(f"    Why: {guidance.get('why_it_matters', '')[:80]}...")
        print(f"    Free path: {guidance.get('free_low_cost_path', '')[:80]}...")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    test_profile_completion()
    test_readiness_scores()
    test_trading_and_grant_locks()
    test_task_generation()
    test_guidance_generator()
    test_no_prohibited_guarantee_language()
    test_credit_report_upload_triggers_funding_refresh()
    test_banking_update_triggers_funding_and_relationship_refresh()
    test_grant_profile_marks_grant_ready()
    test_trading_locked_until_requirements_complete()
    test_hermes_readiness_brief()
    test_build_readiness_snapshot_offline()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"{len(failed)} test(s) FAILED:")
        for name in failed:
            print(f"  - {name}")
        print_example_tasks()
        return 1

    print(f"All {len(_results)} checks passed.")
    print_example_tasks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
