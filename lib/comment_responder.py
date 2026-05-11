from __future__ import annotations

import os


COMMENT_AUTO_REPLY = os.getenv("COMMENT_AUTO_REPLY", "false").lower() == "true"
COMMENT_REQUIRE_APPROVAL = os.getenv("COMMENT_REQUIRE_APPROVAL", "true").lower() == "true"


def generate_comment_reply(comment_text: str, platform: str, content_topic: str) -> dict:
    text = (comment_text or "").lower()
    topic = content_topic or "business funding"
    if "fund" in text:
        reply = "Most people apply too early. The first step is becoming fundable first: credit profile, business setup, and funding timing."
    elif "credit" in text:
        reply = "Credit matters, but it is not the only factor. Lenders also look at business setup, profile consistency, and timing."
    elif "grant" in text:
        reply = "Grants usually work better when your business profile and paperwork are already organized before you apply."
    elif "trade" in text:
        reply = "Start with risk management and education first. Fast profit expectations usually create fast mistakes."
    else:
        reply = f"A strong first step with {topic} is getting the setup and timing right before pushing into applications."
    return {
        "platform": platform,
        "content_topic": topic,
        "reply": reply,
        "auto_reply_enabled": COMMENT_AUTO_REPLY,
        "requires_approval": COMMENT_REQUIRE_APPROVAL,
        "status": "draft_pending_approval" if COMMENT_REQUIRE_APPROVAL or not COMMENT_AUTO_REPLY else "ready",
    }
