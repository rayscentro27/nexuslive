"""
trading/simulator.py — Paper trade simulator.

Converts strategy_library rules into simulated trade events.
Uses demo price data (no live feed required) with realistic spread/slippage.

In DRY_RUN mode (default): simulates everything, writes to Supabase, no broker calls.
All price data is synthetic but parameterised from strategy metadata.
"""
import random
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Demo price seeds per asset class (mid price)
_PRICE_SEEDS = {
    'forex':    {'EURUSD': 1.0850, 'GBPUSD': 1.2650, 'USDJPY': 149.50,
                 'AUDUSD': 0.6420, 'USDCAD': 1.3650, 'NZDUSD': 0.5980},
    'crypto':   {'BTCUSD': 83500.0, 'ETHUSD': 1890.0, 'SOLUSD': 132.0},
    'equities': {'SPY': 510.0, 'QQQ': 425.0, 'AAPL': 195.0, 'NVDA': 825.0},
    'futures':  {'ES': 5250.0, 'NQ': 18200.0, 'CL': 72.50, 'GC': 3050.0},
    'multi':    {'EURUSD': 1.0850, 'SPY': 510.0},
}

_SPREAD = {'forex': 0.0002, 'crypto': 0.003, 'equities': 0.05, 'futures': 0.25, 'multi': 0.0002}


def _pick_symbol(asset_class: str, strategy: dict) -> str:
    """Pick a plausible symbol for this strategy."""
    # Try to get from strategy metadata
    syms = strategy.get('symbols') or []
    if syms and isinstance(syms, list):
        return str(syms[0]).upper()

    seeds = _PRICE_SEEDS.get(asset_class, _PRICE_SEEDS['multi'])
    return list(seeds.keys())[0]


def _simulate_price(symbol: str, asset_class: str, direction: str) -> dict:
    """Generate a synthetic price for entry/exit."""
    seeds = _PRICE_SEEDS.get(asset_class, _PRICE_SEEDS['multi'])
    mid   = seeds.get(symbol, list(seeds.values())[0])
    spread = _SPREAD.get(asset_class, 0.0002)

    # Add small random noise (±0.1% move)
    noise = mid * random.uniform(-0.001, 0.001)
    mid  += noise

    return {
        'mid':   round(mid, 5),
        'bid':   round(mid - spread / 2, 5),
        'ask':   round(mid + spread / 2, 5),
        'spread': spread,
    }


def _estimate_rr(strategy: dict) -> tuple[float, float]:
    """
    Estimate stop distance and R:R from risk rules.
    Returns (stop_pct, target_pct) as fractions of entry price.
    """
    rules_text = str(strategy.get('risk_rules') or {}).lower()
    # Look for R:R hints
    if '3:1' in rules_text or '3r' in rules_text:
        rr = 3.0
    elif '2:1' in rules_text or '2r' in rules_text:
        rr = 2.0
    else:
        rr = 2.0  # default

    stop_pct = 0.01   # 1% stop default
    return stop_pct, stop_pct * rr


def simulate_trade(strategy: dict) -> dict | None:
    """
    Simulate one paper trade from a strategy_library entry.

    Returns a dict with: symbol, side, entry_price, stop_loss, take_profit,
    quantity, pnl, outcome, duration_minutes, events[]
    """
    asset  = strategy.get('market') or 'multi'
    symbol = _pick_symbol(asset, strategy)
    setup  = strategy.get('setup_type') or 'general'

    # Determine side from setup type
    bearish_setups = {'reversal', 'mean_reversion'}
    side = 'sell' if setup in bearish_setups and random.random() < 0.4 else 'buy'

    entry_px = _simulate_price(symbol, asset, side)
    entry    = entry_px['ask'] if side == 'buy' else entry_px['bid']

    stop_pct, target_pct = _estimate_rr(strategy)

    if side == 'buy':
        stop_loss   = round(entry * (1 - stop_pct), 5)
        take_profit = round(entry * (1 + target_pct), 5)
    else:
        stop_loss   = round(entry * (1 + stop_pct), 5)
        take_profit = round(entry * (1 - target_pct), 5)

    # Quantity: fixed micro lot for demo
    qty = 0.01

    # Simulate outcome — weighted by strategy's deterministic score
    det_score = 50.0
    try:
        from db import supabase_client as db
        scores = db.select('strategy_scores',
                           f'strategy_uuid=eq.{strategy["id"]}&select=total_score&limit=1')
        if scores:
            det_score = float(scores[0].get('total_score') or 50.0)
    except Exception:
        pass

    # Win probability loosely tied to strategy quality (30–60%)
    win_prob = 0.30 + (det_score / 100.0) * 0.30

    won      = random.random() < win_prob
    duration = random.randint(15, 480)  # minutes

    if won:
        exit_price = take_profit
        pnl_pips   = abs(take_profit - entry) / entry * 10000
        pnl_usd    = round(pnl_pips * qty * 10, 2)
        outcome    = 'win'
    else:
        exit_price = stop_loss
        pnl_pips   = -abs(stop_loss - entry) / entry * 10000
        pnl_usd    = round(pnl_pips * qty * 10, 2)
        outcome    = 'loss'

    now       = datetime.now(timezone.utc)
    exit_time = now + timedelta(minutes=duration)

    return {
        'symbol':       symbol,
        'asset_class':  asset,
        'side':         side,
        'quantity':     qty,
        'entry_price':  entry,
        'stop_loss':    stop_loss,
        'take_profit':  take_profit,
        'exit_price':   exit_price,
        'pnl':          pnl_usd,
        'outcome':      outcome,
        'duration_min': duration,
        'opened_at':    now.isoformat(),
        'closed_at':    exit_time.isoformat(),
        'setup_type':   setup,
        'events': [
            {'event_type': 'open',  'price': entry,      'time': now.isoformat()},
            {'event_type': 'close', 'price': exit_price, 'time': exit_time.isoformat(),
             'reason': 'take_profit' if won else 'stop_loss'},
        ]
    }
