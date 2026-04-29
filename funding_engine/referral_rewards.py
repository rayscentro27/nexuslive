from __future__ import annotations

import urllib.parse
from typing import Any

from funding_engine.constants import DISCLAIMER
from lib.growth_support import safe_insert
from scripts.prelaunch_utils import rest_select


def calculate_referral_amount(platform_fee: float | int, referral_rate: float = 0.02) -> float:
    return round(float(platform_fee or 0) * float(referral_rate or 0.02), 2)


def build_referral_earning(
    *,
    referrer_user_id: str,
    referred_user_id: str,
    application_result_id: str,
    funding_amount: float | int,
    platform_fee: float | int,
    referral_rate: float = 0.02,
) -> dict[str, Any]:
    return {
        "referrer_user_id": referrer_user_id,
        "referred_user_id": referred_user_id,
        "application_result_id": application_result_id,
        "funding_amount": float(funding_amount or 0),
        "platform_fee": float(platform_fee or 0),
        "referral_rate": float(referral_rate or 0.02),
        "referral_amount": calculate_referral_amount(platform_fee, referral_rate),
        "status": "pending",
    }


def find_active_referral(referred_user_id: str) -> dict[str, Any] | None:
    rows = rest_select(
        "referrals?select=id,referrer_user_id,referred_user_id,referral_code,status"
        f"&referred_user_id=eq.{urllib.parse.quote(referred_user_id, safe='')}"
        "&status=eq.active&limit=1"
    ) or []
    return rows[0] if rows else None


def create_referral_earning_if_eligible(
    *,
    referred_user_id: str,
    application_result_id: str,
    funding_amount: float | int,
    platform_fee: float | int,
) -> dict[str, Any]:
    referral = find_active_referral(referred_user_id)
    if not referral:
        return {"ok": True, "earning": None, "disclaimer": DISCLAIMER}

    payload = build_referral_earning(
        referrer_user_id=referral["referrer_user_id"],
        referred_user_id=referred_user_id,
        application_result_id=application_result_id,
        funding_amount=funding_amount,
        platform_fee=platform_fee,
    )
    created = safe_insert("referral_earnings", payload)
    return {
        "ok": created.get("ok", False),
        "earning": (created.get("rows") or [None])[0],
        "error": created.get("error"),
        "disclaimer": DISCLAIMER,
    }
