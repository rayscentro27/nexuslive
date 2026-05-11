"""
Revenue Tracker — Part 6.

Logs and reports on 12 revenue event types.
Tracks MRR, commissions, concierge fees, and one-time events.
"""

import logging
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('RevenueTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

MRR_TYPES = {'subscription_start', 'upgrade', 'downgrade', 'churn'}
ONE_TIME_TYPES = {
    'grant_payout', 'loan_funded', 'commission_earned', 'concierge_fee',
    'referral_bonus', 'partner_deal', 'content_sale', 'training_sale',
}
ALL_EVENT_TYPES = MRR_TYPES | ONE_TIME_TYPES


def _sb(path: str, method: str = 'GET', body: Optional[dict] = None, prefer: str = '') -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }
    if prefer:
        headers['Prefer'] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())
            return result if isinstance(result, list) else ([result] if result else [])
    except Exception as e:
        logger.warning(f"{method} {path}: {e}")
        return []


# ─── Logging ──────────────────────────────────────────────────────────────────

def log_revenue_event(event_type: str, amount: float, client_id: str = '',
                      lead_id: str = '', description: str = '', notes: str = '') -> Optional[dict]:
    if event_type not in ALL_EVENT_TYPES:
        logger.warning(f"Unknown revenue event type: {event_type}")
        return None
    period_month = datetime.now(timezone.utc).strftime('%Y-%m')
    body: dict = {
        'event_type': event_type,
        'amount': round(amount, 2),
        'period_month': period_month,
        'description': description or None,
        'notes': notes or None,
    }
    if client_id:
        body['client_id'] = client_id
    if lead_id:
        body['lead_id'] = lead_id
    rows = _sb('revenue_events', 'POST', body, prefer='return=representation')
    return rows[0] if rows else None


# ─── Queries ──────────────────────────────────────────────────────────────────

def get_mrr(month: str = '') -> float:
    """Current MRR = sum of subscription_start + upgrade - downgrade - churn for the month."""
    if not month:
        month = datetime.now(timezone.utc).strftime('%Y-%m')
    rows = _sb(
        f"revenue_events?period_month=eq.{month}"
        f"&event_type=in.(subscription_start,upgrade,downgrade,churn)"
        f"&select=event_type,amount&limit=1000"
    )
    mrr = 0.0
    for r in rows:
        amt = float(r.get('amount', 0))
        if r.get('event_type') in ('subscription_start', 'upgrade'):
            mrr += amt
        elif r.get('event_type') in ('downgrade', 'churn'):
            mrr -= amt
    return round(mrr, 2)


def get_revenue_this_month() -> dict:
    month = datetime.now(timezone.utc).strftime('%Y-%m')
    rows = _sb(f"revenue_events?period_month=eq.{month}&select=event_type,amount&limit=2000")
    by_type: dict = {}
    total = 0.0
    for r in rows:
        t = r.get('event_type', 'unknown')
        amt = float(r.get('amount', 0))
        by_type[t] = by_type.get(t, 0.0) + amt
        total += amt
    return {'total': round(total, 2), 'by_type': by_type, 'month': month}


def get_revenue_last_n_days(days: int = 7) -> float:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sb(f"revenue_events?created_at=gt.{cutoff}&select=amount&limit=2000")
    return round(sum(float(r.get('amount', 0)) for r in rows), 2)


def get_commissions_this_month() -> float:
    month = datetime.now(timezone.utc).strftime('%Y-%m')
    rows = _sb(
        f"revenue_events?period_month=eq.{month}"
        f"&event_type=eq.commission_earned&select=amount&limit=500"
    )
    return round(sum(float(r.get('amount', 0)) for r in rows), 2)


def get_concierge_revenue() -> float:
    month = datetime.now(timezone.utc).strftime('%Y-%m')
    rows = _sb(
        f"revenue_events?period_month=eq.{month}"
        f"&event_type=eq.concierge_fee&select=amount&limit=500"
    )
    return round(sum(float(r.get('amount', 0)) for r in rows), 2)


# ─── Reports ──────────────────────────────────────────────────────────────────

def build_revenue_report() -> str:
    month_data = get_revenue_this_month()
    mrr = get_mrr()
    commissions = get_commissions_this_month()
    concierge = get_concierge_revenue()
    last_7d = get_revenue_last_n_days(7)

    lines = [
        '<b>Revenue Report</b>',
        f"Month: {month_data['month']}",
        f"Total this month: <b>${month_data['total']:,.2f}</b>",
        f"MRR (subscriptions): ${mrr:,.2f}",
        f"Last 7 days: ${last_7d:,.2f}",
        f"Commissions: ${commissions:,.2f}",
        f"Concierge fees: ${concierge:,.2f}",
    ]

    by_type = month_data.get('by_type', {})
    if by_type:
        lines.append('\n<b>By Type:</b>')
        for t, amt in sorted(by_type.items(), key=lambda x: -x[1]):
            lines.append(f"  {t.replace('_', ' ').title()}: ${amt:,.2f}")

    return '\n'.join(lines)


def build_revenue_summary_text() -> str:
    month_data = get_revenue_this_month()
    mrr = get_mrr()
    return (
        f"MRR ${mrr:,.2f} | Month total ${month_data['total']:,.2f} | "
        f"7d ${get_revenue_last_n_days(7):,.2f}"
    )
