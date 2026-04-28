"""
Replay result finisher.

Consumes running `paper_trade_runs`, generates one deterministic
`replay_results` row per run, and marks the run as `finished`.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

OPTIONS_STRATEGY_PROFILES = {
    "covered_call": {"typical_win_rate": 0.72, "typical_pnl_pct_win": 0.08, "typical_pnl_pct_loss": -0.15},
    "cash_secured_put": {"typical_win_rate": 0.68, "typical_pnl_pct_win": 0.07, "typical_pnl_pct_loss": -0.18},
    "iron_condor": {"typical_win_rate": 0.65, "typical_pnl_pct_win": 0.12, "typical_pnl_pct_loss": -0.20},
    "credit_spread": {"typical_win_rate": 0.62, "typical_pnl_pct_win": 0.10, "typical_pnl_pct_loss": -0.25},
    "debit_spread": {"typical_win_rate": 0.45, "typical_pnl_pct_win": 0.30, "typical_pnl_pct_loss": -0.50},
    "straddle": {"typical_win_rate": 0.40, "typical_pnl_pct_win": 0.50, "typical_pnl_pct_loss": -0.60},
    "strangle": {"typical_win_rate": 0.38, "typical_pnl_pct_win": 0.60, "typical_pnl_pct_loss": -0.65},
    "butterfly": {"typical_win_rate": 0.55, "typical_pnl_pct_win": 0.20, "typical_pnl_pct_loss": -0.30},
    "calendar_spread": {"typical_win_rate": 0.58, "typical_pnl_pct_win": 0.15, "typical_pnl_pct_loss": -0.20},
    "zebra_strategy": {"typical_win_rate": 0.60, "typical_pnl_pct_win": 0.25, "typical_pnl_pct_loss": -0.20},
    "wheel_strategy": {"typical_win_rate": 0.75, "typical_pnl_pct_win": 0.06, "typical_pnl_pct_loss": -0.12},
}
DEFAULT_OPTIONS_PROFILE = {"typical_win_rate": 0.50, "typical_pnl_pct_win": 0.10, "typical_pnl_pct_loss": -0.20}
OPTIONS_STRATEGY_KEYWORDS = {
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


def _running_runs(limit: int) -> List[dict]:
    return _sb_get(
        "paper_trade_runs"
        "?select=id,proposal_id,signal_id,asset_type,symbol,strategy_id,strategy_type,replay_mode,status,started_at,trace_id"
        "&status=eq.running"
        "&order=started_at.asc"
        f"&limit={limit}"
    )


def _current_run(run_id: str) -> Optional[dict]:
    rows = _sb_get(
        "paper_trade_runs"
        "?select=id,proposal_id,signal_id,asset_type,symbol,strategy_id,strategy_type,replay_mode,status,started_at,trace_id"
        f"&id=eq.{_quote(run_id)}&limit=1"
    )
    return rows[0] if rows else None


def _proposal(proposal_id: str) -> Optional[dict]:
    try:
        rows = _sb_get(
            "reviewed_signal_proposals"
            "?select=id,symbol,side,timeframe,strategy_id,strategy_type,asset_type,entry_price,stop_loss,take_profit,ai_confidence,trace_id"
            f"&id=eq.{_quote(proposal_id)}&limit=1"
        )
    except Exception:
        rows = _sb_get(
            "reviewed_signal_proposals"
            "?select=id,symbol,side,timeframe,strategy_id,asset_type,entry_price,stop_loss,take_profit,ai_confidence,trace_id"
            f"&id=eq.{_quote(proposal_id)}&limit=1"
        )
    return rows[0] if rows else None


def _risk(proposal_id: str) -> Optional[dict]:
    rows = _sb_get(
        "risk_decisions"
        "?select=id,proposal_id,decision,risk_score,risk_flags,rr_ratio,created_at"
        f"&proposal_id=eq.{_quote(proposal_id)}"
        "&order=created_at.desc&limit=1"
    )
    return rows[0] if rows else None


def _safe_float(value: object) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _normalize_strategy_text(value: object) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _resolve_options_strategy_family(strategy_id: object) -> str:
    normalized = _normalize_strategy_text(strategy_id)
    if not normalized:
        return "unknown"

    compact = normalized.replace(" ", "_")
    if compact in OPTIONS_STRATEGY_PROFILES:
        return compact

    for family, keywords in OPTIONS_STRATEGY_KEYWORDS.items():
        if any(keyword in normalized for keyword in keywords):
            return family

    if "leaps" in normalized and any(token in normalized for token in ("selling", "sell", "income", "premium")):
        return "covered_call"
    if "put" in normalized and any(token in normalized for token in ("sell", "selling", "short", "premium")):
        return "cash_secured_put"
    if "call" in normalized and any(token in normalized for token in ("covered", "income", "premium", "selling", "sell")):
        return "covered_call"
    if "spread" in normalized and "credit" not in normalized and "debit" not in normalized:
        return "credit_spread" if "income" in normalized or "selling" in normalized else "debit_spread"

    return "unknown"


def _simulate_forex(proposal: Optional[dict], risk: Optional[dict]) -> dict:
    proposal = proposal or {}
    risk = risk or {}
    entry_price = _safe_float(proposal.get("entry_price"))
    stop_loss = _safe_float(proposal.get("stop_loss"))
    take_profit = _safe_float(proposal.get("take_profit"))
    rr_ratio = _safe_float(risk.get("rr_ratio"))
    if rr_ratio is None and None not in (entry_price, stop_loss, take_profit):
        derived_risk = abs(entry_price - stop_loss)
        derived_reward = abs(take_profit - entry_price)
        if derived_risk:
            rr_ratio = round(derived_reward / derived_risk, 4)

    if rr_ratio is None:
        confidence = float(proposal.get("ai_confidence") or 0)
        risk_score = float(risk.get("risk_score") or 0)
        if risk_score >= 70 or confidence >= 0.8:
            rr_ratio = 2.0
        elif risk_score >= 55 or confidence >= 0.6:
            rr_ratio = 1.5
        else:
            rr_ratio = 1.0

    bars_to_resolution = round(20 + rr_ratio * 10)
    if rr_ratio >= 2.0:
        replay_outcome = "tp_hit"
        pnl_r = round(rr_ratio, 4)
        hit_take_profit = True
        hit_stop_loss = False
    elif rr_ratio >= 1.5:
        replay_outcome = "breakeven"
        pnl_r = 0.0
        hit_take_profit = False
        hit_stop_loss = False
    else:
        replay_outcome = "sl_hit"
        pnl_r = -1.0
        hit_take_profit = False
        hit_stop_loss = True

    if entry_price and stop_loss and take_profit:
        risk_move = abs(entry_price - stop_loss)
        reward_move = abs(take_profit - entry_price)
        if replay_outcome == "tp_hit":
            pnl_pct = round((reward_move / entry_price) * 100, 4)
        elif replay_outcome == "sl_hit":
            pnl_pct = round((-risk_move / entry_price) * 100, 4)
        else:
            pnl_pct = 0.0
    else:
        pnl_pct = round(pnl_r, 4)

    return {
        "replay_outcome": replay_outcome,
        "pnl_r": pnl_r,
        "pnl_pct": pnl_pct,
        "mfe": max(pnl_r, 0.25),
        "mae": -0.5 if replay_outcome != "tp_hit" else -0.25,
        "bars_to_resolution": bars_to_resolution,
        "hit_take_profit": hit_take_profit,
        "hit_stop_loss": hit_stop_loss,
        "expired": False,
    }


def _simulate_options(proposal: Optional[dict]) -> dict:
    proposal = proposal or {}
    strategy_family = proposal.get("strategy_type") or _resolve_options_strategy_family(proposal.get("strategy_id"))
    profile = OPTIONS_STRATEGY_PROFILES.get(strategy_family, DEFAULT_OPTIONS_PROFILE)
    ai_confidence = float(proposal.get("ai_confidence") or 0.5)
    effective_win_prob = (profile["typical_win_rate"] + ai_confidence) / 2

    if effective_win_prob >= 0.55:
        replay_outcome = "win"
        pnl_pct = round(profile["typical_pnl_pct_win"] * 100, 4)
        hit_take_profit = True
        hit_stop_loss = False
    elif effective_win_prob >= 0.45:
        replay_outcome = "breakeven"
        pnl_pct = 0.0
        hit_take_profit = False
        hit_stop_loss = False
    else:
        replay_outcome = "loss"
        pnl_pct = round(profile["typical_pnl_pct_loss"] * 100, 4)
        hit_take_profit = False
        hit_stop_loss = True

    return {
        "replay_outcome": replay_outcome,
        "pnl_r": None,
        "pnl_pct": pnl_pct,
        "mfe": round(max(pnl_pct, 0.0), 4),
        "mae": round(min(pnl_pct, 0.0), 4),
        "bars_to_resolution": None,
        "hit_take_profit": hit_take_profit,
        "hit_stop_loss": hit_stop_loss,
        "expired": False,
    }


def _outcome(run: dict, proposal: Optional[dict], risk: Optional[dict]) -> dict:
    mode = str(run.get("replay_mode") or "")
    asset_type = str(run.get("asset_type") or (proposal or {}).get("asset_type") or "forex")
    if mode == "options_historical_profile" or asset_type == "options":
        return _simulate_options(proposal)
    if mode == "forex_static_rr" or asset_type == "forex":
        return _simulate_forex(proposal, risk)
    return {
        "replay_outcome": "breakeven",
        "pnl_r": 0.0,
        "pnl_pct": 0.0,
        "mfe": 0.25,
        "mae": -0.25,
        "bars_to_resolution": None,
        "hit_take_profit": False,
        "hit_stop_loss": False,
        "expired": False,
    }


def finish_once(limit: int = 20) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")
    runs = _running_runs(limit)
    completed: List[str] = []
    results: List[str] = []
    for initial_run in runs:
        run = _current_run(initial_run["id"])
        if not run or run.get("status") != "running":
            continue
        proposal_id = run.get("proposal_id")
        proposal = _proposal(proposal_id) if proposal_id else None
        risk = _risk(proposal_id) if proposal_id else None
        outcome = _outcome(run, proposal, risk)
        result_id = _deterministic_uuid(f"replay-result:{run['id']}")
        _sb_post(
            "replay_results",
            [
                {
                    "id": result_id,
                    "run_id": run["id"],
                    "proposal_id": proposal_id,
                    "signal_id": run.get("signal_id"),
                    "asset_type": run.get("asset_type") or (proposal or {}).get("asset_type") or "forex",
                    "symbol": run.get("symbol") or (proposal or {}).get("symbol"),
                    "strategy_id": run.get("strategy_id") or (proposal or {}).get("strategy_id"),
                    "strategy_type": run.get("strategy_type"),
                    "replay_outcome": outcome["replay_outcome"],
                    "pnl_r": outcome["pnl_r"],
                    "pnl_pct": outcome["pnl_pct"],
                    "mfe": outcome["mfe"],
                    "mae": outcome["mae"],
                    "bars_to_resolution": outcome["bars_to_resolution"],
                    "hit_take_profit": outcome["hit_take_profit"],
                    "hit_stop_loss": outcome["hit_stop_loss"],
                    "expired": outcome["expired"],
                    "trace_id": run.get("trace_id") or (proposal or {}).get("trace_id"),
                }
            ],
            prefer="resolution=merge-duplicates,return=representation",
        )
        _sb_patch(
            "paper_trade_runs",
            f"id=eq.{_quote(run['id'])}",
            {
                "status": "finished",
                "finished_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        completed.append(run["id"])
        results.append(result_id)
    return {
        "running_runs_seen": len(runs),
        "runs_finished": completed,
        "replay_results_written": results,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(finish_once(limit=args.limit), indent=2))
