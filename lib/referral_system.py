from __future__ import annotations

from lib.growth_support import safe_insert, stable_code


def build_referral_link(referrer_user_id: str, destination_url: str = "https://nexus.goclearonline.com/signup") -> dict:
    code = stable_code("ref", referrer_user_id)
    return {
        "referrer_user_id": referrer_user_id,
        "referral_code": code,
        "destination_url": f"{destination_url}?ref={code}",
        "status": "active",
    }


def save_referral_link(referrer_user_id: str, destination_url: str = "https://nexus.goclearonline.com/signup") -> dict:
    payload = build_referral_link(referrer_user_id, destination_url)
    return safe_insert("referral_links", payload, prefer="resolution=merge-duplicates,return=representation")
