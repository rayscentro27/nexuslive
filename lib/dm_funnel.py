from __future__ import annotations

import os

from lib.growth_support import safe_insert, stable_code

DM_AUTO_SEND = os.getenv("DM_AUTO_SEND", "false").lower() == "true"
DM_REQUIRE_APPROVAL = os.getenv("DM_REQUIRE_APPROVAL", "true").lower() == "true"


def build_dm_draft(handle: str, platform: str, intent_category: str, content_topic: str) -> dict:
    intro = {
        "credit_help": "The first step is usually becoming fundable before applying.",
        "business_setup": "A clean setup often matters more than people expect.",
        "funding": "Funding timing is usually where most people get tripped up.",
        "grants": "Grant readiness usually starts with clean business paperwork.",
        "trading": "Education and risk management come before expectations.",
        "general_interest": "The best next step is usually clarity on setup, timing, and goals.",
    }.get(intent_category, "The best next step is getting the fundamentals right first.")
    return {
        "handle": handle,
        "platform": platform,
        "intent_category": intent_category,
        "content_topic": content_topic,
        "draft_text": f"Thanks for reaching out. {intro} If you want, I can help you narrow down the right next step for {content_topic}.",
        "status": "draft_pending_approval",
        "auto_send_enabled": DM_AUTO_SEND,
        "requires_approval": DM_REQUIRE_APPROVAL,
    }


def save_dm_draft(handle: str, platform: str, intent_category: str, content_topic: str) -> dict:
    lead = safe_insert("dm_leads", {
        "handle": handle,
        "platform": platform,
        "content_topic": content_topic,
        "intent_category": intent_category,
        "status": "draft_pending_approval",
    })
    draft = build_dm_draft(handle, platform, intent_category, content_topic)
    if not lead.get("ok") or not lead.get("rows"):
        return {"ok": False, "error": lead.get("error", "lead_create_failed"), "draft": draft}
    lead_id = lead["rows"][0]["id"]
    seq = safe_insert("dm_sequences", {
        "lead_id": lead_id,
        "sequence_name": stable_code("dm", f"{handle}:{intent_category}"),
        "status": "draft_pending_approval",
    })
    seq_id = seq["rows"][0]["id"] if seq.get("ok") and seq.get("rows") else None
    msg = safe_insert("dm_messages", {
        "sequence_id": seq_id,
        "message_order": 1,
        "draft_text": draft["draft_text"],
        "status": "draft_pending_approval",
    })
    return {"ok": msg.get("ok", False), "lead": lead, "sequence": seq, "message": msg, "draft": draft}
