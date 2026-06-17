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


def connector_status(*, check_network: bool = False) -> dict[str, Any]:
    """Resolve connector readiness via lib.social_connection_resolver.

    The resolver maps the real Meta connection (META_PAGE_ID / META_PAGE_ACCESS_TOKEN /
    META_INSTAGRAM_ACCOUNT_ID — the names content_employee/publisher.py already uses) as
    aliases for the FACEBOOK_PAGE_ID / INSTAGRAM_BUSINESS_ID names the new automation
    originally hard-coded. Never returns raw token values.
    """
    from lib import social_connection_resolver as resolver

    fb = resolver.resolve("facebook", check_network=check_network)
    ig = resolver.resolve("instagram", check_network=check_network)

    postiz_url_present = env_state("POSTIZ_URL")["present"]
    postiz_key_present = env_state("POSTIZ_API_KEY")["present"]
    postiz_ready = postiz_url_present and postiz_key_present
    postiz_blockers = []
    if not postiz_url_present:
        postiz_blockers.append("POSTIZ_URL missing")
    if not postiz_key_present:
        postiz_blockers.append("POSTIZ_API_KEY missing")

    def _blockers(res: dict) -> list[str]:
        return [f"{m} missing" for m in res.get("missing_fields", [])]

    return {
        "postiz": {
            "status": "ready" if postiz_ready else "blocked",
            "account_connected": "yes" if postiz_ready else "no",
            "publishing_ready": "yes" if postiz_ready else "no",
            "url_present": postiz_url_present,
            "api_key_present": postiz_key_present,
            "network_checked": False,
            "blockers": postiz_blockers,
            "note": "Postiz is not configured for Nexus; Meta is connected directly via Graph API.",
        },
        "facebook": {
            "status": "ready" if fb["publishing_ready"] == "yes" else "blocked",
            "account_connected": fb["account_connected"],
            "publishing_ready": fb["publishing_ready"],
            "connection_source": fb["connection_source"],
            "page_id_present": fb["page_id_present"] == "yes",
            "page_id_alias": fb["id_matched_alias"],
            "token_present": fb["token_present"] == "yes",
            "token_alias": fb["token_matched_alias"],
            "token_not_printed": True,
            "permission_check_done": fb["permission_check_done"],
            "permission_check": fb["permission_check"],
            "network_checked": check_network,
            "missing_fields": fb["missing_fields"],
            "blockers": _blockers(fb),
        },
        "instagram": {
            "status": "ready" if ig["publishing_ready"] == "yes" else "blocked",
            "account_connected": ig["account_connected"],
            "publishing_ready": ig["publishing_ready"],
            "connection_source": ig["connection_source"],
            "instagram_account_id_present": ig["ig_business_id_present"] == "yes",
            "business_id_present": ig["ig_business_id_present"] == "yes",
            "instagram_account_id_alias": ig["id_matched_alias"],
            "token_present": ig["token_present"] == "yes",
            "token_alias": ig["token_matched_alias"],
            "token_not_printed": True,
            "permission_check_done": ig["permission_check_done"],
            "permission_check": ig["permission_check"],
            "network_checked": check_network,
            "missing_fields": ig["missing_fields"],
            "media_flow_implemented": False,
            "media_requirements": "Instagram feed/Reels publishing requires the media/container workflow (upload -> create container -> poll status -> media_publish). content_employee/publisher.py implements this; the social_queue dry-run path does not publish.",
            "blockers": _blockers(ig),
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
        # Attach real connector readiness (resolved from existing Meta connection) so the
        # receipt reflects whether a real publish would be gated. Tokens are never included.
        platform = item.get("platform")
        conn = connector_status().get(platform, {}) if platform in {"facebook", "instagram"} else {}
        connector_summary = {
            "account_connected": conn.get("account_connected"),
            "publishing_ready": conn.get("publishing_ready"),
            "connection_source": conn.get("connection_source"),
            "connector_blockers": conn.get("blockers"),
        } if conn else {}
        receipt = {
            "item_id": item.get("id"),
            "platform": platform,
            "caption_preview": str(item.get("caption") or "")[:240],
            "content_path": item.get("content_path"),
            "dry_run": True,
            "would_publish": False,
            "blockers": blockers,
            "connector": connector_summary,
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
