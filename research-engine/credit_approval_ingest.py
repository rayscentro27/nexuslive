#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prelaunch_utils import rest_select, supabase_request

RATE_LIMIT_SECONDS = float(os.getenv("CREDIT_APPROVAL_INGEST_RATE_LIMIT", "1.0"))


def _bucket_score(score: int | None) -> str:
    if not score:
        return "unknown"
    if score < 620:
        return "subprime"
    if score < 680:
        return "near_prime"
    if score < 740:
        return "prime"
    return "super_prime"


def _bucket_income(income: float | None) -> str:
    if not income:
        return "unknown"
    if income < 50000:
        return "lt_50k"
    if income < 100000:
        return "50k_99k"
    if income < 200000:
        return "100k_199k"
    return "200k_plus"


def _bucket_history(history: str | None) -> str:
    text = (history or "").strip().lower()
    if not text:
        return "unknown"
    if any(token in text for token in ("0", "6 month", "new")):
        return "new"
    if any(token in text for token in ("1 year", "12 month")):
        return "1_year_plus"
    if any(token in text for token in ("2 year", "24 month", "3 year", "5 year")):
        return "seasoned"
    return text.replace(" ", "_")


def normalize_approval_record(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_name": raw.get("source_name") or raw.get("source") or "unknown",
        "source_url": raw.get("source_url"),
        "card_name": raw.get("card_name") or raw.get("product_name"),
        "bank_name": raw.get("bank_name") or raw.get("issuer_name"),
        "product_type": raw.get("product_type") or "business_credit_card",
        "approved": bool(raw.get("approved")) if raw.get("approved") is not None else None,
        "credit_limit": raw.get("credit_limit"),
        "credit_score": raw.get("credit_score"),
        "annual_income": raw.get("annual_income"),
        "state": raw.get("state"),
        "bureau": raw.get("bureau"),
        "credit_history_age": raw.get("credit_history_age"),
        "application_date": raw.get("application_date"),
        "raw_payload": raw,
    }


def store_approval_result(record: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
    if dry_run:
        return {"ok": True, "record": record, "dry_run": True}
    rows, _ = supabase_request(
        "credit_approval_results",
        method="POST",
        body=record,
        prefer="return=representation",
    )
    return {"ok": True, "record": (rows or [None])[0]}


def refresh_card_approval_patterns(*, dry_run: bool = True) -> dict[str, Any]:
    rows = rest_select(
        "credit_approval_results?select=id,card_name,bank_name,product_type,approved,credit_limit,credit_score,"
        "annual_income,state,bureau,credit_history_age,application_date&limit=2000"
    ) or []
    grouped: dict[tuple[str, str, str, str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        key = (
            row.get("card_name") or "",
            row.get("bank_name") or "",
            row.get("product_type") or "",
            _bucket_score(row.get("credit_score")),
            _bucket_income(row.get("annual_income")),
            _bucket_history(row.get("credit_history_age")),
            row.get("bureau") or "",
            row.get("state") or "",
        )
        grouped.setdefault(key, []).append(row)

    payloads = []
    for key, items in grouped.items():
        approved_items = [item for item in items if item.get("approved") is True]
        limits = sorted(float(item.get("credit_limit") or 0) for item in approved_items if item.get("credit_limit"))
        payloads.append({
            "card_name": key[0],
            "bank_name": key[1],
            "product_type": key[2],
            "score_bucket": key[3],
            "income_bucket": key[4],
            "history_bucket": key[5],
            "bureau": key[6] or None,
            "state": key[7] or None,
            "sample_size": len(items),
            "approval_rate": round(len(approved_items) / len(items), 4) if items else 0,
            "avg_limit": round(sum(limits) / len(limits), 2) if limits else None,
            "median_limit": round(median(limits), 2) if limits else None,
            "min_score": min((item.get("credit_score") for item in approved_items if item.get("credit_score") is not None), default=None),
            "max_limit": max(limits) if limits else None,
            "confidence_score": round(min(1.0, len(items) / 25.0), 4),
            "last_seen_at": max((item.get("application_date") for item in items if item.get("application_date")), default=None),
        })

    if dry_run:
        return {"ok": True, "patterns": payloads, "dry_run": True}

    for payload in payloads:
        supabase_request("card_approval_patterns", method="POST", body=payload, prefer="return=representation")
    return {"ok": True, "pattern_count": len(payloads)}


def ingest_public_records(records: list[dict[str, Any]], *, dry_run: bool = True) -> dict[str, Any]:
    stored = []
    for raw in records:
        source_url = raw.get("source_url") or ""
        if source_url and not source_url.startswith(("http://", "https://")):
            raise ValueError("source attribution required with a public http(s) URL")
        normalized = normalize_approval_record(raw)
        stored.append(store_approval_result(normalized, dry_run=dry_run))
        time.sleep(RATE_LIMIT_SECONDS)
    patterns = refresh_card_approval_patterns(dry_run=dry_run)
    return {"ok": True, "stored_count": len(stored), "patterns": patterns}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest public, non-personal credit approval trend data.")
    parser.add_argument("--input", required=True, help="Path to a JSON array of public approval records.")
    parser.add_argument("--live", action="store_true", help="Write records to Supabase instead of dry-run preview.")
    args = parser.parse_args()

    records = json.loads(Path(args.input).read_text())
    report = ingest_public_records(records, dry_run=not args.live)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
