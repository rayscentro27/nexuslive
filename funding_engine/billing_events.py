from __future__ import annotations

from typing import Any

from funding_engine.constants import DISCLAIMER
from funding_engine.referral_rewards import create_referral_earning_if_eligible
from lib.growth_support import safe_insert


def build_application_result(
    *,
    tenant_id: str | None,
    user_id: str,
    recommendation_id: str | None,
    result_status: str,
    approved_amount: float | int | None,
    proof_url: str | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "recommendation_id": recommendation_id,
        "result_status": result_status,
        "approved_amount": approved_amount or 0,
        "proof_url": proof_url,
        "verified": verified,
    }


def build_success_fee_invoice(
    *,
    tenant_id: str | None,
    user_id: str,
    application_result_id: str,
    funding_amount: float | int,
    fee_rate: float = 0.10,
) -> dict[str, Any]:
    funding_amount = float(funding_amount or 0)
    fee_rate = float(fee_rate or 0.10)
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "application_result_id": application_result_id,
        "funding_amount": funding_amount,
        "fee_rate": fee_rate,
        "invoice_amount": round(funding_amount * fee_rate, 2),
        "status": "pending",
    }


def record_application_result(
    *,
    tenant_id: str | None,
    user_id: str,
    recommendation_id: str | None,
    result_status: str,
    approved_amount: float | int | None,
    proof_url: str | None = None,
    verified: bool = False,
) -> dict[str, Any]:
    result_payload = build_application_result(
        tenant_id=tenant_id,
        user_id=user_id,
        recommendation_id=recommendation_id,
        result_status=result_status,
        approved_amount=approved_amount,
        proof_url=proof_url,
        verified=verified,
    )
    created = safe_insert("application_results", result_payload)
    response = {
        "ok": created.get("ok", False),
        "application_result": (created.get("rows") or [None])[0],
        "invoice": None,
        "referral_earning": None,
        "disclaimer": DISCLAIMER,
    }
    if not created.get("ok"):
        response["error"] = created.get("error")
        return response

    app_result = response["application_result"] or {}
    amount = float(approved_amount or 0)
    if amount > 0:
        invoice_payload = build_success_fee_invoice(
            tenant_id=tenant_id,
            user_id=user_id,
            application_result_id=app_result.get("id"),
            funding_amount=amount,
        )
        invoice = safe_insert("success_fee_invoices", invoice_payload)
        response["invoice"] = (invoice.get("rows") or [None])[0]
        referral = create_referral_earning_if_eligible(
            referred_user_id=user_id,
            application_result_id=app_result.get("id"),
            funding_amount=amount,
            platform_fee=invoice_payload["invoice_amount"],
        )
        response["referral_earning"] = referral.get("earning")
    try:
        from funding_engine.service import create_or_refresh_user_recommendations

        response["recommendation_refresh"] = create_or_refresh_user_recommendations(
            user_id=user_id,
            tenant_id=tenant_id,
            reason="application_result_submitted",
            force=False,
        ).get("refresh")
    except Exception as exc:
        response["recommendation_refresh_error"] = str(exc)
    return response
