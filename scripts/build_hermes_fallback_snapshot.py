#!/usr/bin/env python3
"""Build a static, non-secret snapshot the Hermes Netlify function serves when the
live Hermes gateway is offline. This is REAL data from the last Operator run + the
social queue — clearly labelled as a snapshot, never presented as a live reply.

Run after run_nexus_operator_core.py. Output is bundled with the Netlify function:
    netlify/functions/hermes-fallback-snapshot.json

Contains NO tokens/secrets — only counts, statuses, and next-action text.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OUT = ROOT / "netlify" / "functions" / "hermes-fallback-snapshot.json"


def _load_json(rel: str) -> dict:
    p = ROOT / rel
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def main() -> int:
    op = _load_json("reports/operator/nexus_operator_status.json")
    social = op.get("social", {}) or {}
    connectors = social.get("connector_status", {}) or {}

    def conn(name: str) -> dict:
        c = connectors.get(name, {}) or {}
        return {
            "account_connected": c.get("account_connected", "unknown"),
            "publishing_ready": c.get("publishing_ready", "unknown"),
        }

    # Queue counts (prefer the live summarize(); fall back to operator's copy)
    counts = {}
    try:
        from lib import social_queue

        counts = social_queue.summarize().get("counts", {})
    except Exception:
        counts = {
            "published": social.get("published_count"),
            "queued_for_review": social.get("pending_review_count"),
            "approved": social.get("approved_count"),
            "dry_run_ready": social.get("dry_run_ready_count"),
            "failed": social.get("failed_count"),
        }

    blockers = [
        {"area": b.get("area"), "blocker": b.get("blocker"), "fix": b.get("fix")}
        for b in (op.get("blockers") or [])
    ][:6]

    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "is_live": False,
        "note": (
            "This is a static system snapshot from the last Nexus Operator run, not a live "
            "Hermes conversation. The live Hermes AI gateway is not reachable from production."
        ),
        "overall_status": op.get("overall_status", "unknown"),
        "social_queue": {
            "published": counts.get("published"),
            "queued_for_review": counts.get("queued_for_review"),
            "approved": counts.get("approved"),
            "dry_run_ready": counts.get("dry_run_ready"),
            "failed": counts.get("failed"),
            "average_quality_score": social.get("average_quality_score"),
        },
        "connectors": {"facebook": conn("facebook"), "instagram": conn("instagram")},
        "approvals_pending": counts.get("queued_for_review"),
        "next_social_action": social.get("next_social_action"),
        "next_actions": op.get("top_3_next_actions") or [],
        "blockers": blockers,
        "trading": {"mode": "paper/demo only", "note": "No live or funded trading."},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)} (generated_at={snapshot['generated_at']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
