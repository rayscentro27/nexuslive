#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.prelaunch_utils import default_test_mode, supabase_request, table_exists

CATEGORIES = [
    "credit_repair",
    "business_setup",
    "business_funding_tier_1",
    "business_opportunities",
    "grants",
    "trading_education",
    "sba_tier_2_funding",
]


def str_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def sample_records() -> list[dict]:
    rows = []
    for category in CATEGORIES:
        rows.append({
            "source_title": f"Sample {category.replace('_', ' ').title()} Brief",
            "source_type": "seed_sample",
            "category": category,
            "summary": f"Seed sample for {category}.",
            "key_takeaways": [f"Initial takeaways for {category}."],
            "recommended_user_stage": "prelaunch",
            "risk_compliance_notes": "Not approved for user display.",
            "created_by_agent": "codex_prelaunch",
            "confidence_score": 0.42,
            "approved_for_user_display": False,
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", nargs="?", const="true", default="true")
    args = parser.parse_args()
    dry_run = str_bool(args.dry_run, True)

    existing_tables = {name: table_exists(name) for name in ["knowledge_documents", "knowledge_chunks", "nexus_knowledge_items"]}
    report = {
        "dry_run": dry_run,
        "test_mode_default": default_test_mode(),
        "existing_tables": existing_tables,
        "sample_records": sample_records(),
    }
    if not any(existing_tables.values()):
        report["status"] = "needs_migration_confirmation"
        report["note"] = "No existing knowledge table was found. A migration proposal should be reviewed before inserting records."
    else:
        report["status"] = "ready_to_seed"
        report["note"] = "Existing knowledge storage detected. Live inserts were skipped because dry-run is active."
        if not dry_run and existing_tables.get("nexus_knowledge_items"):
            inserted, _ = supabase_request(
                "nexus_knowledge_items",
                method="POST",
                body=sample_records(),
                prefer="return=representation",
            )
            report["status"] = "seeded"
            report["inserted_count"] = len(inserted or [])
            report["note"] = "Inserted sample knowledge records with approved_for_user_display=false."

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
