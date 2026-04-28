"""
Signal Candidate Ingest Service.

Converts a risk-gate-approved tv_normalized_signals row into a signal_candidates
staging record. This is the entry point for the scoring pipeline.

Flow:
  tv_normalized_signals (status='approved')
      → ingest_signal_candidate()
      → signal_candidates (review_status='new')

Key rules:
  - Idempotent: if a signal_candidates row already exists for this source_signal_id
    the function returns that row's id without creating a duplicate.
  - Raw payload is stored verbatim (JSONB) for full audit trail.
  - Zones are normalised to { "price": <float> } JSONB objects.
  - market_type is inferred from symbol if not supplied.
  - direction is normalised: 'buy'/'long' → 'long', 'sell'/'short' → 'short'.

Usage:
  from signal_candidate_ingest_service import ingest_signal_candidate
  candidate_id = ingest_signal_candidate(signal_row, ai_review)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('SignalCandidateIngestService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _sb_insert(table: str, data: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method='POST',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'return=representation',
        }
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())
        return rows[0] if rows else {}


# ─── Normalisation helpers ─────────────────────────────────────────────────────

def _normalise_direction(side: str) -> str:
    s = (side or '').lower().strip()
    if s in ('buy', 'long'):
        return 'long'
    if s in ('sell', 'short'):
        return 'short'
    return s or None


_CRYPTO_SUFFIXES  = ('BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'USDT', 'USDC')
_FOREX_PAIRS      = {
    'EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCHF',
    'NZDUSD', 'USDCAD', 'EURJPY', 'GBPJPY', 'EURGBP',
}
_INDEX_SYMBOLS    = ('SPX', 'SPY', 'QQQ', 'NDX', 'DJI', 'US30', 'NAS100', 'US500')
_COMMODITY_SYMS   = ('GOLD', 'XAUUSD', 'SILVER', 'XAGUSD', 'OIL', 'CRUDE', 'NATGAS')
_FUTURES_SUFFIXES = ('F', 'H', 'M', 'U', 'Z')  # CME delivery codes — rough heuristic


def _infer_market_type(symbol: str) -> str:
    s = (symbol or '').upper().replace('/', '').replace('-', '')
    # Commodities first — XAUUSD/XAGUSD would otherwise match generic forex heuristic
    if any(s.startswith(c) for c in _COMMODITY_SYMS) or s in _COMMODITY_SYMS:
        return 'commodities'
    if s in _FOREX_PAIRS or (len(s) == 6 and s[:3].isalpha() and s[3:].isalpha()):
        return 'forex'
    if any(s.endswith(c) for c in ('USDT', 'USDC', 'BTC', 'ETH')) or any(s.startswith(c) for c in _CRYPTO_SUFFIXES):
        return 'crypto'
    if any(s.startswith(c) for c in _INDEX_SYMBOLS) or s in _INDEX_SYMBOLS:
        return 'indices'
    if len(s) <= 5 and s[-1] in _FUTURES_SUFFIXES:
        return 'futures'
    if len(s) <= 5 and s.isalpha():
        return 'equity'
    return None


def _make_zone(price_val) -> Optional[dict]:
    """Wrap a raw price value into a { "price": float } zone dict."""
    if price_val is None:
        return None
    try:
        p = float(price_val)
        return {'price': p} if p > 0 else None
    except (TypeError, ValueError):
        return None


def _normalise_timeframe(raw_tf) -> Optional[str]:
    """Normalise timeframe to a consistent label."""
    mapping = {
        '1':   '1m', '3': '3m', '5': '5m', '15': '15m', '30': '30m',
        '60':  '1h', '240': '4h', '1440': '1D', '10080': '1W',
        '1m':  '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
        '1h':  '1h', '4h': '4h', '1d': '1D', '1w': '1W', '1mo': '1MO',
        'd':   '1D', 'w':  '1W',
    }
    raw = str(raw_tf or '').strip().lower()
    return mapping.get(raw, raw or None)


# ─── Idempotency check ────────────────────────────────────────────────────────

def _candidate_exists(source_signal_id: str) -> Optional[str]:
    """Return the existing candidate id if one already exists for this source signal."""
    try:
        rows = _sb_get(
            f"signal_candidates"
            f"?source_signal_id=eq.{source_signal_id}"
            f"&select=id&limit=1"
        )
        return rows[0]['id'] if rows else None
    except Exception as e:
        logger.warning(f"Idempotency check failed: {e}")
        return None


# ─── Public API ───────────────────────────────────────────────────────────────

def ingest_signal_candidate(
    signal: dict,
    ai_review: dict,
    tenant_id: str = None,
) -> Optional[str]:
    """
    Create a signal_candidates row from a risk-gate-approved tv_normalized_signals row.

    Args:
        signal:    The tv_normalized_signals dict (as returned by signal_poller).
        ai_review: The AI review dict from signal_reviewer.review_signal().
        tenant_id: Optional tenant UUID for multi-tenant isolation.

    Returns:
        The UUID of the signal_candidates row, or None on failure.
    """
    source_signal_id = str(signal.get('id', ''))
    symbol           = (signal.get('symbol') or '').upper()

    if not source_signal_id or not symbol:
        logger.error("ingest_signal_candidate: missing id or symbol in signal")
        return None

    # Idempotency — don't duplicate
    existing = _candidate_exists(source_signal_id)
    if existing:
        logger.info(f"Candidate already exists for signal {source_signal_id}: {existing}")
        return existing

    direction  = _normalise_direction(signal.get('side') or signal.get('direction') or '')
    timeframe  = _normalise_timeframe(signal.get('timeframe'))
    market_type = signal.get('market_type') or _infer_market_type(symbol)

    entry_zone  = _make_zone(signal.get('entry_price'))
    stop_zone   = _make_zone(signal.get('stop_loss'))
    target_zone = _make_zone(signal.get('take_profit'))

    # Embed ai_review into raw_payload for downstream services
    raw_payload = {**signal}
    if ai_review:
        raw_payload['_ai_review'] = ai_review

    row = {
        'source':          'tradingview',
        'source_signal_id': source_signal_id,
        'symbol':           symbol,
        'market_type':      market_type,
        'setup_type':       signal.get('strategy_id') or signal.get('setup_type') or None,
        'direction':        direction,
        'timeframe':        timeframe,
        'entry_zone':       json.dumps(entry_zone)  if entry_zone  else None,
        'stop_zone':        json.dumps(stop_zone)   if stop_zone   else None,
        'target_zone':      json.dumps(target_zone) if target_zone else None,
        'raw_payload':      json.dumps(raw_payload),
        'review_status':    'new',
        'updated_at':       datetime.now(timezone.utc).isoformat(),
    }
    if tenant_id:
        row['tenant_id'] = tenant_id

    try:
        inserted = _sb_insert('signal_candidates', row)
        candidate_id = inserted.get('id')
        if not candidate_id:
            logger.error(f"Insert returned no id for signal {source_signal_id}")
            return None
        logger.info(f"Ingested candidate {candidate_id} ← signal {source_signal_id} ({symbol} {direction})")
        return candidate_id

    except Exception as e:
        logger.error(f"Failed to ingest signal {source_signal_id}: {e}")
        return None
