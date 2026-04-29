from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any

from funding_engine.business_readiness_score import calculate_business_readiness_score
from funding_engine.capital_ladder import evaluate_tier_progress
from funding_engine.constants import DISCLAIMER
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


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _is_stale_timestamp(value: Any, days: int = 7) -> bool:
    stamp = _parse_timestamp(value)
    if not stamp:
        return True
    return stamp < (datetime.now(timezone.utc) - timedelta(days=days))


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


def _summarize_recommendations(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            -(float(row.get("approval_score") or 0)),
            int(row.get("tier") or 99),
            str(row.get("product_name") or ""),
        ),
    )
    summary = []
    for row in ranked[:limit]:
        summary.append({
            "id": row.get("id"),
            "tier": row.get("tier"),
            "product_name": row.get("product_name"),
            "institution_name": row.get("institution_name"),
            "product_type": row.get("product_type"),
            "recommendation_type": row.get("recommendation_type"),
            "approval_score": row.get("approval_score"),
            "confidence_level": row.get("confidence_level"),
            "expected_limit_low": row.get("expected_limit_low"),
            "expected_limit_high": row.get("expected_limit_high"),
            "reason": row.get("reason"),
            "disclaimer": row.get("disclaimer") or DISCLAIMER,
        })
    return summary


def _pick_journey_next_action(
    *,
    readiness_snapshot: dict[str, Any] | None,
    strategy: dict[str, Any] | None,
    top_recommendations: list[dict[str, Any]],
    missing_inputs: list[str],
) -> dict[str, Any]:
    readiness_snapshot = readiness_snapshot or {}
    readiness_action = readiness_snapshot.get("next_best_action") or {}
    readiness_score = float(readiness_snapshot.get("overall_score") or 0)
    pending_tasks = [row for row in (readiness_snapshot.get("tasks") or []) if row.get("status") == "pending"]
    has_high_priority_tasks = any((row.get("priority") or "").lower() == "high" for row in pending_tasks)

    if readiness_action and (readiness_score < 65 or has_high_priority_tasks):
        return {
            "source": "readiness",
            "phase": "readiness",
            "priority": readiness_action.get("priority") or "high",
            "title": readiness_action.get("task_title") or "Complete the next readiness task.",
            "detail": readiness_action.get("task_description") or "",
            "task_id": readiness_action.get("id"),
            "safe_action": {
                "type": "complete_task",
                "method": "POST",
                "endpoint": f"/api/readiness/tasks/{readiness_action.get('id')}/complete" if readiness_action.get("id") else None,
            },
        }

    strategy_action = (strategy or {}).get("next_best_action") or {}
    if strategy_action:
        return {
            "source": "funding_strategy",
            "phase": (strategy or {}).get("current_phase") or strategy_action.get("phase") or "funding",
            "priority": strategy_action.get("priority") or "medium",
            "title": strategy_action.get("action") or "Review your funding strategy.",
            "detail": strategy_action.get("detail") or "",
            "safe_action": {
                "type": "refresh_recommendations",
                "method": "POST",
                "endpoint": "/api/funding/recommendations/refresh",
            },
        }

    if top_recommendations:
        row = top_recommendations[0]
        return {
            "source": "recommendations",
            "phase": "funding",
            "priority": "medium",
            "title": row.get("product_name") or "Review your top funding recommendation.",
            "detail": row.get("reason") or DISCLAIMER,
            "safe_action": {
                "type": "refresh_recommendations",
                "method": "POST",
                "endpoint": "/api/funding/recommendations/refresh",
            },
        }

    if missing_inputs:
        missing = missing_inputs[0]
        return {
            "source": "profile_gap",
            "phase": "readiness",
            "priority": "high",
            "title": f"Add {missing}.",
            "detail": "Nexus can generate stronger guidance after the missing profile data is filled in.",
            "safe_action": {
                "type": "recalculate_readiness",
                "method": "POST",
                "endpoint": "/api/readiness/recalculate",
            },
        }

    return {
        "source": "system",
        "phase": "readiness",
        "priority": "medium",
        "title": "Review your Funding Journey.",
        "detail": DISCLAIMER,
        "safe_action": {
            "type": "refresh_recommendations",
            "method": "POST",
            "endpoint": "/api/funding/recommendations/refresh",
        },
    }


def build_funding_journey_orchestrator(
    user_id: str,
    tenant_id: str | None = None,
    *,
    auto_generate_if_missing: bool = False,
    force_refresh: bool = False,
) -> dict[str, Any]:
    from funding_engine.strategy_engine import build_and_persist_strategy, get_active_strategy
    from readiness_engine.service import build_readiness_snapshot

    readiness_snapshot = build_readiness_snapshot(user_id, tenant_id)
    funding_snapshot = build_funding_snapshot(user_id, tenant_id)
    active_recommendations = get_active_recommendations(user_id, tenant_id)
    generated = False

    if auto_generate_if_missing and (force_refresh or not active_recommendations) and has_usable_profile_data(funding_snapshot):
        refresh_reason = "journey_orchestrator_force_refresh" if force_refresh else "journey_orchestrator_auto_generate"
        refresh_result = create_or_refresh_user_recommendations(
            user_id=user_id,
            tenant_id=tenant_id,
            reason=refresh_reason,
            force=force_refresh,
        )
        active_recommendations = get_active_recommendations(user_id, tenant_id)
        generated = not bool(refresh_result.get("refresh", {}).get("skipped"))

    strategy = get_active_strategy(user_id, tenant_id)
    if not strategy and active_recommendations:
        try:
            strategy_result = build_and_persist_strategy(
                user_id=user_id,
                tenant_id=tenant_id,
                user_profile=funding_snapshot.get("user_profile") or {},
                readiness_profile=funding_snapshot.get("readiness") or {},
                recommendations=active_recommendations,
                relationships=funding_snapshot.get("banking_relationships") or [],
                force=False,
            )
            strategy = strategy_result.get("strategy")
        except Exception:
            strategy = None

    missing_inputs = list(dict.fromkeys(
        list(funding_snapshot.get("missing_inputs") or [])
        + [
            section.replace("_", " ")
            for section, meta in ((readiness_snapshot.get("completion") or {}).get("sections") or {}).items()
            if float(meta.get("pct") or 0) < 1.0
        ]
    ))
    top_recommendations = _summarize_recommendations(active_recommendations)
    stale_recommendations = [row for row in active_recommendations if _is_stale_timestamp(row.get("last_generated_at"))]
    next_action = _pick_journey_next_action(
        readiness_snapshot=readiness_snapshot,
        strategy=strategy,
        top_recommendations=top_recommendations,
        missing_inputs=missing_inputs,
    )

    warnings = []
    if not has_usable_profile_data(funding_snapshot):
        warnings.append("Profile data is still too thin for strong funding recommendations.")
    if not active_recommendations:
        warnings.append("No active funding recommendations are on file yet.")
    if stale_recommendations:
        warnings.append("Some active recommendations are older than 7 days and should be refreshed.")

    completion = readiness_snapshot.get("completion") or {}
    sections = completion.get("sections") or {}
    available_actions = [
        {
            "type": "refresh_recommendations",
            "label": "Refresh Recommendations",
            "method": "POST",
            "endpoint": "/api/funding/recommendations/refresh",
            "body": {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "reason": "frontend_orchestrator_refresh",
                "force": False,
            },
            "safe": True,
        },
        {
            "type": "recalculate_readiness",
            "label": "Recalculate Readiness",
            "method": "POST",
            "endpoint": "/api/readiness/recalculate",
            "body": {
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
            "safe": True,
        },
    ]
    pending_tasks = [row for row in (readiness_snapshot.get("tasks") or []) if row.get("status") == "pending"]
    if pending_tasks and pending_tasks[0].get("id"):
        available_actions.append({
            "type": "complete_top_readiness_task",
            "label": "Mark Top Task Complete",
            "method": "POST",
            "endpoint": f"/api/readiness/tasks/{pending_tasks[0]['id']}/complete",
            "body": {},
            "safe": True,
        })

    return {
        "orchestrator_version": "v1",
        "user_id": user_id,
        "tenant_id": tenant_id,
        "generated_at": utc_now_iso(),
        "auto_generated_recommendations": generated,
        "can_generate_recommendations": has_usable_profile_data(funding_snapshot),
        "missing_inputs": missing_inputs,
        "warnings": warnings,
        "next_best_action": next_action,
        "available_actions": available_actions,
        "readiness": {
            "overall_score": readiness_snapshot.get("overall_score"),
            "completion_pct": completion.get("overall_pct"),
            "pending_task_count": len(pending_tasks),
            "next_best_action": readiness_snapshot.get("next_best_action"),
            "incomplete_sections": [
                {
                    "section": name,
                    "pct": meta.get("pct"),
                    "missing_fields": meta.get("missing_fields") or [],
                }
                for name, meta in sections.items()
                if float(meta.get("pct") or 0) < 1.0
            ],
            "grant_ready": readiness_snapshot.get("grant_ready"),
            "trading_eligible": readiness_snapshot.get("trading_eligible"),
            "note": readiness_snapshot.get("note"),
        },
        "funding": {
            "current_phase": (strategy or {}).get("current_phase") or "readiness",
            "strategy_summary": (strategy or {}).get("strategy_summary"),
            "strategy_next_best_action": (strategy or {}).get("next_best_action"),
            "estimated_funding_low": (strategy or {}).get("estimated_funding_low"),
            "estimated_funding_high": (strategy or {}).get("estimated_funding_high"),
            "relationship_score": funding_snapshot.get("relationship_score"),
            "tier_progress": funding_snapshot.get("tier_progress"),
            "active_recommendation_count": len(active_recommendations),
            "stale_recommendation_count": len(stale_recommendations),
            "last_recommendation_generated_at": max(
                [row.get("last_generated_at") for row in active_recommendations if row.get("last_generated_at")],
                default=None,
            ),
            "top_recommendations": top_recommendations,
        },
        "disclaimer": DISCLAIMER,
    }


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

    # Fetch historical (dismissed/completed/invoiced) keys so we never re-insert them.
    hist_filters = [f"user_id=eq.{_quote(user_id)}"]
    if tenant_id:
        hist_filters.append(f"tenant_id=eq.{_quote(tenant_id)}")
    historical = _safe_select(
        "funding_recommendations?select=tier,recommendation_type,institution_name,product_name,product_type"
        "&status=in.(dismissed,completed,invoiced)&limit=500&" + "&".join(hist_filters)
    )
    dismissed_keys = {_recommendation_key(row) for row in historical}

    saved: list[dict[str, Any]] = []
    created_count = 0
    updated_count = 0

    for row in data["recommendations"]:
        if _recommendation_key(row) in dismissed_keys:
            continue
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

    # Build and persist funding strategy after recommendations are saved.
    try:
        from funding_engine.strategy_engine import build_and_persist_strategy
        snap = data.get("snapshot") or {}
        strategy_result = build_and_persist_strategy(
            user_id=user_id,
            tenant_id=tenant_id,
            user_profile=snap.get("user_profile") or {},
            readiness_profile=snap.get("readiness") or {},
            recommendations=data.get("recommendations") or [],
            relationships=snap.get("banking_relationships") or [],
            force=force,
        )
        data["strategy"] = strategy_result
    except Exception:
        data["strategy"] = {"persisted": False, "error": "strategy_build_skipped"}

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
    processed_pairs: set[tuple[Any, Any]] = set()
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
            processed_pairs.add((job.get("tenant_id"), job["user_id"]))
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
    return {
        "processed": processed,
        "failed": failed,
        "skipped": skipped,
        "job_count": len(jobs),
        "processed_pairs": processed_pairs,
    }


def build_hermes_funding_brief(user_id: str, tenant_id: str | None = None, user_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    from funding_engine.strategy_engine import build_hermes_strategy_brief, get_active_strategy

    active = get_active_recommendations(user_id, tenant_id)
    if not active:
        create_or_refresh_user_recommendations(
            user_id=user_id,
            tenant_id=tenant_id,
            reason="hermes_brief_auto_generate",
            force=False,
        )
        active = get_active_recommendations(user_id, tenant_id)

    if active:
        # Use saved recommendations — avoid a redundant full re-score pass.
        snapshot = build_funding_snapshot(user_id, tenant_id, user_profile=user_profile)
        recs = active
    else:
        # Fallback: no saved recs after auto-generate (e.g. missing profile data).
        data = generate_user_recommendations(user_id=user_id, tenant_id=tenant_id, user_profile=user_profile, tier=None)
        recs = data["recommendations"]
        snapshot = data["snapshot"]

    top_tier_1 = next((row for row in recs if row.get("tier") == 1), None)
    relationship_move = next((row for row in recs if row.get("recommendation_type") == "relationship_action"), None)
    tier_progress = snapshot["tier_progress"]
    capital_brief = build_daily_capital_brief({
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

    # Augment with persisted strategy data if available.
    persisted_strategy = get_active_strategy(user_id, tenant_id)
    strategy_brief = build_hermes_strategy_brief(user_id, tenant_id, strategy=persisted_strategy)

    capital_brief["strategy_brief"] = strategy_brief
    capital_brief["next_best_action"] = strategy_brief.get("next_best_action")
    capital_brief["estimated_funding_low"] = strategy_brief.get("estimated_funding_low")
    capital_brief["estimated_funding_high"] = strategy_brief.get("estimated_funding_high")
    capital_brief["current_phase"] = strategy_brief.get("current_phase")
    return capital_brief
