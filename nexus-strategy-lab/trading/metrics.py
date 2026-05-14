"""
trading/metrics.py — Trade metrics calculator + Supabase writer.

Computes: net P&L, win rate, max drawdown, stability score.
Writes to demo_trade_metrics and sends Telegram summary.
"""
import sys
import logging
import math
from pathlib import Path

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
from db import supabase_client as db

logger = logging.getLogger(__name__)


def compute_metrics(trades: list[dict]) -> dict:
    """
    Compute performance metrics from a list of completed trades.

    Args:
        trades: list of trade dicts with 'pnl', 'outcome' keys

    Returns:
        dict with trade_count, net_pnl, win_rate, max_drawdown,
              stability_score, recommendation
    """
    if not trades:
        return {
            'trade_count': 0, 'net_pnl': 0.0, 'win_rate': 0.0,
            'max_drawdown': 0.0, 'stability_score': 0.0,
            'recommendation': 'insufficient_data',
        }

    trade_count = len(trades)
    pnls        = [t.get('pnl', 0.0) for t in trades]
    wins        = sum(1 for t in trades if t.get('outcome') == 'win')

    net_pnl  = round(sum(pnls), 2)
    win_rate = round(wins / trade_count, 4)

    # Max drawdown (peak-to-trough on cumulative P&L curve)
    cumulative = []
    running = 0.0
    for p in pnls:
        running += p
        cumulative.append(running)

    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd
    max_drawdown = round(max_dd, 2)

    # Stability score: 0–100
    # Components: win rate, positive expectancy, low drawdown, trade count
    wr_score    = win_rate * 40                              # max 40
    exp_score   = 20 if net_pnl > 0 else 0                  # max 20
    dd_score    = max(0, 20 * (1 - max_drawdown / max(abs(net_pnl), 1)))  # max 20
    count_score = min(20, trade_count * 2)                   # max 20 at 10 trades
    stability   = round(wr_score + exp_score + dd_score + count_score, 1)

    # Recommendation
    if stability >= 65 and win_rate >= 0.5 and net_pnl > 0:
        recommendation = 'promote'
    elif stability >= 40:
        recommendation = 'continue'
    else:
        recommendation = 'review'

    return {
        'trade_count':   trade_count,
        'net_pnl':       net_pnl,
        'win_rate':      win_rate,
        'max_drawdown':  max_drawdown,
        'stability_score': stability,
        'recommendation': recommendation,
    }


def write_metrics(run_id: str, metrics: dict) -> str | None:
    """Persist metrics to demo_trade_metrics."""
    try:
        inserted = db.insert('demo_trade_metrics', {'run_id': run_id, **metrics})
        metrics_id = inserted.get('id')
        logger.info(
            f"Metrics saved: run={run_id[:8]} trades={metrics['trade_count']} "
            f"pnl={metrics['net_pnl']} wr={metrics['win_rate']:.0%} "
            f"stability={metrics['stability_score']} rec={metrics['recommendation']}"
        )
        return metrics_id
    except Exception as e:
        logger.error(f"demo_trade_metrics insert failed: {e}")
        return None


def notify_metrics(run_name: str, metrics: dict, strategy_name: str = ''):
    """Send Telegram summary of run metrics."""
    rec_emoji = {'promote': '🟢', 'continue': '🟡', 'review': '🔴'}.get(
        metrics.get('recommendation', ''), '⚪')
    text = (
        f"*Demo Trade Run Complete* {rec_emoji}\n"
        f"Run: `{run_name}`\n"
        f"Strategy: {strategy_name[:50] or 'N/A'}\n\n"
        f"Trades: {metrics['trade_count']} | "
        f"Win rate: {metrics['win_rate']:.0%}\n"
        f"Net P&L: ${metrics['net_pnl']:+.2f} | "
        f"Max DD: ${metrics['max_drawdown']:.2f}\n"
        f"Stability: {metrics['stability_score']}/100 → *{metrics['recommendation'].upper()}*"
    )
    try:
        from lib.telegram_notification_policy import should_send_telegram_notification
        from lib.hermes_gate import send as gate_send

        allowed, _ = should_send_telegram_notification('run_summary')
        if not allowed:
            return
        gate_send(text, event_type='run_summary', severity='summary')
    except Exception:
        pass
