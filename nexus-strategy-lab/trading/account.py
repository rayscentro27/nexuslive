"""
trading/account.py — Demo account management.

Creates or retrieves the paper trading account in Supabase.
One account per tenant, idempotent on account_label.
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

ACCOUNT_LABEL = os.getenv('DEMO_ACCOUNT_LABEL', 'nexus-demo-main')
TENANT_ID     = os.getenv('NEXUS_TENANT_ID', '')


def get_or_create_account() -> dict:
    """
    Return the demo account dict. Creates it if it doesn't exist.
    Saves the account id to DEMO_ACCOUNT_ID env var for this process.
    """
    # Check env override first
    existing_id = settings.DEMO_ACCOUNT_ID
    if existing_id:
        try:
            rows = db.select('demo_accounts', f'id=eq.{existing_id}&select=*&limit=1')
            if rows:
                return rows[0]
        except Exception:
            pass

    # Look up by label
    try:
        rows = db.select('demo_accounts',
                         f'account_label=eq.{ACCOUNT_LABEL}&select=*&limit=1')
        if rows:
            os.environ['DEMO_ACCOUNT_ID'] = rows[0]['id']
            return rows[0]
    except Exception as e:
        logger.warning(f"Could not look up demo account: {e}")

    # Create new
    row = {
        'account_label':      ACCOUNT_LABEL,
        'account_mode':       'paper',
        'provider':           'internal',
        'connection_status':  'active',
        'metadata_json': {
            'starting_balance': settings.DEMO_STARTING_BALANCE,
            'currency':         'USD',
            'dry_run':          settings.DRY_RUN,
            'created_by':       'trading_engine',
        },
    }
    if TENANT_ID:
        row['tenant_id'] = TENANT_ID

    try:
        account = db.insert('demo_accounts', row)
        os.environ['DEMO_ACCOUNT_ID'] = account['id']
        logger.info(f"Created demo account: {account['id']} ({ACCOUNT_LABEL})")
        return account
    except Exception as e:
        logger.error(f"Could not create demo account: {e}")
        return {'id': None, 'metadata_json': {'starting_balance': settings.DEMO_STARTING_BALANCE}}


def sync_account(account_id: str):
    """Update last_sync_at timestamp."""
    try:
        db.update('demo_accounts',
                  {'last_sync_at': datetime.now(timezone.utc).isoformat(),
                   'connection_status': 'active'},
                  f'id=eq.{account_id}')
    except Exception:
        pass
