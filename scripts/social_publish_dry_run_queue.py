#!/usr/bin/env python3
"""Create local social publishing dry-run queue items.

This script never publishes, never calls Meta/Postiz, and never reads credentials.
It records intent for Ray review only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "outputs" / "social_queue"
RECEIPT_DIR = ROOT / "logs" / "social_publish_dry_run"
VALID_PLATFORMS = {"facebook", "instagram", "newsletter"}
DEFAULT_SOURCE_REPORT = "reports/value_test/social_first_funnel_plan_20260617.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(platform: str, content_path: str, caption: str, cta: str, offer: str, created_at: str) -> str:
    seed = "|".join([platform, content_path, caption, cta, offer, created_at])
    return "social_dry_run_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_item(args: argparse.Namespace) -> dict:
    created_at = utc_now()
    item_id = stable_id(args.platform, args.content_path, args.caption, args.cta, args.offer, created_at)
    return {
        "id": item_id,
        "platform": args.platform,
        "offer": args.offer,
        "content_path": args.content_path,
        "caption": args.caption,
        "cta": args.cta,
        "publish_intent": False,
        "approved_by_ray": False,
        "status": "dry_run_queued_for_ray_review",
        "created_at": created_at,
        "source_report": args.source_report,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local social publishing dry-run queue item.")
    parser.add_argument("--platform", required=True, choices=sorted(VALID_PLATFORMS))
    parser.add_argument("--content-path", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--cta", required=True)
    parser.add_argument("--offer", default="Credit/Funding Readiness Starter Review - $97")
    parser.add_argument("--source-report", default=DEFAULT_SOURCE_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    item = build_item(args)
    queue_path = QUEUE_DIR / f"{item['id']}.json"
    receipt_path = RECEIPT_DIR / f"{item['id']}_receipt.json"
    write_json(queue_path, item)
    receipt = {
        "ok": True,
        "dry_run_only": True,
        "published": False,
        "queued_to_external_service": False,
        "network_calls": False,
        "credentials_required": False,
        "queue_path": str(queue_path.relative_to(ROOT)),
        "item_id": item["id"],
        "created_at": utc_now(),
    }
    write_json(receipt_path, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
