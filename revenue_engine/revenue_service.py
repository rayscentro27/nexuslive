"""
Revenue Service.

Records and queries revenue streams per instance.

Stream types (examples — extensible):
  funding_fee       — 10% success fee on funded amounts
  subscription      — monthly SaaS/signal access fees
  affiliate         — referral commissions
  ad_revenue        — advertising income
  trading_profit    — realized P&L from trading engine
  consulting        — one-off consulting fees

Period format: YYYY-MM  (e.g. "2026-03")
Upsert pattern: UNIQUE(instance_id, stream_type, period) → merge-duplicates

Usage:
    from revenue_engine.revenue_service import (
        record_revenue, get_instance_revenue,
        get_monthly_total, get_all_time_total,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('RevenueService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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


def _sb_post(path: str, body: dict, prefer: str = 'return=representation') -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = prefer
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            if 'minimal' in prefer:
                return {}
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _current_period() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


# ─── Core revenue recording ───────────────────────────────────────────────────

def record_revenue(
    stream_type: str,
    amount: float,
    transactions: int          = 1,
    instance_id: Optional[str] = None,
    period: Optional[str]      = None,
) -> Optional[dict]:
    """
    Record revenue for a stream type in a given period.
    Upserts — adds to existing revenue/transactions for that period.
    Note: Supabase merge-duplicates replaces, so we fetch + add first.
    """
    p = period or _current_period()

    # Fetch existing row to add to it
    filters = f"stream_type=eq.{stream_type}&period=eq.{p}"
    if instance_id:
        filters += f"&instance_id=eq.{instance_id}"
    existing = _sb_get(f"revenue_streams?{filters}&select=*&limit=1")

    if existing:
        row = existing[0]
        new_revenue      = float(row.get('revenue', 0)) + amount
        new_transactions = int(row.get('transactions', 0)) + transactions

        # Compute growth rate vs prior period
        growth_rate = _compute_growth_rate(
            instance_id=instance_id,
            stream_type=stream_type,
            current_period=p,
            current_revenue=new_revenue,
        )

        body: dict = {
            'stream_type':  stream_type,
            'period':       p,
            'revenue':      new_revenue,
            'transactions': new_transactions,
            'growth_rate':  growth_rate,
            'updated_at':   datetime.now(timezone.utc).isoformat(),
        }
        if instance_id:
            body['instance_id'] = instance_id

        return _sb_post(
            'revenue_streams',
            body,
            prefer='resolution=merge-duplicates,return=representation',
        )
    else:
        body = {
            'stream_type':  stream_type,
            'period':       p,
            'revenue':      amount,
            'transactions': transactions,
            'growth_rate':  0,
            'updated_at':   datetime.now(timezone.utc).isoformat(),
        }
        if instance_id:
            body['instance_id'] = instance_id
        return _sb_post(
            'revenue_streams',
            body,
            prefer='resolution=merge-duplicates,return=representation',
        )


def _compute_growth_rate(
    instance_id: Optional[str],
    stream_type: str,
    current_period: str,
    current_revenue: float,
) -> float:
    """Compute MoM growth rate vs prior period."""
    try:
        year, month = current_period.split('-')
        prior_month = int(month) - 1
        prior_year  = int(year)
        if prior_month == 0:
            prior_month = 12
            prior_year -= 1
        prior_period = f"{prior_year}-{prior_month:02d}"

        filters = f"stream_type=eq.{stream_type}&period=eq.{prior_period}"
        if instance_id:
            filters += f"&instance_id=eq.{instance_id}"
        rows = _sb_get(f"revenue_streams?{filters}&select=revenue&limit=1")
        if not rows:
            return 0.0
        prior_revenue = float(rows[0].get('revenue', 0))
        if prior_revenue == 0:
            return 100.0 if current_revenue > 0 else 0.0
        return round((current_revenue - prior_revenue) / prior_revenue * 100, 2)
    except Exception:
        return 0.0


# ─── Queries ──────────────────────────────────────────────────────────────────

def get_instance_revenue(
    instance_id: str,
    period: Optional[str] = None,
) -> List[dict]:
    """All revenue streams for an instance, optionally filtered by period."""
    parts = [f"instance_id=eq.{instance_id}&select=*&order=period.desc"]
    if period:
        parts[0] += f"&period=eq.{period}"
    return _sb_get(f"revenue_streams?{'&'.join(parts)}")


def get_monthly_total(
    instance_id: Optional[str] = None,
    period: Optional[str]      = None,
) -> float:
    """Total revenue across all streams for a given period."""
    p = period or _current_period()
    filters = f"period=eq.{p}&select=revenue"
    if instance_id:
        filters += f"&instance_id=eq.{instance_id}"
    rows = _sb_get(f"revenue_streams?{filters}")
    return round(sum(float(r.get('revenue', 0)) for r in rows), 2)


def get_all_time_total(instance_id: Optional[str] = None) -> float:
    """Total revenue all-time for an instance (or entire portfolio)."""
    filters = "select=revenue"
    if instance_id:
        filters += f"&instance_id=eq.{instance_id}"
    rows = _sb_get(f"revenue_streams?{filters}")
    return round(sum(float(r.get('revenue', 0)) for r in rows), 2)


def get_revenue_by_stream(period: Optional[str] = None) -> dict:
    """Revenue broken down by stream_type for a period."""
    p = period or _current_period()
    rows = _sb_get(f"revenue_streams?period=eq.{p}&select=stream_type,revenue")
    by_stream: dict = {}
    for r in rows:
        st = r.get('stream_type', 'unknown')
        by_stream[st] = by_stream.get(st, 0) + float(r.get('revenue', 0))
    return by_stream


def get_top_revenue_instances(period: Optional[str] = None, limit: int = 5) -> List[dict]:
    """Return instances ranked by revenue for a period."""
    p = period or _current_period()
    rows = _sb_get(
        f"revenue_streams?period=eq.{p}&select=instance_id,revenue&order=revenue.desc&limit={limit * 3}"
    )
    # Aggregate by instance
    totals: dict = {}
    for r in rows:
        iid = r.get('instance_id')
        if iid:
            totals[iid] = totals.get(iid, 0) + float(r.get('revenue', 0))

    sorted_instances = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return [
        {'instance_id': iid, 'revenue': rev}
        for iid, rev in sorted_instances[:limit]
    ]
