"""
trading/session_intelligence.py — Session-level performance intelligence.

Tracks win rate, P&L, and trade frequency by session (London, NY Open, Asia,
NY/London overlap) and time-of-day. Used by Hermes to recommend session
restrictions and identify edge decay.

NEXUS_DRY_RUN must be true. No live execution from this module.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Session definitions (UTC hours, inclusive)
SESSIONS = {
    "asia":      {"start": 0,  "end": 8,   "peak": (2, 5)},
    "london":    {"start": 7,  "end": 16,  "peak": (8, 11)},
    "ny_open":   {"start": 13, "end": 21,  "peak": (13, 16)},
    "overlap":   {"start": 13, "end": 16,  "peak": (13, 15)},  # London/NY overlap
}


def classify_session(dt: datetime) -> str:
    """Return the primary session name for a given UTC datetime."""
    h = dt.hour
    # Overlap takes priority
    if 13 <= h < 16:
        return "overlap"
    if 7 <= h < 16:
        return "london"
    if 13 <= h < 21:
        return "ny_open"
    return "asia"


def analyze_session_performance(trades: list[dict]) -> dict:
    """
    Compute per-session performance metrics from a list of trade dicts.

    Each trade dict must have:
        opened_at: ISO datetime string
        outcome: "win" | "loss"
        pnl_usd: float

    Returns a dict keyed by session name, each with win_rate, avg_pnl,
    trade_count, gross_profit, gross_loss.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)

    for trade in trades:
        try:
            opened = datetime.fromisoformat(str(trade.get("opened_at", "") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        session = classify_session(opened)
        buckets[session].append(trade)

    result = {}
    for session, session_trades in buckets.items():
        wins   = [t for t in session_trades if str(t.get("outcome", "")).lower() == "win"]
        losses = [t for t in session_trades if str(t.get("outcome", "")).lower() != "win"]
        gross_profit = sum(float(t.get("pnl_usd", 0) or 0) for t in wins)
        gross_loss   = abs(sum(float(t.get("pnl_usd", 0) or 0) for t in losses))
        result[session] = {
            "session":      session,
            "trade_count":  len(session_trades),
            "wins":         len(wins),
            "losses":       len(losses),
            "win_rate":     round(len(wins) / len(session_trades) * 100, 1) if session_trades else 0.0,
            "gross_profit": round(gross_profit, 2),
            "gross_loss":   round(gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else None,
            "avg_pnl_usd":  round(sum(float(t.get("pnl_usd", 0) or 0) for t in session_trades) / len(session_trades), 2)
                            if session_trades else 0.0,
        }

    return result


def best_session(performance: dict) -> str | None:
    """Return the session name with the highest win rate (minimum 5 trades)."""
    eligible = {s: v for s, v in performance.items() if v["trade_count"] >= 5}
    if not eligible:
        return None
    return max(eligible, key=lambda s: eligible[s]["win_rate"])


def worst_session(performance: dict) -> str | None:
    """Return the session name with the lowest win rate (minimum 5 trades)."""
    eligible = {s: v for s, v in performance.items() if v["trade_count"] >= 5}
    if not eligible:
        return None
    return min(eligible, key=lambda s: eligible[s]["win_rate"])


def detect_edge_decay(trades: list[dict], baseline_win_rate: float, window: int = 20) -> dict:
    """
    Detect edge decay over the last `window` trades.
    Returns {decaying: bool, current_wr: float, delta_pct: float, message: str}.
    """
    recent = trades[-window:] if len(trades) >= window else trades
    if not recent:
        return {"decaying": False, "current_wr": 0.0, "delta_pct": 0.0, "message": "insufficient data"}

    wins = sum(1 for t in recent if str(t.get("outcome", "")).lower() == "win")
    current_wr = wins / len(recent) * 100
    delta = current_wr - baseline_win_rate
    decaying = delta < -15  # more than 15% below baseline

    return {
        "decaying":    decaying,
        "current_wr":  round(current_wr, 1),
        "baseline_wr": round(baseline_win_rate, 1),
        "delta_pct":   round(delta, 1),
        "sample_size": len(recent),
        "message": (
            f"Edge deteriorating: win rate {current_wr:.1f}% vs baseline {baseline_win_rate:.1f}% "
            f"({delta:.1f}%). Strategy paused for review."
            if decaying else
            f"Edge stable: win rate {current_wr:.1f}% vs baseline {baseline_win_rate:.1f}% ({delta:+.1f}%)."
        ),
    }


def session_heatmap(trades: list[dict]) -> dict[str, list[float]]:
    """
    Build an hour-of-day win rate heatmap.
    Returns {session: [win_rate_hour_0, ..., win_rate_hour_23]}.
    """
    hour_buckets: dict[int, list[dict]] = defaultdict(list)

    for trade in trades:
        try:
            opened = datetime.fromisoformat(str(trade.get("opened_at", "") or "").replace("Z", "+00:00"))
        except Exception:
            continue
        hour_buckets[opened.hour].append(trade)

    hourly_wr = []
    for h in range(24):
        bucket = hour_buckets.get(h, [])
        if bucket:
            wins = sum(1 for t in bucket if str(t.get("outcome", "")).lower() == "win")
            hourly_wr.append(round(wins / len(bucket) * 100, 1))
        else:
            hourly_wr.append(None)

    return {"hourly_win_rate": hourly_wr, "sample_hours": [len(hour_buckets.get(h, [])) for h in range(24)]}
