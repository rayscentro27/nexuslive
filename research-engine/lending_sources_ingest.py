#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prelaunch_utils import supabase_request

RATE_LIMIT_SECONDS = float(os.getenv("LENDING_SOURCES_INGEST_RATE_LIMIT", "1.0"))
ALLOWED_SOURCE_HINTS = ("ncua", "sba.gov", "credit union", "bank", "official")


def normalize_lending_institution(raw: dict[str, Any]) -> dict[str, Any]:
    source_url = raw.get("source_url") or ""
    if source_url and not source_url.startswith(("http://", "https://")):
        raise ValueError("source_url must be a public http(s) URL")

    product_types = raw.get("product_types") or []
    if isinstance(product_types, str):
        product_types = [part.strip() for part in product_types.split(",") if part.strip()]

    prep_steps = raw.get("recommended_prep_steps") or []
    if isinstance(prep_steps, str):
        prep_steps = [prep_steps]

    return {
        "institution_name": raw.get("institution_name"),
        "institution_type": raw.get("institution_type"),
        "product_types": product_types,
        "min_score": raw.get("min_score"),
        "max_funding": raw.get("max_funding"),
        "geo_restrictions": raw.get("geo_restrictions"),
        "membership_required": bool(raw.get("membership_required")),
        "business_checking_available": bool(raw.get("business_checking_available")),
        "business_credit_card_available": bool(raw.get("business_credit_card_available")),
        "business_loc_available": bool(raw.get("business_loc_available")),
        "sba_available": bool(raw.get("sba_available")),
        "relationship_notes": raw.get("relationship_notes"),
        "recommended_prep_steps": prep_steps,
        "source_url": source_url,
    }


def ingest_lending_sources(records: list[dict[str, Any]], *, dry_run: bool = True) -> dict[str, Any]:
    normalized_rows = []
    for raw in records:
        normalized = normalize_lending_institution(raw)
        normalized_rows.append(normalized)
        if not dry_run:
            supabase_request(
                "lending_institutions",
                method="POST",
                body=normalized,
                prefer="return=representation",
            )
        time.sleep(RATE_LIMIT_SECONDS)
    return {"ok": True, "count": len(normalized_rows), "rows": normalized_rows if dry_run else []}


def build_admin_review_note(records: list[dict[str, Any]]) -> dict[str, Any]:
    notes = []
    for row in records:
        source = (row.get("source_url") or "").lower()
        source_ok = any(hint in source for hint in ALLOWED_SOURCE_HINTS) if source else False
        notes.append({
            "institution_name": row.get("institution_name"),
            "source_url": row.get("source_url"),
            "source_review_hint": "official_or_public" if source_ok else "manual_review_recommended",
        })
    return {"notes": notes}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest credit union, SBA lender, and bank relationship research.")
    parser.add_argument("--input", required=True, help="Path to JSON array of institution records.")
    parser.add_argument("--live", action="store_true", help="Write institutions to Supabase.")
    args = parser.parse_args()

    records = json.loads(Path(args.input).read_text())
    report = ingest_lending_sources(records, dry_run=not args.live)
    report["admin_review"] = build_admin_review_note(records)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
