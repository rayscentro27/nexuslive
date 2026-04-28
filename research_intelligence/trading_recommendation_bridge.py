"""
Trading recommendation bridge.

Converts strong `research_artifacts` trading rows into real
`reviewed_signal_proposals` plus companion `risk_decisions` rows so the
downstream recommendation and replay pipeline can operate on first-class
trading proposals instead of artifact-only placeholders.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

from research_intelligence.recommendation_packet_engine import (
    _artifact_score,
    _is_artifact_noise,
    _sanitize_research_text,
)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
MIN_SCORE = 60
OPTIONS_STRATEGY_FAMILIES = {
    "covered_call": ("covered call", "covered-call", "cc "),
    "cash_secured_put": ("cash secured put", "cash-secured put", "short put", "sold put"),
    "iron_condor": ("iron condor", "condor"),
    "credit_spread": ("credit spread", "short spread"),
    "debit_spread": ("debit spread", "long spread"),
    "straddle": ("straddle",),
    "strangle": ("strangle",),
    "butterfly": ("butterfly", "broken wing butterfly"),
    "calendar_spread": ("calendar spread", "calendar", "diagonal"),
    "zebra_strategy": ("zebra",),
    "wheel_strategy": ("wheel",),
}


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


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _artifact_rows(limit: int) -> List[dict]:
    rows = _sb_get(
        "research_artifacts"
        "?select=id,title,topic,subtheme,summary,content,key_points,action_items,risk_warnings,opportunity_notes,source,trace_id,created_at"
        "&topic=eq.trading"
        f"&order=created_at.desc&limit={limit * 4}"
    )
    cleaned: List[dict] = []
    for row in rows:
        summary = _sanitize_research_text(row.get("summary") or "")
        if _is_artifact_noise(summary):
            continue
        key_points = [
            _sanitize_research_text(x)
            for x in (row.get("key_points") or [])
            if not _is_artifact_noise(str(x))
        ]
        risk_warnings = [
            _sanitize_research_text(x)
            for x in (row.get("risk_warnings") or [])
            if not _is_artifact_noise(str(x))
        ]
        content = _sanitize_research_text(row.get("content") or "")
        normalized = {
            **row,
            "summary": summary,
            "content": content,
            "key_points": key_points,
            "risk_warnings": risk_warnings,
        }
        score = _artifact_score(normalized)
        if score < MIN_SCORE:
            continue
        normalized["bridge_score"] = score
        cleaned.append(normalized)
        if len(cleaned) >= limit:
            break
    return cleaned


def _asset_type(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in (" call ", " put ", " option", " strike", " expiry", " expiration")):
        return "options"
    return "forex"


def _symbol(row: dict) -> str:
    candidates = [
        row.get("subtheme"),
        row.get("source"),
        "research_candidate",
    ]
    for candidate in candidates:
        value = re.sub(r"[^A-Za-z0-9_/.-]+", "_", str(candidate or "")).strip("_")
        if value:
            return value[:40]
    return "research_candidate"


def _side(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("short", "bearish", "sell", "put")):
        return "short"
    if any(term in lowered for term in ("long", "bullish", "buy", "call")):
        return "long"
    return "research"


def _timeframe(text: str) -> str:
    lowered = text.lower()
    mapping = [
        ("scalp", "5m"),
        ("intraday", "15m"),
        ("swing", "4h"),
        ("daily", "1d"),
        ("weekly", "1w"),
    ]
    for needle, value in mapping:
        if needle in lowered:
            return value
    return "multi"


def _strategy_id(row: dict) -> str:
    return str(row.get("title") or f"artifact-{row.get('id')}")[:120]


def _normalize_strategy_text(value: object) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _strategy_type(row: dict) -> str | None:
    strategy_text = _normalize_strategy_text(row.get("title") or row.get("summary") or row.get("content"))
    if not strategy_text:
        return None

    compact = strategy_text.replace(" ", "_")
    if compact in OPTIONS_STRATEGY_FAMILIES:
        return compact

    for family, keywords in OPTIONS_STRATEGY_FAMILIES.items():
        if any(keyword in strategy_text for keyword in keywords):
            return family

    if "leaps" in strategy_text and any(token in strategy_text for token in ("selling", "sell", "income", "premium")):
        return "covered_call"
    if "put" in strategy_text and any(token in strategy_text for token in ("sell", "selling", "short", "premium", "income")):
        return "cash_secured_put"
    if "call" in strategy_text and any(token in strategy_text for token in ("covered", "income", "premium", "selling", "sell")):
        return "covered_call"
    if "spread" in strategy_text and "credit" not in strategy_text and "debit" not in strategy_text:
        return "credit_spread" if any(token in strategy_text for token in ("income", "selling", "sell", "short")) else "debit_spread"

    return None


def _proposal_row(row: dict) -> dict:
    artifact_id = row["id"]
    score = int(row["bridge_score"])
    confidence = round(score / 100, 3)
    combined_text = " ".join(
        [
            str(row.get("title") or ""),
            str(row.get("summary") or ""),
            str(row.get("content") or ""),
            " ".join(row.get("key_points") or []),
            " ".join(row.get("risk_warnings") or []),
        ]
    )
    asset_type = _asset_type(combined_text)
    recommendation = "; ".join((row.get("action_items") or [])[:3]) or row.get("summary") or row.get("title")
    underlying = _symbol(row) if asset_type == "options" else None
    expiration_note = "Derived from research artifact context." if asset_type == "options" else None
    return {
        "id": _deterministic_uuid(f"artifact-bridge-proposal:{artifact_id}"),
        "signal_id": None,
        "symbol": _symbol(row),
        "side": _side(combined_text),
        "timeframe": _timeframe(combined_text),
        "strategy_id": _strategy_id(row),
        "strategy_type": _strategy_type(row),
        "asset_type": asset_type,
        "entry_price": None,
        "stop_loss": None,
        "take_profit": None,
        "underlying": underlying,
        "expiration_note": expiration_note,
        "strike_note": None,
        "premium_estimate": None,
        "delta_guidance": None,
        "theta_note": None,
        "vega_note": None,
        "iv_context": None,
        "webull_note": None,
        "ai_confidence": confidence,
        "market_context": row.get("summary"),
        "research_context": row.get("content"),
        "risk_notes": "; ".join((row.get("risk_warnings") or [])[:3]),
        "recommendation": recommendation[:1000] if recommendation else None,
        "status": "needs_review",
        "trace_id": row.get("trace_id"),
    }


def _risk_row(row: dict, proposal_id: str) -> dict:
    score = int(row["bridge_score"])
    if score >= 70:
        decision = "approved"
    elif score >= 40:
        decision = "manual_review"
    else:
        decision = "blocked"
    return {
        "id": _deterministic_uuid(f"artifact-bridge-risk:{row['id']}"),
        "proposal_id": proposal_id,
        "signal_id": None,
        "symbol": _symbol(row),
        "side": _side(" ".join([str(row.get('title') or ''), str(row.get('summary') or '')])),
        "asset_type": _asset_type(" ".join([str(row.get("title") or ""), str(row.get("content") or "")])),
        "decision": decision,
        "risk_score": score,
        "risk_flags": row.get("risk_warnings") or [],
        "rr_ratio": None,
        "daily_pnl_used": None,
        "open_positions_count": None,
        "rr_ok": None,
        "prices_ok": None,
        "daily_pnl_ok": None,
        "positions_ok": None,
        "no_duplicate": None,
        "rejection_reason": "; ".join((row.get("risk_warnings") or [])[:3]) if decision == "blocked" else None,
        "trace_id": row.get("trace_id"),
    }


def bridge_once(limit: int = 3) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    artifacts = _artifact_rows(limit)
    proposals_inserted: List[str] = []
    risks_inserted: List[str] = []
    for artifact in artifacts:
        proposal = _proposal_row(artifact)
        risk = _risk_row(artifact, proposal["id"])
        try:
            _sb_post("reviewed_signal_proposals", [proposal], prefer="resolution=merge-duplicates,return=representation")
        except urllib.error.HTTPError as exc:
            if exc.code != 400:
                raise
            legacy_proposal = {k: v for k, v in proposal.items() if k != "strategy_type"}
            _sb_post("reviewed_signal_proposals", [legacy_proposal], prefer="resolution=merge-duplicates,return=representation")
        _sb_post("risk_decisions", [risk], prefer="resolution=merge-duplicates,return=representation")
        proposals_inserted.append(proposal["id"])
        risks_inserted.append(risk["id"])
    return {
        "artifacts_considered": len(artifacts),
        "proposals_written": proposals_inserted,
        "risk_decisions_written": risks_inserted,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    print(json.dumps(bridge_once(limit=args.limit), indent=2))
