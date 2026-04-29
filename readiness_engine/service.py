"""
service.py — Client Readiness Engine service layer.

Handles data fetching, profile upserts, score calculation,
task generation, and integration triggers.

Endpoints served by the control_center_server Flask app:
  GET  /api/readiness/profile
  POST /api/readiness/business-foundation
  POST /api/readiness/credit-profile
  POST /api/readiness/banking
  POST /api/readiness/grants
  POST /api/readiness/trading
  GET  /api/readiness/tasks
  POST /api/readiness/tasks/:id/complete
  POST /api/readiness/recalculate
"""
from __future__ import annotations

import urllib.parse
from typing import Any

from lib.growth_support import safe_insert, safe_patch
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
from readiness_engine.task_generation import generate_all_tasks, get_next_best_action
from scripts.prelaunch_utils import rest_select, table_exists, utc_now_iso


def _q(value: str | None) -> str:
    return urllib.parse.quote(str(value or ""), safe="")


def _safe_select(path: str) -> list[dict[str, Any]]:
    try:
        return rest_select(path) or []
    except Exception:
        return []


# ── Profile fetchers ──────────────────────────────────────────────────────────

def get_business_foundation(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("business_foundation_profiles?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_credit_profile(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("credit_profile_inputs?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_banking_profile(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("banking_setup_profiles?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_grant_profile(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("grant_eligibility_profiles?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_trading_profile(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("trading_eligibility_profiles?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_readiness_profile(user_id: str, tenant_id: str | None = None) -> dict[str, Any] | None:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    rows = _safe_select("client_readiness_profiles?select=*&order=updated_at.desc&limit=1&" + "&".join(filters))
    return rows[0] if rows else None


def get_readiness_tasks(user_id: str, tenant_id: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    filters = [f"user_id=eq.{_q(user_id)}"]
    if tenant_id:
        filters.append(f"tenant_id=eq.{_q(tenant_id)}")
    if status:
        filters.append(f"status=eq.{_q(status)}")
    return _safe_select("readiness_tasks?select=*&order=priority.asc,created_at.asc&" + "&".join(filters))


# ── Score calculation ─────────────────────────────────────────────────────────

def build_readiness_snapshot(user_id: str, tenant_id: str | None = None) -> dict[str, Any]:
    foundation_data = get_business_foundation(user_id, tenant_id) or {}
    credit_data = get_credit_profile(user_id, tenant_id) or {}
    banking_data = get_banking_profile(user_id, tenant_id) or {}
    grant_data = get_grant_profile(user_id, tenant_id) or {}
    trading_data = get_trading_profile(user_id, tenant_id) or {}

    foundation_score = score_business_foundation(foundation_data)["score"]
    credit_score = score_credit_profile(credit_data)["score"]
    banking_score = score_banking_setup(banking_data)["score"]
    grant_score = score_grant_eligibility(grant_data)["score"]
    trading_score = score_trading_eligibility(trading_data)["score"]

    overall = calculate_overall_readiness_score(
        foundation_score, credit_score, banking_score, grant_score, trading_score
    )

    completion = overall_profile_completion(
        business_foundation_completion(foundation_data),
        credit_profile_completion(credit_data),
        banking_setup_completion(banking_data),
        grant_eligibility_completion(grant_data),
        trading_eligibility_completion(trading_data),
    )

    tasks = generate_all_tasks(foundation_data, credit_data, banking_data, grant_data, trading_data)
    next_action = get_next_best_action(tasks)

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "overall_score": overall["score"],
        "score_breakdown": overall["breakdown"],
        "completion": completion,
        "tasks": tasks,
        "next_best_action": next_action,
        "grant_ready": is_grant_ready(grant_data),
        "trading_eligible": is_trading_eligible(trading_data),
        "generated_at": utc_now_iso(),
        "note": overall["note"],
    }


def _upsert_readiness_profile(
    user_id: str,
    tenant_id: str | None,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if not table_exists("client_readiness_profiles"):
        return {"ok": False, "error": "table_missing:client_readiness_profiles"}

    existing = get_readiness_profile(user_id, tenant_id)
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "overall_score": snapshot["overall_score"],
        "score_breakdown": snapshot["score_breakdown"],
        "completion_pct": snapshot["completion"]["overall_pct"],
        "grant_ready": snapshot["grant_ready"],
        "trading_eligible": snapshot["trading_eligible"],
        "updated_at": utc_now_iso(),
    }
    if existing:
        return safe_patch(
            f"client_readiness_profiles?user_id=eq.{_q(user_id)}"
            + (f"&tenant_id=eq.{_q(tenant_id)}" if tenant_id else ""),
            payload,
        )
    payload["created_at"] = utc_now_iso()
    return safe_insert("client_readiness_profiles", payload)


def _persist_tasks(
    user_id: str,
    tenant_id: str | None,
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    if not table_exists("readiness_tasks"):
        return {"ok": False, "error": "table_missing:readiness_tasks", "saved": 0}

    saved = 0
    for task in tasks:
        payload = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "category": task.get("category"),
            "task_type": task.get("task_type"),
            "task_title": task.get("task_title"),
            "task_description": task.get("task_description"),
            "guidance_content": task.get("guidance_content"),
            "execution_tools": task.get("execution_tools"),
            "education_notes": task.get("education_notes"),
            "status": task.get("status", "pending"),
            "priority": task.get("priority"),
            "unlocks_feature": task.get("unlocks_feature"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        result = safe_insert("readiness_tasks", payload)
        if result.get("ok"):
            saved += 1
    return {"ok": True, "saved": saved}


# ── Integration triggers ──────────────────────────────────────────────────────

def _trigger_funding_refresh(user_id: str, tenant_id: str | None, reason: str) -> None:
    try:
        from funding_engine.service import queue_recommendation_refresh
        queue_recommendation_refresh(
            user_id=user_id,
            tenant_id=tenant_id,
            reason=reason,
        )
    except Exception:
        pass


def _trigger_relationship_refresh(user_id: str, tenant_id: str | None) -> None:
    pass


# ── Profile upsert handlers ───────────────────────────────────────────────────

def _upsert_section(
    table: str,
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
    fetch_fn: Any,
) -> dict[str, Any]:
    if not table_exists(table):
        return {"ok": False, "error": f"table_missing:{table}"}
    existing = fetch_fn(user_id, tenant_id)
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        **{k: v for k, v in data.items() if k not in {"id", "user_id", "tenant_id", "created_at"}},
        "updated_at": utc_now_iso(),
    }
    if existing:
        return safe_patch(
            f"{table}?user_id=eq.{_q(user_id)}" + (f"&tenant_id=eq.{_q(tenant_id)}" if tenant_id else ""),
            payload,
        )
    payload["created_at"] = utc_now_iso()
    return safe_insert(table, payload)


def save_business_foundation(
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    result = _upsert_section("business_foundation_profiles", user_id, tenant_id, data, get_business_foundation)
    if result.get("ok"):
        _trigger_funding_refresh(user_id, tenant_id, "business_foundation_updated")
    return result


def save_credit_profile(
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    result = _upsert_section("credit_profile_inputs", user_id, tenant_id, data, get_credit_profile)
    if result.get("ok"):
        _trigger_funding_refresh(user_id, tenant_id, "credit_profile_updated")
    return result


def save_banking_profile(
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    result = _upsert_section("banking_setup_profiles", user_id, tenant_id, data, get_banking_profile)
    if result.get("ok"):
        _trigger_relationship_refresh(user_id, tenant_id)
        _trigger_funding_refresh(user_id, tenant_id, "banking_setup_updated")
    return result


def save_grant_profile(
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    return _upsert_section("grant_eligibility_profiles", user_id, tenant_id, data, get_grant_profile)


def save_trading_profile(
    user_id: str,
    tenant_id: str | None,
    data: dict[str, Any],
) -> dict[str, Any]:
    return _upsert_section("trading_eligibility_profiles", user_id, tenant_id, data, get_trading_profile)


def complete_task(task_id: str) -> dict[str, Any]:
    if not table_exists("readiness_tasks"):
        return {"ok": False, "error": "table_missing:readiness_tasks"}
    return safe_patch(
        f"readiness_tasks?id=eq.{_q(task_id)}",
        {"status": "completed", "updated_at": utc_now_iso()},
    )


# ── Full recalculation ────────────────────────────────────────────────────────

def recalculate_readiness(
    user_id: str,
    tenant_id: str | None = None,
    persist_tasks: bool = True,
) -> dict[str, Any]:
    snapshot = build_readiness_snapshot(user_id, tenant_id)
    profile_result = _upsert_readiness_profile(user_id, tenant_id, snapshot)
    tasks_result: dict[str, Any] = {"ok": True, "saved": 0}
    if persist_tasks:
        tasks_result = _persist_tasks(user_id, tenant_id, snapshot["tasks"])
    return {
        "snapshot": snapshot,
        "profile_saved": profile_result.get("ok", False),
        "tasks_saved": tasks_result.get("saved", 0),
    }
