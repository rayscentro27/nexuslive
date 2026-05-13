#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw in dotenv_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def headers() -> dict[str, str]:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not key:
        raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY/SUPABASE_KEY in environment")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def base_url() -> str:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    if not url:
        raise RuntimeError("Missing SUPABASE_URL in environment")
    return f"{url}/rest/v1"


def get_rows(filters: dict[str, str], limit: int | None) -> list[dict]:
    query = {
        "select": "id,title,status,quality_score,domain,approved_at,created_at",
        "status": "eq.proposed",
        "order": "created_at.desc",
    }
    query.update(filters)
    if limit is not None:
        query["limit"] = str(limit)

    url = f"{base_url()}/knowledge_items?{urllib.parse.urlencode(query)}"
    req = urllib.request.Request(url, headers=headers(), method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def patch_row(item_id: str, payload: dict) -> dict:
    query = urllib.parse.urlencode({"id": f"eq.{item_id}", "select": "id,title,status,quality_score,approved_at,domain"})
    url = f"{base_url()}/knowledge_items?{query}"
    h = headers()
    h["Prefer"] = "return=representation"
    req = urllib.request.Request(url, headers=h, method="PATCH", data=json.dumps(payload).encode())
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode())
    return rows[0] if rows else {}


def normalize_title(title: str) -> str:
    return re.sub(r"^\s*\[Proposed\]\s*", "", title or "", flags=re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Approve selected proposed knowledge_items for testing")
    p.add_argument("--id", dest="item_id", help="Single knowledge_item UUID to approve")
    p.add_argument("--domain", help="Domain filter when using --limit")
    p.add_argument("--limit", type=int, help="Max proposed rows to approve for a domain")
    p.add_argument("--quality-score", type=int, default=85, help="Quality score to set (default: 85)")
    p.add_argument("--apply", action="store_true", help="Apply changes (default is dry-run)")
    return p.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.item_id and (args.domain or args.limit is not None):
        raise ValueError("Use either --id OR --domain with --limit, not both")

    if not args.item_id:
        if not args.domain or args.limit is None:
            raise ValueError("When not using --id, you must provide both --domain and --limit")
        if args.limit <= 0:
            raise ValueError("--limit must be > 0")

    if args.quality_score < 0 or args.quality_score > 100:
        raise ValueError("--quality-score must be between 0 and 100")


def main() -> int:
    args = parse_args()
    try:
        validate_args(args)
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return 2

    filters: dict[str, str] = {}
    limit: int | None = None
    if args.item_id:
        filters["id"] = f"eq.{args.item_id}"
        limit = 1
    else:
        filters["domain"] = f"eq.{args.domain}"
        limit = args.limit

    try:
        rows = get_rows(filters, limit)
    except Exception as exc:
        print(f"[ERROR] Failed to fetch candidate rows: {exc}")
        return 2

    if not rows:
        print("No proposed rows matched the selection.")
        return 0

    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Candidates: {len(rows)}")
    print("Before summary:")
    for r in rows:
        print(f"- {r.get('id')} | {r.get('status')} | q={r.get('quality_score')} | {r.get('title')}")

    approved_ids: list[str] = []
    after_rows: list[dict] = []
    approved_at = datetime.now(timezone.utc).isoformat()

    for row in rows:
        payload = {
            "status": "approved",
            "quality_score": args.quality_score,
            "title": normalize_title(row.get("title") or ""),
        }
        if not row.get("approved_at"):
            payload["approved_at"] = approved_at

        if args.apply:
            try:
                updated = patch_row(row["id"], payload)
            except Exception as exc:
                print(f"[WARN] Failed to update {row.get('id')}: {exc}")
                continue
            after_rows.append(updated)
            approved_ids.append(str(updated.get("id")))
        else:
            preview = dict(row)
            preview.update(payload)
            after_rows.append(preview)
            approved_ids.append(str(row.get("id")))

    print("After summary:")
    for r in after_rows:
        print(f"- {r.get('id')} | {r.get('status')} | q={r.get('quality_score')} | {r.get('title')}")

    print("Approved IDs:")
    for item_id in approved_ids:
        print(item_id)

    if not args.apply:
        print("Dry-run complete. Re-run with --apply to persist changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
