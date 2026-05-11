from __future__ import annotations


def prepare_post(payload: dict) -> dict:
    return {"platform": "instagram_reels", "mode": "manual", "ready": True, "payload": payload}
