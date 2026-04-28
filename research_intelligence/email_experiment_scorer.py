"""
Rolls low-level email send events into experiment results.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_post(table: str, rows: List[dict], prefer: str = "return=representation") -> List[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(prefer),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_patch(table: str, query: str, data: dict) -> None:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?{query}",
        data=json.dumps(data).encode(),
        headers=_headers("return=minimal"),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=20):
        pass


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _events(limit: int) -> List[dict]:
    return _sb_get(
        "email_send_events"
        "?select=id,campaign_id,variant_id,recipient_email,event_type,event_at,metadata"
        "&order=event_at.desc"
        f"&limit={limit}"
    )


def _campaign_status(campaign_id: str) -> List[dict]:
    return _sb_get(f"email_campaigns?id=eq.{_quote(campaign_id)}&select=id,send_status,updated_at&limit=1")


def score_once(limit: int = 1000, mark_winners: bool = False) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    rows = _events(limit)
    grouped: Dict[Tuple[str, str], dict] = {}
    recipients_seen: Dict[Tuple[str, str], set] = defaultdict(set)

    for row in rows:
        campaign_id = str(row.get("campaign_id") or "")
        variant_id = str(row.get("variant_id") or "")
        if not campaign_id or not variant_id:
            continue
        key = (campaign_id, variant_id)
        grouped.setdefault(
            key,
            {
                "campaign_id": campaign_id,
                "variant_id": variant_id,
                "recipients_count": 0,
                "delivered_count": 0,
                "open_count": 0,
                "click_count": 0,
                "reply_count": 0,
                "conversion_count": 0,
                "revenue": 0,
            },
        )
        recipient = str(row.get("recipient_email") or "")
        if recipient and recipient not in recipients_seen[key]:
            recipients_seen[key].add(recipient)
            grouped[key]["recipients_count"] += 1

        event_type = str(row.get("event_type") or "")
        if event_type == "delivered":
            grouped[key]["delivered_count"] += 1
        elif event_type == "opened":
            grouped[key]["open_count"] += 1
        elif event_type == "clicked":
            grouped[key]["click_count"] += 1
        elif event_type == "replied":
            grouped[key]["reply_count"] += 1
        elif event_type == "converted":
            grouped[key]["conversion_count"] += 1
            try:
                grouped[key]["revenue"] += float((row.get("metadata") or {}).get("revenue") or 0)
            except Exception:
                pass

    results_written: List[str] = []
    winners_marked: List[str] = []
    per_campaign_best: Dict[str, Tuple[str, float]] = {}

    for (campaign_id, variant_id), stats in grouped.items():
        score = (
            stats["reply_count"] * 4
            + stats["click_count"] * 2
            + stats["open_count"] * 0.5
            + stats["conversion_count"] * 6
        )
        best = per_campaign_best.get(campaign_id)
        if not best or score > best[1]:
            per_campaign_best[campaign_id] = (variant_id, score)

        result_id = _deterministic_uuid(f"email-experiment-result:{campaign_id}:{variant_id}:lifetime")
        row = {
            "id": result_id,
            "campaign_id": campaign_id,
            "variant_id": variant_id,
            "metric_window": "lifetime",
            **stats,
            "notes": f"auto_scored score={score}",
        }
        _sb_post("email_experiment_results", [row], prefer="resolution=merge-duplicates,return=representation")
        results_written.append(result_id)

    if mark_winners:
        for campaign_id, (winner_variant_id, _score) in per_campaign_best.items():
            _sb_patch("email_variants", f"campaign_id=eq.{_quote(campaign_id)}&status=eq.queued", {"status": "loser"})
            _sb_patch("email_variants", f"id=eq.{_quote(winner_variant_id)}", {"status": "winner"})
            winners_marked.append(winner_variant_id)
            campaign_rows = _campaign_status(campaign_id)
            if campaign_rows:
                _sb_patch("email_campaigns", f"id=eq.{_quote(campaign_id)}", {"send_status": campaign_rows[0].get("send_status") or "queued"})

    return {
        "events_seen": len(rows),
        "results_written": results_written,
        "winners_marked": winners_marked,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--mark-winners", action="store_true")
    args = parser.parse_args()
    print(json.dumps(score_once(limit=args.limit, mark_winners=args.mark_winners), indent=2))
