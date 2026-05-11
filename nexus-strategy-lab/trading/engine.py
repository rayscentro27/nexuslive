"""
trading/engine.py — Modular demo trading engine.

Pulls reviewed strategies from strategy_library, simulates paper trades,
writes all events to Supabase, and produces metrics + Telegram report.

Safety:
  DRY_RUN=true (default) — all trades are synthetic paper trades.
  No broker connections are made. Safe to run at any time.

Usage:
  cd ~/nexus-ai/nexus-strategy-lab
  python3 -m trading.engine                    # run one batch
  python3 -m trading.engine --trades 5         # 5 trades per strategy
  python3 -m trading.engine --strategy-id <uuid>  # specific strategy only
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
settings.validate()

from db import supabase_client as db
from trading.account    import get_or_create_account, sync_account
from trading.simulator  import simulate_trade
from trading.journal    import write_journal_entry, write_outcome
from trading.metrics    import compute_metrics, write_metrics, notify_metrics

logger = logging.getLogger(__name__)

TENANT_ID = os.getenv('NEXUS_TENANT_ID', '')


# ── Strategy fetcher ──────────────────────────────────────────────────────────

def _fetch_strategies(strategy_id: str = None, limit: int = 5) -> list[dict]:
    """
    Fetch strategies that have been AI-reviewed and are eligible for demo trading.
    Filters: status in (review, approve, scored) with at least one score.
    """
    if strategy_id:
        rows = db.select('strategy_library', f'id=eq.{strategy_id}&select=*&limit=1')
        return rows

    # Get strategies with AI review scores ≥ 40 (eligible for demo)
    try:
        scores = db.select('strategy_scores',
                           f'total_score=gte.30&select=strategy_uuid,total_score'
                           f'&order=total_score.desc&limit={limit * 2}')
        if not scores:
            # Fallback: any scored strategy
            scores = db.select('strategy_scores',
                               f'select=strategy_uuid,total_score'
                               f'&order=total_score.desc&limit={limit}')
    except Exception as e:
        logger.error(f"Could not fetch strategy scores: {e}")
        return []

    strategy_ids = [s['strategy_uuid'] for s in scores if s.get('strategy_uuid')][:limit]

    strategies = []
    for sid in strategy_ids:
        try:
            rows = db.select('strategy_library', f'id=eq.{sid}&select=*&limit=1')
            if rows:
                strategies.append(rows[0])
        except Exception:
            pass

    return strategies


# ── Run writer ────────────────────────────────────────────────────────────────

def _create_run(account_id: str, strategy: dict, run_name: str) -> str | None:
    row = {
        'demo_account_id': account_id,
        'run_name':        run_name,
        'asset_class':     strategy.get('market') or 'multi',
        'run_status':      'running',
        'started_at':      datetime.now(timezone.utc).isoformat(),
    }
    if TENANT_ID:
        row['tenant_id'] = TENANT_ID
    if strategy.get('version_id'):
        row['strategy_version_id'] = strategy['version_id']

    try:
        inserted = db.insert('demo_trade_runs', row)
        return inserted.get('id')
    except Exception as e:
        logger.error(f"demo_trade_runs insert failed: {e}")
        return None


def _close_run(run_id: str, status: str = 'completed'):
    try:
        db.update('demo_trade_runs',
                  {'run_status': status,
                   'completed_at': datetime.now(timezone.utc).isoformat()},
                  f'id=eq.{run_id}')
    except Exception:
        pass


def _write_event(run_id: str, event: dict):
    try:
        db.insert('demo_trade_events', {
            'run_id':     run_id,
            'event_type': event.get('event_type', 'info'),
            'symbol':     event.get('symbol'),
            'side':       event.get('side'),
            'quantity':   event.get('quantity'),
            'price':      event.get('price'),
            'event_time': event.get('time'),
            'payload':    {k: v for k, v in event.items()
                          if k not in ('event_type','symbol','side','quantity','price','time')},
        })
    except Exception as e:
        logger.debug(f"event write failed: {e}")


# ── Core engine ───────────────────────────────────────────────────────────────

def run_demo_trades(
    trades_per_strategy: int = 3,
    strategy_id: str = None,
    strategy_limit: int = 3,
) -> dict:
    """
    Main entry point. Runs demo trades for eligible strategies.

    Returns summary dict: { strategies: int, trades: int, net_pnl: float,
                             win_rate: float, errors: int }
    """
    if settings.DRY_RUN:
        logger.info("DRY_RUN=true — running paper trades only (no broker connections)")

    account = get_or_create_account()
    acct_id = account.get('id')
    if not acct_id:
        logger.error("No demo account — cannot run trades")
        return {'strategies': 0, 'trades': 0, 'net_pnl': 0.0, 'win_rate': 0.0, 'errors': 1}

    strategies = _fetch_strategies(strategy_id=strategy_id, limit=strategy_limit)
    if not strategies:
        logger.warning("No eligible strategies found for demo trading")
        return {'strategies': 0, 'trades': 0, 'net_pnl': 0.0, 'win_rate': 0.0, 'errors': 0}

    total_trades = 0
    total_pnl    = 0.0
    total_wins   = 0
    errors       = 0

    for strategy in strategies:
        s_name = strategy.get('strategy_name') or strategy.get('title') or 'Unknown'
        s_id   = strategy['id']

        # Create a run for this strategy
        ts       = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M')
        run_name = f"{s_name[:40].replace(' ','_')}-{ts}"
        run_id   = _create_run(acct_id, strategy, run_name)
        if not run_id:
            errors += 1
            continue

        logger.info(f"Starting run '{run_name}' ({trades_per_strategy} trades) "
                    f"for strategy: {s_name[:60]}")

        run_trades = []

        for i in range(trades_per_strategy):
            try:
                trade = simulate_trade(strategy)
                if not trade:
                    continue

                # Write trade events
                for ev in trade.get('events', []):
                    ev['symbol']   = trade['symbol']
                    ev['side']     = trade['side']
                    ev['quantity'] = trade['quantity']
                    _write_event(run_id, ev)

                # Journal + outcome
                journal_id = write_journal_entry(trade, strategy)
                write_outcome(journal_id, trade)

                run_trades.append(trade)
                total_trades += 1
                total_pnl    += trade['pnl']
                if trade['outcome'] == 'win':
                    total_wins += 1

                logger.info(
                    f"  Trade {i+1}: {trade['symbol']} {trade['side'].upper()} "
                    f"→ {trade['outcome'].upper()} ${trade['pnl']:+.2f}"
                )

            except Exception as e:
                logger.error(f"Trade simulation error: {e}")
                errors += 1

        # Compute and save metrics for this run
        metrics = compute_metrics(run_trades)
        write_metrics(run_id, metrics)
        _close_run(run_id, 'completed')

        # Telegram notification
        notify_metrics(run_name, metrics, s_name)

    sync_account(acct_id)

    win_rate = round(total_wins / total_trades, 4) if total_trades else 0.0
    logger.info(
        f"Demo trading complete: strategies={len(strategies)} trades={total_trades} "
        f"pnl=${total_pnl:+.2f} win_rate={win_rate:.0%} errors={errors}"
    )
    return {
        'strategies': len(strategies),
        'trades':     total_trades,
        'net_pnl':    round(total_pnl, 2),
        'win_rate':   win_rate,
        'errors':     errors,
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser(description='Nexus Demo Trading Engine')
    parser.add_argument('--trades',      type=int, default=3,
                        help='Trades per strategy (default 3)')
    parser.add_argument('--strategies',  type=int, default=3,
                        help='Max strategies to run (default 3)')
    parser.add_argument('--strategy-id', type=str, default=None,
                        help='Run for a specific strategy UUID only')
    args = parser.parse_args()

    result = run_demo_trades(
        trades_per_strategy=args.trades,
        strategy_id=args.strategy_id,
        strategy_limit=args.strategies,
    )
    print(f"\nResult: {result}")
