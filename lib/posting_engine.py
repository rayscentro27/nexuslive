from __future__ import annotations

import os
from typing import Any

AUTO_POST_ENABLED = os.getenv("AUTO_POST_ENABLED", "false").lower() == "true"


def prepare_manual_post(variant_id: str, platform: str, content: dict[str, Any]) -> dict[str, Any]:
    return {
        "variant_id": variant_id,
        "platform": platform,
        "content": content,
        "status": "ready_to_post_manually",
        "would_post": False,
        "reason": "AUTO_POST_ENABLED=false",
    }
