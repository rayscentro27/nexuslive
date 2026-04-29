from __future__ import annotations

import os

from lib.growth_support import safe_insert

INFLUENCER_AUTO_SEND = os.getenv("INFLUENCER_AUTO_SEND", "false").lower() == "true"
INFLUENCER_REQUIRE_APPROVAL = os.getenv("INFLUENCER_REQUIRE_APPROVAL", "true").lower() == "true"


def build_outreach_draft(handle: str, niche: str, platform: str) -> dict:
    draft = (
        f"Hi {handle}, I like how you explain {niche} in a practical way. "
        "We are building education-first content around business readiness and would love to explore a simple, audience-first collaboration idea."
    )
    return {
        "handle": handle,
        "platform": platform,
        "niche": niche,
        "draft_text": draft,
        "status": "draft_pending_approval",
        "auto_send_enabled": INFLUENCER_AUTO_SEND,
        "requires_approval": INFLUENCER_REQUIRE_APPROVAL,
    }


def save_outreach_draft(handle: str, niche: str, platform: str, audience_size: int = 0) -> dict:
    prospect = safe_insert("influencer_prospects", {
        "handle": handle,
        "platform": platform,
        "niche": niche,
        "audience_size": audience_size,
        "status": "draft_prospect",
    })
    if not prospect.get("ok") or not prospect.get("rows"):
        return {"ok": False, "error": prospect.get("error", "prospect_create_failed")}
    prospect_id = prospect["rows"][0]["id"]
    draft = build_outreach_draft(handle, niche, platform)
    msg = safe_insert("influencer_outreach_messages", {
        "prospect_id": prospect_id,
        "draft_text": draft["draft_text"],
        "status": "draft_pending_approval",
    })
    return {"ok": msg.get("ok", False), "prospect": prospect, "message": msg, "draft": draft}
