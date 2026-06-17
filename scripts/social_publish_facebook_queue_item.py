#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import social_queue  # noqa: E402
from lib import social_connection_resolver as resolver  # noqa: E402


GRAPH_BASE = "https://graph.facebook.com/v19.0"
EXPECTED_PAGE_ID = "131069194210954"
EXPECTED_PAGE_NAME = "Clear Credentials"
ALLOWED_REAL_STATUSES = {"approved", "dry_run_ready", "queued_for_publish", "failed_retry_allowed"}


def load_dotenv_defaults() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(errors="ignore").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        os.environ.setdefault(key.replace("export ", "").strip(), value.strip().strip('"').strip("'"))


def ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def redact(text: str, token: str | None = None) -> str:
    out = text or ""
    if token:
        out = out.replace(token, "<redacted-token>")
    return out[:800]


def post_specific_id(post_id: str) -> str:
    if "_" in post_id:
        return post_id.split("_", 1)[1]
    return post_id


def permalink(page_id: str, post_id: str) -> str:
    return f"https://www.facebook.com/{page_id}/posts/{post_specific_id(post_id)}"


def identity_check(page_id: str, token: str) -> dict[str, Any]:
    url = (
        f"{GRAPH_BASE}/{urllib.parse.quote(page_id)}"
        f"?fields=id,name&access_token={urllib.parse.quote(token)}"
    )
    try:
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "nexus-facebook-queue-publisher"})
        with urllib.request.urlopen(req, timeout=15, context=ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        return {"ok": True, "id": data.get("id"), "name": data.get("name")}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return {"ok": False, "error": redact(f"HTTP {exc.code}: {body}", token)}
    except Exception as exc:
        return {"ok": False, "error": redact(str(exc), token)}


def graph_publish(page_id: str, token: str, caption: str) -> dict[str, Any]:
    data = urllib.parse.urlencode({"message": caption, "access_token": token}).encode("utf-8")
    req = urllib.request.Request(
        f"{GRAPH_BASE}/{urllib.parse.quote(page_id)}/feed",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "nexus-facebook-queue-publisher",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context()) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
        return {"ok": bool(payload.get("id")), "post_id": payload.get("id"), "raw_ok": True}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        return {"ok": False, "error": redact(f"HTTP {exc.code}: {body}", token)}
    except Exception as exc:
        return {"ok": False, "error": redact(str(exc), token)}


def safety_flags(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "instagram_disabled": True,
        "media_uploads_disabled": True,
        "postiz_disabled": True,
        "auto_retry_disabled": True,
        "auto_publish_disabled": True,
        "requires_ray_approval": True,
        "requires_confirm_real_publish": True,
        "token_not_printed": True,
        "dry_run_default": True,
        "allow_duplicate_test": bool(args.allow_duplicate_test),
    }


def validate_item(item: dict[str, Any], *, real_publish: bool, allow_duplicate_test: bool) -> list[str]:
    blockers = []
    if item.get("platform") != "facebook":
        blockers.append("platform is not facebook")
    if item.get("platform") != "facebook" and (
        item.get("instagram_business_id") or item.get("ig_user_id") or item.get("media_container_id")
    ):
        blockers.append("instagram fields present on non-facebook item")
    if not str(item.get("caption") or "").strip():
        blockers.append("caption is empty")
    if real_publish:
        if not item.get("approved_by_ray"):
            blockers.append("approved_by_ray is not true")
        if item.get("status") not in ALLOWED_REAL_STATUSES:
            blockers.append(f"status {item.get('status')} is not allowed for real publish")
        if item.get("status") == "published" and not allow_duplicate_test:
            blockers.append("item is already published; duplicate real publish refused")
        if item.get("quality_score") is not None and int(item.get("quality_score") or 0) < 75:
            blockers.append("quality_score below threshold")
        if item.get("banned_claims_found"):
            blockers.append("banned compliance claims found")
        if item.get("compliance_pass") is False:
            blockers.append("compliance_pass is false")
    return blockers


def write_result_receipt(
    *,
    item: dict[str, Any],
    kind: str,
    dry_run: bool,
    real_publish: bool,
    success: bool,
    page_id: str | None,
    page_name: str | None,
    post_id: str | None = None,
    graph_error_redacted: str | None = None,
    blockers: list[str] | None = None,
    queue_status_after: str | None = None,
    args: argparse.Namespace,
) -> str:
    receipt = {
        "item_id": item.get("id"),
        "platform": item.get("platform"),
        "page_id": page_id,
        "page_name": page_name,
        "caption_preview": str(item.get("caption") or "")[:240],
        "attempted_at": social_queue.now_utc(),
        "dry_run": dry_run,
        "real_publish": real_publish,
        "success": success,
        "post_id": post_id,
        "permalink": permalink(page_id, post_id) if page_id and post_id else None,
        "graph_error_redacted": graph_error_redacted,
        "blockers": blockers or [],
        "token_not_printed": True,
        "queue_status_after": queue_status_after,
        "safety_flags": safety_flags(args),
    }
    return social_queue.write_receipt(kind, str(item.get("id")), receipt)


def main() -> int:
    load_dotenv_defaults()
    ap = argparse.ArgumentParser(description="Publish a Facebook text post directly from an approved social queue item.")
    ap.add_argument("--item-id", required=True)
    ap.add_argument("--dry-run", action="store_true", help="validate and write a dry-run receipt only")
    ap.add_argument("--confirm-real-publish", action="store_true", help="required for real Facebook publishing")
    ap.add_argument("--allow-duplicate-test", action="store_true", help="explicitly allow duplicate testing of a published item")
    args = ap.parse_args()

    item = social_queue.find_item(args.item_id)
    if not item:
        raise SystemExit(f"queue item not found: {args.item_id}")

    real_publish = bool(args.confirm_real_publish and not args.dry_run)
    dry_run = not real_publish
    creds = resolver.facebook_page_credentials()
    page_id = creds.get("page_id")
    token = creds.get("token")
    blockers = validate_item(item, real_publish=real_publish, allow_duplicate_test=args.allow_duplicate_test)

    if page_id != EXPECTED_PAGE_ID:
        blockers.append(f"page ID does not match {EXPECTED_PAGE_ID}")
    if not token:
        blockers.append("META_PAGE_ACCESS_TOKEN/FACEBOOK page token missing")

    page_name = EXPECTED_PAGE_NAME
    identity = None
    if page_id and token:
        identity = identity_check(str(page_id), str(token))
        if not identity.get("ok"):
            blockers.append(f"page identity check failed: {identity.get('error')}")
        else:
            page_name = identity.get("name") or page_name
            if identity.get("id") != EXPECTED_PAGE_ID or identity.get("name") != EXPECTED_PAGE_NAME:
                blockers.append("page identity does not resolve to Clear Credentials / 131069194210954")

    if os.getenv("SOCIAL_PUBLISHING_ENABLED", "false").lower() != "true" and real_publish:
        blockers.append("SOCIAL_PUBLISHING_ENABLED=true required")
    if os.getenv("SOCIAL_DRY_RUN", "true").lower() != "false" and real_publish:
        blockers.append("SOCIAL_DRY_RUN=false required")
    if not args.confirm_real_publish and real_publish:
        blockers.append("--confirm-real-publish required")

    if dry_run:
        if item.get("status") == "published":
            blockers.append("item is already published; dry-run refuses duplicate real publish by default")
        receipt_path = write_result_receipt(
            item=item,
            kind="dry_run_facebook_queue",
            dry_run=True,
            real_publish=False,
            success=False,
            page_id=page_id,
            page_name=page_name,
            blockers=blockers,
            queue_status_after=item.get("status"),
            args=args,
        )
        result = {
            "ok": not blockers,
            "mode": "dry_run",
            "would_publish": False,
            "item_id": item.get("id"),
            "status": item.get("status"),
            "page_id": page_id,
            "page_name": page_name,
            "blockers": blockers,
            "receipt_path": receipt_path,
            "token_not_printed": True,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if not blockers or item.get("status") == "published" else 2

    if blockers:
        receipt_path = write_result_receipt(
            item=item,
            kind="failed_real_publish_facebook",
            dry_run=False,
            real_publish=True,
            success=False,
            page_id=page_id,
            page_name=page_name,
            graph_error_redacted="; ".join(blockers),
            blockers=blockers,
            queue_status_after="blocked",
            args=args,
        )
        social_queue.update_item(
            str(item.get("id")),
            status="blocked",
            publish_result={"published": False, "blockers": blockers, "token_not_printed": True},
            receipt_path=receipt_path,
        )
        print(json.dumps({"ok": False, "published": False, "blockers": blockers, "receipt_path": receipt_path}, indent=2))
        return 2

    published = graph_publish(str(page_id), str(token), str(item.get("caption") or ""))
    if published.get("ok"):
        post_id = published.get("post_id")
        result = {
            "item_id": item.get("id"),
            "platform": "facebook",
            "page_id": page_id,
            "page_name": page_name,
            "caption_preview": str(item.get("caption") or "")[:240],
            "post_id": post_id,
            "permalink": permalink(str(page_id), str(post_id)),
            "published": True,
            "published_at": social_queue.now_utc(),
            "real_publish_attempt": True,
            "token_not_printed": True,
            "token_type": "PAGE",
        }
        receipt_path = write_result_receipt(
            item=item,
            kind="real_publish_facebook",
            dry_run=False,
            real_publish=True,
            success=True,
            page_id=str(page_id),
            page_name=page_name,
            post_id=str(post_id),
            queue_status_after="published",
            args=args,
        )
        result["receipt_path"] = receipt_path
        social_queue.update_item(
            str(item.get("id")),
            status="published",
            publish_result=result,
            receipt_path=receipt_path,
        )
        print(json.dumps({"ok": True, "published": True, "post_id": post_id, "permalink": result["permalink"], "receipt_path": receipt_path}, indent=2))
        return 0

    error = published.get("error") or "Graph API publish failed"
    receipt_path = write_result_receipt(
        item=item,
        kind="failed_real_publish_facebook",
        dry_run=False,
        real_publish=True,
        success=False,
        page_id=page_id,
        page_name=page_name,
        graph_error_redacted=error,
        blockers=[error],
        queue_status_after="failed",
        args=args,
    )
    social_queue.update_item(
        str(item.get("id")),
        status="failed",
        publish_result={"published": False, "graph_error_redacted": error, "token_not_printed": True},
        receipt_path=receipt_path,
    )
    print(json.dumps({"ok": False, "published": False, "graph_error_redacted": error, "receipt_path": receipt_path}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
