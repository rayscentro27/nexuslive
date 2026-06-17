from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from lib import social_queue


ROOT = Path(__file__).resolve().parent.parent


def _dotenv_value(name: str) -> str | None:
    for path in (ROOT / ".env", ROOT / ".env.example"):
        if not path.exists():
            continue
        try:
            for line in path.read_text(errors="ignore").splitlines():
                text = line.strip()
                if not text or text.startswith("#") or "=" not in text:
                    continue
                key, value = text.split("=", 1)
                key = key.replace("export ", "").strip()
                if key == name:
                    return value.strip().strip("\"").strip("'")
        except Exception:
            continue
    return None


def env_state(name: str) -> dict[str, Any]:
    val = os.getenv(name)
    source = "env"
    if val is None:
        val = _dotenv_value(name)
        source = ".env" if val is not None else "not_found"
    if val is None:
        return {"present": False, "empty": False, "placeholder": False, "source": source}
    text = val.strip()
    placeholder = text.lower() in {"changeme", "placeholder", "todo", "replace_me"} or "your_" in text.lower()
    return {"present": True, "empty": not bool(text), "placeholder": placeholder, "source": source}


def connector_status() -> dict[str, Any]:
    postiz_ready = all(env_state(k)["present"] and not env_state(k)["empty"] for k in ("POSTIZ_URL", "POSTIZ_API_KEY"))
    fb_token = env_state("META_PAGE_ACCESS_TOKEN")["present"] or env_state("FACEBOOK_ACCESS_TOKEN")["present"]
    fb_page_present = env_state("FACEBOOK_PAGE_ID")["present"]
    fb_ready = fb_page_present and fb_token
    ig_token = env_state("INSTAGRAM_ACCESS_TOKEN")["present"] or env_state("META_PAGE_ACCESS_TOKEN")["present"]
    ig_business_present = env_state("INSTAGRAM_BUSINESS_ID")["present"]
    ig_ready = ig_business_present and ig_token
    postiz_blockers = []
    if not env_state("POSTIZ_URL")["present"]:
        postiz_blockers.append("POSTIZ_URL missing")
    if not env_state("POSTIZ_API_KEY")["present"]:
        postiz_blockers.append("POSTIZ_API_KEY missing")
    facebook_blockers = []
    if not fb_page_present:
        facebook_blockers.append("FACEBOOK_PAGE_ID missing")
    if not fb_token:
        facebook_blockers.append("META_PAGE_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN missing")
    instagram_blockers = []
    if not ig_business_present:
        instagram_blockers.append("INSTAGRAM_BUSINESS_ID missing")
    if not ig_token:
        instagram_blockers.append("INSTAGRAM_ACCESS_TOKEN or META_PAGE_ACCESS_TOKEN missing")
    return {
        "postiz": {
            "status": "ready" if postiz_ready else "blocked",
            "url_present": env_state("POSTIZ_URL")["present"],
            "api_key_present": env_state("POSTIZ_API_KEY")["present"],
            "network_checked": False,
            "blockers": postiz_blockers,
        },
        "facebook": {
            "status": "ready" if fb_ready else "blocked",
            "page_id_present": fb_page_present,
            "token_present": fb_token,
            "network_checked": False,
            "blockers": facebook_blockers,
        },
        "instagram": {
            "status": "ready" if ig_ready else "blocked",
            "business_id_present": ig_business_present,
            "token_present": ig_token,
            "network_checked": False,
            "media_requirements": "Instagram publishing usually requires media/container workflow; text-only captions are not enough for feed/Reels.",
            "blockers": instagram_blockers,
        },
        "real_publish_enabled": os.getenv("SOCIAL_PUBLISHING_ENABLED", "false").lower() == "true",
        "dry_run": os.getenv("SOCIAL_DRY_RUN", "true").lower() != "false",
        "approval_required": os.getenv("SOCIAL_APPROVAL_REQUIRED", "true").lower() != "false",
    }


class DryRunPublisher:
    name = "dry_run"

    def publish(self, item: dict[str, Any]) -> dict[str, Any]:
        blockers = social_queue.validate_item_fields(item)
        if not item.get("approved_by_ray"):
            blockers.append("item is not approved_by_ray")
        if item.get("platform") == "instagram" and not item.get("media_path"):
            blockers.append("instagram real publishing would require media_path; dry-run only")
        receipt = {
            "item_id": item.get("id"),
            "platform": item.get("platform"),
            "caption_preview": str(item.get("caption") or "")[:240],
            "content_path": item.get("content_path"),
            "dry_run": True,
            "would_publish": False,
            "blockers": blockers,
        }
        receipt_path = social_queue.write_receipt("dry_run", str(item.get("id")), receipt)
        updated = social_queue.update_item(
            str(item.get("id")),
            status="dry_run_ready" if not blockers or blockers == ["instagram real publishing would require media_path; dry-run only"] else "blocked",
            publish_result=receipt,
            receipt_path=receipt_path,
        )
        return {"ok": True, "receipt_path": receipt_path, "item": updated, **receipt}


class _BlockedRealPublisher:
    name = "blocked"

    def __init__(self, connector: str):
        self.connector = connector

    def publish(self, item: dict[str, Any], *, confirm_real_publish: bool = False) -> dict[str, Any]:
        status = connector_status().get(self.connector, {})
        blockers = list(status.get("blockers") or [])
        if not confirm_real_publish:
            blockers.append("--confirm-real-publish required")
        if os.getenv("SOCIAL_PUBLISHING_ENABLED", "false").lower() != "true":
            blockers.append("SOCIAL_PUBLISHING_ENABLED=true required")
        if os.getenv("SOCIAL_DRY_RUN", "true").lower() != "false":
            blockers.append("SOCIAL_DRY_RUN=false required")
        if not item.get("approved_by_ray"):
            blockers.append("approved_by_ray=true required")
        receipt = {
            "item_id": item.get("id"),
            "connector": self.connector,
            "dry_run": False,
            "published": False,
            "blockers": blockers,
        }
        receipt_path = social_queue.write_receipt("blocked_real_publish", str(item.get("id")), receipt)
        return {"ok": False, "receipt_path": receipt_path, **receipt}


class PostizPublisher(_BlockedRealPublisher):
    def __init__(self):
        super().__init__("postiz")


class FacebookPublisher(_BlockedRealPublisher):
    def __init__(self):
        super().__init__("facebook")


class InstagramPublisher(_BlockedRealPublisher):
    def __init__(self):
        super().__init__("instagram")
