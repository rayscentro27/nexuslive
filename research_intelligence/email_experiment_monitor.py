"""
Operator-friendly status view for live email experiments.

Optionally refreshes rollups first, then prints a compact JSON snapshot of:
- recent send/engagement events
- result rollups per variant
- queue/campaign/variant status for the tracked rows
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

try:
    from research_intelligence.email_experiment_scorer import score_once
except Exception:
    from email_experiment_scorer import score_once

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _campaign_map(campaign_ids: List[str]) -> Dict[str, dict]:
    if not campaign_ids:
        return {}
    ids = ",".join(_quote(cid) for cid in sorted(set(campaign_ids)))
    rows = _sb_get(
        "email_campaigns"
        "?select=id,campaign_name,topic,audience,send_status,updated_at"
        f"&id=in.({ids})"
    )
    return {str(row["id"]): row for row in rows}


def _variant_map(variant_ids: List[str]) -> Dict[str, dict]:
    if not variant_ids:
        return {}
    ids = ",".join(_quote(vid) for vid in sorted(set(variant_ids)))
    rows = _sb_get(
        "email_variants"
        "?select=id,campaign_id,variant_label,hook_type,subject_line,status,updated_at"
        f"&id=in.({ids})"
    )
    return {str(row["id"]): row for row in rows}


def _queue_map(variant_ids: List[str]) -> Dict[str, dict]:
    if not variant_ids:
        return {}
    ids = ",".join(_quote(vid) for vid in sorted(set(variant_ids)))
    rows = _sb_get(
        "email_send_queue"
        "?select=id,campaign_id,variant_id,send_channel,queue_status,approval_note,approved_at,scheduled_for,sent_at,updated_at"
        f"&variant_id=in.({ids})"
    )
    return {str(row["variant_id"]): row for row in rows}


def _recent_events(limit: int) -> List[dict]:
    return _sb_get(
        "email_send_events"
        "?select=id,campaign_id,variant_id,recipient_email,event_type,event_at,metadata"
        "&order=event_at.desc"
        f"&limit={limit}"
    )


def _results(limit: int) -> List[dict]:
    return _sb_get(
        "email_experiment_results"
        "?select=id,campaign_id,variant_id,metric_window,recipients_count,delivered_count,open_count,click_count,reply_count,conversion_count,revenue,notes,created_at"
        "&metric_window=eq.lifetime"
        "&order=created_at.desc"
        f"&limit={limit}"
    )


def monitor_once(limit: int = 10, refresh_score: bool = True) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    score_summary = score_once(limit=1000, mark_winners=False) if refresh_score else None
    result_rows = _results(limit)
    event_rows = _recent_events(limit * 5)

    campaign_ids = [str(row.get("campaign_id") or "") for row in result_rows + event_rows]
    variant_ids = [str(row.get("variant_id") or "") for row in result_rows + event_rows]
    campaigns = _campaign_map([cid for cid in campaign_ids if cid])
    variants = _variant_map([vid for vid in variant_ids if vid])
    queues = _queue_map([vid for vid in variant_ids if vid])

    results = []
    for row in result_rows:
        campaign_id = str(row.get("campaign_id") or "")
        variant_id = str(row.get("variant_id") or "")
        results.append(
            {
                **row,
                "campaign_name": (campaigns.get(campaign_id) or {}).get("campaign_name"),
                "topic": (campaigns.get(campaign_id) or {}).get("topic"),
                "variant_label": (variants.get(variant_id) or {}).get("variant_label"),
                "hook_type": (variants.get(variant_id) or {}).get("hook_type"),
                "variant_status": (variants.get(variant_id) or {}).get("status"),
                "queue_status": (queues.get(variant_id) or {}).get("queue_status"),
            }
        )

    events = []
    for row in event_rows:
        campaign_id = str(row.get("campaign_id") or "")
        variant_id = str(row.get("variant_id") or "")
        events.append(
            {
                **row,
                "campaign_name": (campaigns.get(campaign_id) or {}).get("campaign_name"),
                "variant_label": (variants.get(variant_id) or {}).get("variant_label"),
                "hook_type": (variants.get(variant_id) or {}).get("hook_type"),
            }
        )

    return {
        "score_refresh": score_summary,
        "results": results,
        "recent_events": events,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-refresh-score", action="store_true")
    args = parser.parse_args()
    print(json.dumps(monitor_once(limit=args.limit, refresh_score=not args.no_refresh_score), indent=2))
