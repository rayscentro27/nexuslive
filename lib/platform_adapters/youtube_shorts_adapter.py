from __future__ import annotations


def prepare_post(payload: dict) -> dict:
    return {"platform": "youtube_shorts", "mode": "manual", "ready": True, "payload": payload}
