"""
Portfolio Service.

Aggregates the full nexus portfolio state into append-only snapshots.
Identifies top performers and underperformers for kill/scale decisions.

Snapshot structure (matches portfolio_summary table):
  total_revenue     — all-time portfolio revenue
  monthly_revenue   — current month revenue
  active_instances  — count by status
  testing_instances
  scaled_instances
  killed_instances
  top_performers    — top 3 by monthly revenue
  underperformers   — bottom instances with low/zero revenue

Usage:
    from portfolio.portfolio_service import (
        take_snapshot, get_latest_snapshot,
        get_top_performers, get_underperformers,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('PortfolioService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Instance is underperforming if monthly revenue < this after N days active
UNDERPERFORM_THRESHOLD = 500.0
# Instance must be active at least this many days before flagging
MIN_ACTIVE_DAYS = 14


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
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


# ─── Portfolio state ──────────────────────────────────────────────────────────

def _get_status_counts() -> dict:
    rows = _sb_get("nexus_instances?select=status")
    counts = {'testing': 0, 'active': 0, 'scaled': 0, 'killed': 0}
    for r in rows:
        s = r.get('status', 'testing')
        counts[s] = counts.get(s, 0) + 1
    return counts


def get_top_performers(limit: int = 3) -> List[dict]:
    """Top instances by current month revenue."""
    from revenue_engine.revenue_service import get_top_revenue_instances
    period = datetime.now(timezone.utc).strftime('%Y-%m')
    top    = get_top_revenue_instances(period=period, limit=limit)

    result = []
    for item in top:
        iid    = item['instance_id']
        rows   = _sb_get(f"nexus_instances?id=eq.{iid}&select=id,niche,display_name,status&limit=1")
        detail = rows[0] if rows else {}
        result.append({
            'instance_id':  iid,
            'niche':        detail.get('niche', ''),
            'display_name': detail.get('display_name', ''),
            'status':       detail.get('status', ''),
            'monthly_rev':  item['revenue'],
        })
    return result


def get_underperformers(limit: int = 5) -> List[dict]:
    """
    Active/testing instances with revenue below threshold.
    Only flags instances older than MIN_ACTIVE_DAYS.
    """
    from revenue_engine.revenue_service import get_monthly_total

    period  = datetime.now(timezone.utc).strftime('%Y-%m')
    rows    = _sb_get(
        f"nexus_instances?status=in.(active,testing)&select=id,niche,display_name,status,created_at"
        f"&order=created_at.asc&limit=100"
    )

    now   = datetime.now(timezone.utc)
    under = []
    for r in rows:
        created_str = r.get('created_at', '')
        try:
            created = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
            age_days = (now - created).days
        except Exception:
            age_days = 0

        if age_days < MIN_ACTIVE_DAYS:
            continue

        monthly = get_monthly_total(instance_id=r['id'], period=period)
        if monthly < UNDERPERFORM_THRESHOLD:
            under.append({
                'instance_id':  r['id'],
                'niche':        r.get('niche', ''),
                'display_name': r.get('display_name', ''),
                'status':       r.get('status', ''),
                'monthly_rev':  monthly,
                'age_days':     age_days,
            })

    under.sort(key=lambda x: x['monthly_rev'])
    return under[:limit]


def take_snapshot() -> Optional[dict]:
    """
    Create an append-only portfolio snapshot.
    Called by portfolio_worker on schedule.
    """
    from revenue_engine.revenue_service import get_all_time_total, get_monthly_total

    period         = datetime.now(timezone.utc).strftime('%Y-%m')
    total_revenue  = get_all_time_total()
    monthly_rev    = get_monthly_total(period=period)
    status_counts  = _get_status_counts()
    top_performers = get_top_performers(3)
    underperformers = get_underperformers(5)

    row = {
        'total_revenue':     total_revenue,
        'monthly_revenue':   monthly_rev,
        'active_instances':  status_counts.get('active', 0),
        'testing_instances': status_counts.get('testing', 0),
        'scaled_instances':  status_counts.get('scaled', 0),
        'killed_instances':  status_counts.get('killed', 0),
        'top_performers':    top_performers,
        'underperformers':   underperformers,
    }
    result = _sb_post('portfolio_summary', row)
    if result:
        logger.info(
            f"Portfolio snapshot taken: monthly=${monthly_rev} "
            f"active={status_counts.get('active',0)} "
            f"testing={status_counts.get('testing',0)}"
        )
    return result


def get_latest_snapshot() -> Optional[dict]:
    """Return the most recent portfolio snapshot."""
    rows = _sb_get(
        "portfolio_summary?select=*&order=snapshot_at.desc&limit=1"
    )
    return rows[0] if rows else None


def get_snapshot_history(limit: int = 30) -> List[dict]:
    return _sb_get(
        f"portfolio_summary?select=*&order=snapshot_at.desc&limit={limit}"
    )


def get_portfolio_summary_text() -> str:
    """Human-readable summary of current portfolio state."""
    snap = get_latest_snapshot()
    if not snap:
        return "No portfolio snapshot available."

    top   = snap.get('top_performers') or []
    under = snap.get('underperformers') or []

    top_lines = '\n'.join(
        f"  • {p.get('display_name') or p.get('niche', '?')}: ${p.get('monthly_rev', 0):,.0f}/mo"
        for p in top
    ) or '  (none)'

    under_lines = '\n'.join(
        f"  • {u.get('display_name') or u.get('niche', '?')}: ${u.get('monthly_rev', 0):,.0f}/mo ({u.get('age_days',0)}d old)"
        for u in under
    ) or '  (none)'

    return (
        f"Portfolio snapshot — {snap.get('snapshot_at', '')[:10]}\n"
        f"Monthly revenue:  ${snap.get('monthly_revenue', 0):,.2f}\n"
        f"All-time revenue: ${snap.get('total_revenue', 0):,.2f}\n"
        f"Instances: active={snap.get('active_instances',0)} "
        f"testing={snap.get('testing_instances',0)} "
        f"scaled={snap.get('scaled_instances',0)} "
        f"killed={snap.get('killed_instances',0)}\n\n"
        f"Top performers:\n{top_lines}\n\n"
        f"Underperformers:\n{under_lines}"
    )
