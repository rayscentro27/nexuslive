from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
QUEUE_PATH = ROOT / "outputs" / "social_queue" / "social_queue.jsonl"
RECEIPT_DIR = ROOT / "logs" / "social_publish_receipts"
REPORT_DIR = ROOT / "reports" / "social"

VALID_PLATFORMS = {"facebook", "instagram", "newsletter"}
VALID_STATUSES = {
    "draft",
    "queued_for_review",
    "queued_for_publish",
    "approved",
    "dry_run_ready",
    "published",
    "failed",
    "failed_retry_allowed",
    "blocked",
    "needs_revision",
    "blocked_compliance",
    "rejected",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(platform: str, title: str, caption: str, content_path: str) -> str:
    seed = "|".join([platform, title, caption, content_path, now_utc()])
    return "social_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def ensure_dirs() -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_items() -> list[dict[str, Any]]:
    if not QUEUE_PATH.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in QUEUE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            items.append(item)
    return items


def save_items(items: list[dict[str, Any]]) -> None:
    ensure_dirs()
    QUEUE_PATH.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in items),
        encoding="utf-8",
    )


def find_item(item_id: str) -> dict[str, Any] | None:
    return next((item for item in load_items() if item.get("id") == item_id), None)


def validate_item_fields(item: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if item.get("platform") not in VALID_PLATFORMS:
        blockers.append("unknown platform")
    if not str(item.get("caption") or "").strip():
        blockers.append("caption is empty")
    if not str(item.get("content_path") or "").strip():
        blockers.append("content_path is empty")
    if not str(item.get("cta") or "").strip():
        blockers.append("cta is empty")
    return blockers


def create_item(
    *,
    platform: str,
    channel: str = "",
    offer: str,
    title: str,
    caption: str,
    content_path: str,
    media_path: str = "",
    cta: str,
    source: str = "manual",
    source_report: str = "",
    scheduled_for: str = "",
    status: str = "queued_for_review",
    quality_score: int | None = None,
    quality_pass: bool | None = None,
    compliance_pass: bool | None = None,
    banned_claims_found: list[str] | None = None,
    needs_revision_reason: str = "",
) -> dict[str, Any]:
    if platform not in VALID_PLATFORMS:
        raise ValueError(f"invalid platform: {platform}")
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status: {status}")
    created_at = now_utc()
    item = {
        "id": stable_id(platform, title, caption, content_path),
        "created_at": created_at,
        "updated_at": created_at,
        "platform": platform,
        "channel": channel,
        "offer": offer,
        "title": title,
        "caption": caption,
        "content_path": content_path,
        "media_path": media_path,
        "cta": cta,
        "status": status,
        "publish_intent": False,
        "approved_by_ray": False,
        "approved_at": "",
        "scheduled_for": scheduled_for,
        "source": source,
        "source_report": source_report,
        "publish_result": {},
        "receipt_path": "",
        "quality_score": quality_score,
        "quality_pass": quality_pass,
        "compliance_pass": compliance_pass,
        "banned_claims_found": banned_claims_found or [],
        "needs_revision_reason": needs_revision_reason,
    }
    blockers = validate_item_fields(item)
    if banned_claims_found:
        item["status"] = "blocked_compliance"
        item["publish_result"] = {"blockers": ["banned compliance claim found"]}
    elif quality_score is not None and quality_score < 75:
        item["status"] = "needs_revision"
        item["needs_revision_reason"] = needs_revision_reason or "quality score below 75"
    elif quality_pass is False or compliance_pass is False:
        item["status"] = "needs_revision" if compliance_pass is not False else "blocked_compliance"
        item["needs_revision_reason"] = needs_revision_reason or "quality/compliance gate did not pass"
    if blockers:
        item["status"] = "blocked"
        item["publish_result"] = {"blockers": blockers}
    items = load_items()
    items.append(item)
    save_items(items)
    return item


def update_item(item_id: str, **updates: Any) -> dict[str, Any]:
    items = load_items()
    for idx, item in enumerate(items):
        if item.get("id") == item_id:
            merged = dict(item)
            merged.update(updates)
            merged["updated_at"] = now_utc()
            if merged.get("status") not in VALID_STATUSES:
                raise ValueError(f"invalid status: {merged.get('status')}")
            items[idx] = merged
            save_items(items)
            return merged
    raise KeyError(f"queue item not found: {item_id}")


def write_receipt(kind: str, item_id: str, payload: dict[str, Any]) -> str:
    ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RECEIPT_DIR / f"{ts}_{kind}_{item_id}.json"
    body = {"kind": kind, "item_id": item_id, "created_at": now_utc(), **payload}
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return _rel(path)


def approve_item(item_id: str, *, ray_approved: bool) -> dict[str, Any]:
    if not ray_approved:
        raise PermissionError("--ray-approved is required")
    item = find_item(item_id)
    if not item:
        raise KeyError(f"queue item not found: {item_id}")
    blockers = validate_item_fields(item)
    if blockers:
        raise ValueError("; ".join(blockers))
    approved_at = now_utc()
    receipt_path = write_receipt(
        "approval",
        item_id,
        {"approved_by_ray": True, "approved_at": approved_at, "published": False},
    )
    return update_item(
        item_id,
        approved_by_ray=True,
        approved_at=approved_at,
        status="approved",
        receipt_path=receipt_path,
    )


def reject_item(item_id: str, reason: str) -> dict[str, Any]:
    if not reason.strip():
        raise ValueError("reason is required")
    receipt_path = write_receipt("rejection", item_id, {"reason": reason, "published": False})
    return update_item(
        item_id,
        status="rejected",
        publish_result={"rejected": True, "reason": reason},
        receipt_path=receipt_path,
    )


def summarize(items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    items = load_items() if items is None else items
    counts = {status: 0 for status in sorted(VALID_STATUSES)}
    by_platform: dict[str, int] = {}
    last_published: dict[str, Any] | None = None
    for item in items:
        status = item.get("status") or "unknown"
        counts[status] = counts.get(status, 0) + 1
        platform = item.get("platform") or "unknown"
        by_platform[platform] = by_platform.get(platform, 0) + 1
        if status == "published":
            last_published = item
    next_action = "Queue a social post for Ray review."
    if counts.get("queued_for_review", 0):
        next_action = "Ray reviews and approves the next queued post; run dry-run before any real publish."
    elif counts.get("approved", 0) or counts.get("dry_run_ready", 0) or counts.get("queued_for_publish", 0):
        next_action = "Run a dry-run or publish only after Ray approves the exact post/account."
    elif counts.get("failed", 0) or counts.get("blocked", 0):
        next_action = "Review failed/blocked receipts before retrying."
    last_result = (last_published or {}).get("publish_result") or {}
    return {
        "queue_path": _rel(QUEUE_PATH),
        "total": len(items),
        "counts": counts,
        "by_platform": by_platform,
        "pending_review_count": counts.get("queued_for_review", 0),
        "approved_count": counts.get("approved", 0),
        "dry_run_ready_count": counts.get("dry_run_ready", 0),
        "published_count": counts.get("published", 0),
        "failed_count": counts.get("failed", 0),
        "blocked_count": counts.get("blocked", 0),
        "needs_revision_count": counts.get("needs_revision", 0),
        "blocked_compliance_count": counts.get("blocked_compliance", 0),
        "queued_for_publish_count": counts.get("queued_for_publish", 0),
        "failed_retry_allowed_count": counts.get("failed_retry_allowed", 0),
        "average_quality_score": round(
            sum(int(item.get("quality_score") or 0) for item in items if item.get("quality_score") is not None)
            / max(1, sum(1 for item in items if item.get("quality_score") is not None)),
            1,
        ),
        "next_recommended_action": next_action,
        "last_published": {
            "id": (last_published or {}).get("id"),
            "platform": (last_published or {}).get("platform"),
            "title": (last_published or {}).get("title"),
            "post_id": last_result.get("post_id"),
            "permalink": last_result.get("permalink"),
            "receipt_path": (last_published or {}).get("receipt_path"),
        } if last_published else None,
        "latest_items": items[-10:],
    }


def write_status_reports(connector_status: dict[str, Any] | None = None) -> dict[str, str]:
    summary = summarize()
    if connector_status is not None:
        summary["connector_status"] = connector_status
    ensure_dirs()
    json_path = REPORT_DIR / "social_queue_status_latest.json"
    md_path = REPORT_DIR / "social_queue_status_latest.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Social Queue Status - Latest",
        "",
        f"- Total: {summary['total']}",
        f"- Pending review: {summary['pending_review_count']}",
        f"- Approved: {summary['approved_count']}",
        f"- Dry-run ready: {summary['dry_run_ready_count']}",
        f"- Queued for publish: {summary['queued_for_publish_count']}",
        f"- Published: {summary['published_count']}",
        f"- Failed: {summary['failed_count']}",
        f"- Blocked: {summary['blocked_count']}",
        f"- Needs revision: {summary['needs_revision_count']}",
        f"- Blocked compliance: {summary['blocked_compliance_count']}",
        f"- Average quality score: {summary['average_quality_score']}",
        f"- Next recommended action: {summary['next_recommended_action']}",
        "",
        "## Last Published",
    ]
    last = summary.get("last_published")
    if last:
        lines += [
            f"- Item: {last.get('id')}",
            f"- Post ID: {last.get('post_id')}",
            f"- Permalink: {last.get('permalink')}",
            f"- Receipt: {last.get('receipt_path')}",
            "",
        ]
    else:
        lines += ["- None", ""]
    lines += [
        "## Latest Items",
    ]
    for item in summary["latest_items"]:
        lines.append(
            f"- {item.get('id')} | {item.get('platform')} | {item.get('status')} | {item.get('title')}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"json": _rel(json_path), "markdown": _rel(md_path)}
