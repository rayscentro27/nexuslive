"""
Business Unit Registry.

Manages business_units and business_configs in Supabase.

Each business unit is an isolated logical entity (funding, trading, grants, saas)
sharing the same Supabase + Telegram infrastructure but with separate:
  - commission models
  - prompt templates
  - agent configurations
  - funnel stages

Default units are seeded by SQL migration. Use this module to read/write configs
and route agent logic per unit.

Usage:
    from business_units.business_registry import get_unit_config, set_unit_config

    config = get_unit_config('nexus_funding')
    commission = float(config.get('commission_rate', '0.10'))
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, List, Dict

logger = logging.getLogger('BusinessRegistry')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Default configs applied if not overridden in DB
_DEFAULT_CONFIGS: Dict[str, Dict[str, str]] = {
    'nexus_funding': {
        'commission_rate':   '0.10',
        'min_funding':       '5000',
        'max_funding':       '5000000',
        'min_credit_score':  '550',
        'fee_description':   '10% of funded amount, paid on success only',
        'telegram_channel':  'default',
    },
    'nexus_trading': {
        'subscription_price': '97',
        'subscription_period': 'monthly',
        'signal_frequency':   'daily',
        'telegram_channel':  'default',
    },
    'nexus_grants': {
        'success_fee':        '0.08',
        'retainer':           '0',
        'min_grant_size':     '10000',
        'telegram_channel':  'default',
    },
    'nexus_saas': {
        'monthly_price':      '297',
        'trial_days':         '14',
        'telegram_channel':  'default',
    },
}


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"PATCH {path} → {e}")
        return False


# ─── Units ────────────────────────────────────────────────────────────────────

def get_unit(unit_name: str) -> Optional[dict]:
    import urllib.parse
    rows = _sb_get(
        f"business_units?unit_name=eq.{urllib.parse.quote(unit_name)}&select=*&limit=1"
    )
    return rows[0] if rows else None


def get_all_units(active_only: bool = True) -> List[dict]:
    filter_str = "&status=eq.active" if active_only else ""
    return _sb_get(f"business_units?select=*{filter_str}&order=unit_name.asc")


# ─── Configs ──────────────────────────────────────────────────────────────────

def get_unit_config(unit_name: str) -> Dict[str, str]:
    """
    Return merged config for a business unit.
    DB values override defaults.
    """
    unit = get_unit(unit_name)
    if not unit:
        return _DEFAULT_CONFIGS.get(unit_name, {}).copy()

    unit_id = unit['id']
    rows    = _sb_get(
        f"business_configs?unit_id=eq.{unit_id}&select=config_key,config_value&limit=200"
    )
    config = _DEFAULT_CONFIGS.get(unit_name, {}).copy()
    for r in rows:
        config[r['config_key']] = r.get('config_value', '')

    return config


def set_unit_config(unit_name: str, key: str, value: str) -> bool:
    """Set or update a single config value for a business unit."""
    unit = get_unit(unit_name)
    if not unit:
        logger.warning(f"Business unit not found: {unit_name}")
        return False

    unit_id = unit['id']
    # Try upsert
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/business_configs"
    body = json.dumps({'unit_id': unit_id, 'config_key': key, 'config_value': value}).encode()
    h    = _headers()
    h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    req  = urllib.request.Request(url, data=body, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            logger.info(f"Config set: {unit_name}.{key}={value}")
            return True
    except Exception as e:
        logger.error(f"Set config → {e}")
        return False


def ensure_default_configs() -> int:
    """
    Seed default configs for all business units if not already present.
    Returns count of configs written.
    """
    written = 0
    for unit_name, defaults in _DEFAULT_CONFIGS.items():
        unit = get_unit(unit_name)
        if not unit:
            continue
        for key, value in defaults.items():
            ok = set_unit_config(unit_name, key, value)
            if ok:
                written += 1
    return written


def get_commission_rate(unit_name: str = 'nexus_funding') -> float:
    config = get_unit_config(unit_name)
    try:
        return float(config.get('commission_rate', '0.10'))
    except (ValueError, TypeError):
        return 0.10
