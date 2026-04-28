"""
trading/journal.py — Paper trading journal writer.

Writes paper_trading_journal_entries + paper_trading_outcomes for each
simulated trade. These feed the portal's trade journal UI.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timezone

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
from db import supabase_client as db

logger = logging.getLogger(__name__)

TENANT_ID = os.getenv('NEXUS_TENANT_ID', '')


def write_journal_entry(trade: dict, strategy: dict) -> str | None:
    """
    Write a paper_trading_journal_entries row.
    Returns journal entry id or None.
    """
    thesis = (
        f"{strategy.get('setup_type','?').replace('_',' ').title()} setup on "
        f"{trade['symbol']} ({trade['asset_class']}). "
        f"Strategy: {strategy.get('strategy_name','?')[:80]}."
    )

    row = {
        'asset_class':  trade['asset_class'],
        'symbol':       trade['symbol'],
        'timeframe':    strategy.get('timeframes', [None])[0] if strategy.get('timeframes') else None,
        'thesis':       thesis[:500],
        'entry_idea':   str(strategy.get('entry_rules') or '')[:500],
        'stop_loss':    trade['stop_loss'],
        'target_price': trade['take_profit'],
        'risk_percent': 1.0,
        'tags':         [strategy.get('setup_type'), trade['asset_class'], 'demo', 'paper'],
        'entry_status': 'closed',
        'opened_at':    trade['opened_at'],
        'closed_at':    trade['closed_at'],
    }
    if TENANT_ID:
        row['tenant_id'] = TENANT_ID
    if strategy.get('version_id'):
        row['strategy_version_id'] = strategy['version_id']

    try:
        inserted = db.insert('paper_trading_journal_entries', row)
        return inserted.get('id')
    except Exception as e:
        logger.error(f"journal_entries insert failed: {e}")
        return None


def write_outcome(journal_id: str, trade: dict) -> str | None:
    """
    Write a paper_trading_outcomes row linked to a journal entry.
    Returns outcome id or None.
    """
    if not journal_id:
        return None

    entry = trade['entry_price']
    exit_ = trade['exit_price']
    pnl_pct = round((exit_ - entry) / entry * 100, 4) if entry else 0.0
    if trade['side'] == 'sell':
        pnl_pct = -pnl_pct

    # MFE / MAE approximations
    if trade['outcome'] == 'win':
        mfe = abs(trade['take_profit'] - entry)
        mae = abs(trade['stop_loss']   - entry) * 0.3  # never hit stop
    else:
        mfe = abs(trade['take_profit'] - entry) * 0.4  # never reached target
        mae = abs(trade['stop_loss']   - entry)

    row = {
        'journal_entry_id':       journal_id,
        'result_label':           trade['outcome'],
        'pnl_amount':             trade['pnl'],
        'pnl_percent':            pnl_pct,
        'max_favorable_excursion': round(mfe, 5),
        'max_adverse_excursion':   round(mae, 5),
        'notes': (
            f"Simulated {trade['duration_min']}min trade. "
            f"Entry {entry} → Exit {exit_}. "
            f"{'TP hit' if trade['outcome']=='win' else 'SL hit'}."
        ),
    }

    try:
        inserted = db.insert('paper_trading_outcomes', row)
        return inserted.get('id')
    except Exception as e:
        logger.error(f"paper_trading_outcomes insert failed: {e}")
        return None
