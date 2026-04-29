from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from funding_engine.business_readiness_score import calculate_business_readiness_score
from funding_engine.capital_ladder import evaluate_tier_progress
from funding_engine.hermes_brief import build_daily_capital_brief
from funding_engine.recommendations import generate_recommendations
from funding_engine.relationship_scoring import score_relationship
from lib.growth_support import safe_insert, safe_patch
from scripts.prelaunch_utils import rest_select, supabase_request, table_exists, utc_now_iso

RECOMMENDATION_VERSION = "v1"
ACTIVE_RECOMMENDATION_STATUSES = {"recommended", "pending_review", "active"}
HISTORICAL_RECOMMENDATION_STATUSES = {"completed", "dismissed", "invoiced"}


def _safe_select(path: str) -> list[dict[str, Any]]:
    try:
        return rest_select(path) or []
    except Exception:
        return []


def _quote(value: str | None) -> str:
    return urllib.parse.quote(str(value or ""), safe="")


def _column_supported(table: str, column: str) -> bool:
    try:
        rest_select(f"{table}?select={urllib.parse.quote(column, safe='')}&limit=0")
        return True
    except Exception:
        return False


def get_user_profile(user_id: str) -> dict[str, Any] | None:
    rows = _safe_select(
        f"user_profiles?select=id,full_name,role,subscription_plan,onboarding_complete,updated_at"
        f"&id=eq.{_quote(user_id)}&limit=1"
    )
    return rows[0] if rows else None


def get_user_business_score_input(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_quote(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_quote(tenant_id)}")
    query = "user_business_score_inputs?select=*&order=created_at.desc&limit=1&" + "&".join(filters)
    rows = _safe_select(query)
    return rows[0] if rows else None


def get_banking_relationships(user_id: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    filters = [f"user_id=eq.{_quote(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_quote(tenant_id)}")
    query = "banking_relationships?select=*&order=created_at.desc&" + "&".join(filters)
    return _safe_select(query)


def get_user_tier_progress(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_quote(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_quote(tenant_id)}")
    query = "user_tier_progress?select=*&order=created_at.desc&limit=1&" + "&".join(filters)
    rows = _safe_select(query)
    return rows[0] if rows else None


def get_lending_institutions(limit: int = 50) -> list[dict[str, Any]]:
    return _safe_select(f"lending_institutions?select=*&order=created_at.desc&limit={limit}")


def get_approval_patterns(limit: int = 200) -> list[dict[str, Any]]:
    return _safe_select(f"card_approval_patterns?select=*&order=updated_at.desc&limit={limit}")


def get_active_recommendations(user_id: str, tenant_id: str | None = None) -> list[dict[str, Any]]:
    filters = [f"user_id=eq.{_quote(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_quote(tenant_id)}")
    status_filter = ",".join(sorted(ACTIVE_RECOMMENDATION_STATUSES))
    query = (
        "funding_recommendations?select=*"
        f"&status=in.({status_filter})&order=created_at.desc&" + "&".join(filters)
    )
    return _safe_select(query)


def _recommendation_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("tier"),
        row.get("recommendation_type"),
        (row.get("institution_name") or "").strip().lower(),
        (row.get("product_name") or "").strip().lower(),
        (row.get("product_type") or "").strip().lower(),
    )


def build_funding_snapshot(user_id: str, tenant_id: str | None = None, user_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    db_profile = get_user_profile(user_id) or {}
    user_profile = {**db_profile, **(user_profile or {})}
    business_input = get_user_business_score_input(user_id, tenant_id)
    relationships = get_banking_relationships(user_id, tenant_id)
    relationship_scores = [score_relationship(row)["relationship_score"] for row in relationships]
    tier_progress = get_user_tier_progress(user_id, tenant_id) or {}
    readiness = calculate_business_readiness_score(
        profile=user_profile,
        business_score_inputs=business_input or {},
        relationships=[{"relationship_score": value} for value in relationship_scores],
        execution_history={
            "reported_results_count": tier_progress.get("reported_tier_1_results_count"),
            "verified_results_count": tier_progress.get("verified_results_count"),
            "completed_actions_count": user_profile.get("completed_tier_1_actions"),
        },
    )
    ladder = evaluate_tier_progress(
        readiness_score=readiness["score"],
        relationship_score=max(relationship_scores) if relationship_scores else 0,
        tier_1_actions_completed=int(user_profile.get("completed_tier_1_actions") or 0),
        reported_tier_1_results_count=int(tier_progress.get("reported_tier_1_results_count") or 0),
        relationship_prep_completed=bool(user_profile.get("relationship_prep_completed")),
        relationship_prep_scheduled=bool(user_profile.get("relationship_prep_scheduled")),
    )
    missing = []
    if not business_input:
        missing.append("business score inputs")
    if not relationships:
        missing.append("banking relationship inputs")
    return {
        "user_profile": user_profile,
        "business_score_input": business_input,
        "banking_relationships": relationships,
        "readiness": readiness,
        "tier_progress": ladder,
        "relationship_score": max(relationship_scores) if relationship_scores else 0,
        "missing_inputs": missing,
    }


def has_usable_profile_data(snapshot: dict[str, Any], user_profile: dict[str, Any] | None = None) -> bool:
    user_profile = user_profile or snapshot.get("user_profile") or {}
    business_input = snapshot.get("business_score_input") or {}
    relationships = snapshot.get("banking_relationships") or []
    if business_input:
        return True
    if relationships:
        return True
    if user_profile.get("onboarding_complete") and user_profile.get("personal_credit_score"):
        return True
    return False


def generate_user_recommendations(
    *,
    user_id: str,
    tenant_id: str | None = None,
    user_profile: dict[str, Any] | None = None,
    tier: int | None = None,
) -> dict[str, Any]:
    snapshot = build_funding_snapshot(user_id, tenant_id, user_profile=user_profile)
    profile_for_scoring = {
        **(snapshot["user_profile"] or {}),
        "average_balance": (snapshot["business_score_input"] or {}).get("average_balance") or (snapshot["user_profile"] or {}).get("average_balance"),
        "monthly_deposits": (snapshot["business_score_input"] or {}).get("monthly_deposits") or (snapshot["user_profile"] or {}).get("monthly_deposits"),
        "deposit_consistency": (snapshot["business_score_input"] or {}).get("revenue_consistency") or (snapshot["user_profile"] or {}).get("deposit_consistency"),
    }
    recs = generate_recommendations(
        user_profile=profile_for_scoring,
        readiness_score=snapshot["readiness"]["score"],
        institutions=get_lending_institutions(),
        approval_patterns=get_approval_patterns(),
        tier=tier,
    )
    return {
        "snapshot": snapshot,
        "recommendations": recs,
    }


def _build_source_snapshot(reason: str, data: dict[str, Any]) -> dict[str, Any]:
    snapshot = data.get("snapshot") or {}
    return {
        "generated_at": utc_now_iso(),
        "reason": reason,
        "readiness_score": (snapshot.get("readiness") or {}).get("score"),
        "relationship_score": snapshot.get("relationship_score"),
        "missing_inputs": snapshot.get("missing_inputs") or [],
        "tier_progress": snapshot.get("tier_progress") or {},
    }


def _build_recommendation_payload(
    *,
    user_id: str,
    tenant_id: str | None,
    row: dict[str, Any],
    reason: str,
    source_snapshot: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "tier": row.get("tier"),
        "recommendation_type": row.get("recommendation_type"),
        "institution_name": row.get("institution_name"),
        "product_name": row.get("product_name"),
        "product_type": row.get("product_type"),
        "approval_score": row.get("approval_score"),
        "approval_score_without_relationship": row.get("approval_score_without_relationship"),
        "relationship_boost": row.get("relationship_boost"),
        "expected_limit_low": row.get("expected_limit_low"),
        "expected_limit_high": row.get("expected_limit_high"),
        "confidence_level": row.get("confidence_level"),
        "reason": row.get("reason"),
        "prep_steps": row.get("prep_steps"),
        "evidence_summary": row.get("evidence_summary"),
        "disclaimer": row.get("disclaimer"),
        "status": row.get("status", "recommended"),
    }
    if _column_supported("funding_recommendations", "last_generated_at"):
        payload["last_generated_at"] = utc_now_iso()
    if _column_supported("funding_recommendations", "generation_reason"):
        payload["generation_reason"] = reason
    if _column_supported("funding_recommendations", "recommendation_version"):
        payload["recommendation_version"] = RECOMMENDATION_VERSION
    if _column_supported("funding_recommendations", "source_snapshot"):
        payload["source_snapshot"] = source_snapshot
    else:
        evidence = dict(payload.get("evidence_summary") or {})
        evidence["_source_snapshot"] = source_snapshot
        payload["evidence_summary"] = evidence
    return payload


def _log_recommendation_run(
    *,
    user_id: str,
    tenant_id: str | None,
    reason: str,
    force: bool,
    status: str,
    created_count: int = 0,
    updated_count: int = 0,
    archived_count: int = 0,
    skipped_reason: str | None = None,
    error: str | None = None,
    source_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "reason": reason,
        "force": force,
        "status": status,
        "recommendations_created": created_count,
        "recommendations_updated": updated_count,
        "recommendations_archived": archived_count,
        "skipped_reason": skipped_reason,
        "error": error,
        "source_snapshot": source_snapshot or {},
        "completed_at": utc_now_iso(),
    }
    return safe_insert("funding_recommendation_runs", payload)


def create_or_refresh_user_recommendations(
    user_id: str,
    tenant_id: str | None,
    reason: str,
    force: bool = False,
) -> dict[str, Any]:
    data = generate_user_recommendations(user_id=user_id, tenant_id=tenant_id)
    snapshot = data["snapshot"]
    source_snapshot = _build_source_snapshot(reason, data)
    if not has_usable_profile_data(snapshot):
        _log_recommendation_run(
            user_id=user_id,
            tenant_id=tenant_id,
            reason=reason,
            force=force,
            status="skipped",
            skipped_reason="missing_usable_profile_data",
            source_snapshot=source_snapshot,
        )
        data["saved_recommendations"] = []
        data["refresh"] = {"created": 0, "updated": 0, "skipped": True, "reason": "missing_usable_profile_data"}
        return data

    existing = get_active_recommendations(user_id, tenant_id)
    existing_by_key = {_recommendation_key(row): row for row in existing}
    saved: list[dict[str, Any]] = []
    created_count = 0
    updated_count = 0

    for row in data["recommendations"]:
        payload = _build_recommendation_payload(
            user_id=user_id,
            tenant_id=tenant_id,
            row=row,
            reason=reason,
            source_snapshot=source_snapshot,
        )
        existing_row = existing_by_key.get(_recommendation_key(row))
        if existing_row and existing_row.get("status") in ACTIVE_RECOMMENDATION_STATUSES:
            updated = safe_patch(
                f"funding_recommendations?id=eq.{_quote(existing_row.get('id'))}",
                payload,
            )
            if updated.get("ok"):
                saved.extend(updated.get("rows") or [])
                updated_count += 1
            continue
        created = safe_insert("funding_recommendations", payload)
        if created.get("ok"):
            saved.extend(created.get("rows") or [])
            created_count += 1

    _log_recommendation_run(
        user_id=user_id,
        tenant_id=tenant_id,
        reason=reason,
        force=force,
        status="completed",
        created_count=created_count,
        updated_count=updated_count,
        source_snapshot=source_snapshot,
    )
    data["saved_recommendations"] = saved
    data["refresh"] = {"created": created_count, "updated": updated_count, "skipped": False}
    return data


def persist_user_recommendations(
    *,
    user_id: str,
    tenant_id: str | None = None,
    user_profile: dict[str, Any] | None = None,
    tier: int | None = None,
) -> dict[str, Any]:
    if user_profile is not None or tier is not None:
        return generate_user_recommendations(user_id=user_id, tenant_id=tenant_id, user_profile=user_profile, tier=tier)
    return create_or_refresh_user_recommendations(
        user_id=user_id,
        tenant_id=tenant_id,
        reason="manual_persist_request",
        force=False,
    )


def queue_recommendation_refresh(
    *,
    user_id: str,
    tenant_id: str | None,
    reason: str,
    force: bool = False,
    source_table: str | None = None,
    source_row_id: str | None = None,
) -> dict[str, Any]:
    if not table_exists("funding_recommendation_jobs"):
        return {"ok": False, "error": "table_missing:funding_recommendation_jobs"}
    body = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "reason": reason,
        "force": force,
        "source_table": source_table,
        "source_row_id": source_row_id,
        "status": "pending",
    }
    return safe_insert("funding_recommendation_jobs", body)


def get_users_needing_recommendations() -> list[dict[str, Any]]:
    rows = _safe_select(
        "user_profiles?select=id,onboarding_complete,updated_at&order=updated_at.desc&limit=250"
    )
    score_rows = _safe_select("user_business_score_inputs?select=user_id,tenant_id,updated_at&limit=250")
    relationship_rows = _safe_select("banking_relationships?select=user_id,tenant_id,updated_at&limit=250")
    active_rows = _safe_select(
        "funding_recommendations?select=user_id,tenant_id,status,last_generated_at"
        "&status=in.(recommended,pending_review,active)&limit=500"
    )
    active_users = {(row.get("tenant_id"), row.get("user_id")) for row in active_rows}
    candidates: dict[tuple[Any, Any], dict[str, Any]] = {}
    for row in rows:
        if row.get("onboarding_complete"):
            candidates[(None, row.get("id"))] = {"tenant_id": None, "user_id": row.get("id"), "reason": "onboarding_complete"}
    for row in score_rows + relationship_rows:
        key = (row.get("tenant_id"), row.get("user_id"))
        candidates[key] = {"tenant_id": row.get("tenant_id"), "user_id": row.get("user_id"), "reason": "profile_data_available"}
    return [row for key, row in candidates.items() if key not in active_users and row.get("user_id")]


def get_users_with_stale_recommendations() -> list[dict[str, Any]]:
    rows = _safe_select(
        "funding_recommendations?select=id,user_id,tenant_id,product_name,last_generated_at,status"
        "&status=in.(recommended,pending_review,active)"
        "&last_generated_at=lt.now()-interval'7 days'&order=last_generated_at.asc&limit=250"
    )
    if rows:
        return rows
    # Fallback for PostgREST interval filter compatibility.
    fallback_rows = _safe_select(
        "funding_recommendations?select=id,user_id,tenant_id,product_name,last_generated_at,status"
        "&status=in.(recommended,pending_review,active)&order=last_generated_at.asc.nullsfirst&limit=250"
    )
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    stale = []
    for row in fallback_rows:
        raw = row.get("last_generated_at")
        if not raw:
            stale.append(row)
            continue
        try:
            if datetime.fromisoformat(str(raw).replace("Z", "+00:00")) < cutoff:
                stale.append(row)
        except Exception:
            stale.append(row)
    return stale


def get_recent_recommendation_errors(limit: int = 20) -> list[dict[str, Any]]:
    return _safe_select(
        "funding_recommendation_runs?select=user_id,tenant_id,reason,status,error,skipped_reason,created_at,completed_at"
        "&status=in.(failed,skipped)&order=created_at.desc"
        f"&limit={limit}"
    )


def process_pending_recommendation_jobs(limit: int = 25) -> dict[str, Any]:
    jobs = _safe_select(
        "funding_recommendation_jobs?select=*&status=eq.pending&order=created_at.asc"
        f"&limit={limit}"
    )
    processed = 0
    failed = 0
    skipped = 0
    for job in jobs:
        job_id = job.get("id")
        try:
            result = create_or_refresh_user_recommendations(
                user_id=job["user_id"],
                tenant_id=job.get("tenant_id"),
                reason=job.get("reason") or "queued_refresh",
                force=bool(job.get("force")),
            )
            status = "completed"
            if result.get("refresh", {}).get("skipped"):
                status = "skipped"
                skipped += 1
            processed += 1
            safe_patch(
                f"funding_recommendation_jobs?id=eq.{_quote(job_id)}",
                {"status": status, "processed_at": utc_now_iso(), "error": None},
            )
        except Exception as exc:
            failed += 1
            safe_patch(
                f"funding_recommendation_jobs?id=eq.{_quote(job_id)}",
                {"status": "failed", "processed_at": utc_now_iso(), "error": str(exc)},
            )
    return {"processed": processed, "failed": failed, "skipped": skipped, "job_count": len(jobs)}


def build_hermes_funding_brief(user_id: str, tenant_id: str | None = None, user_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    active = get_active_recommendations(user_id, tenant_id)
    if not active:
        create_or_refresh_user_recommendations(
            user_id=user_id,
            tenant_id=tenant_id,
            reason="hermes_brief_auto_generate",
            force=False,
        )
    data = generate_user_recommendations(user_id=user_id, tenant_id=tenant_id, user_profile=user_profile, tier=None)
    recs = data["recommendations"]
    snapshot = data["snapshot"]
    top_tier_1 = next((row for row in recs if row.get("tier") == 1), None)
    relationship_move = next((row for row in recs if row.get("recommendation_type") == "relationship_action"), None)
    tier_progress = snapshot["tier_progress"]
    return build_daily_capital_brief({
        "top_tier_1_move": top_tier_1["reason"] if top_tier_1 else None,
        "relationship_move": relationship_move["reason"] if relationship_move else None,
        "credit_union_opportunity": top_tier_1["product_name"] if top_tier_1 else None,
        "readiness_score": snapshot["readiness"]["score"],
        "missing_data": snapshot["missing_inputs"],
        "tier_progress": (
            f"Current tier: {tier_progress['current_tier']} | "
            f"Tier 2: {tier_progress['tier_2_status']}"
        ),
        "referral_earnings_reminder": "Referral earnings appear only after eligible Tier 1 or Tier 2 funding is reported.",
    })
