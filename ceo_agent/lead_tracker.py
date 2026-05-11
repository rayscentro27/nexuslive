"""
Lead Tracker — Part 5.

CRUD helpers for the leads table + Hermes report generation.
10-stage funnel: new → contacted → qualified → proposal → negotiation → won → lost → cold
"""

import logging
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('LeadTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

FUNNEL_STAGES = ['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost', 'cold']


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


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def create_lead(name: str, email: str = '', phone: str = '', source: str = 'manual',
                business_name: str = '', estimated_value: float = 0,
                notes: str = '', assigned_to: str = 'owner') -> Optional[dict]:
    rows = _sb('leads', 'POST', {
        'name': name,
        'email': email or None,
        'phone': phone or None,
        'source': source,
        'business_name': business_name or None,
        'estimated_value': estimated_value or None,
        'notes': notes or None,
        'assigned_to': assigned_to,
        'next_followup_at': (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    }, prefer='return=representation')
    return rows[0] if rows else None


def update_lead_status(lead_id: str, status: str, notes: str = '') -> bool:
    if status not in FUNNEL_STAGES:
        return False
    body: dict = {'status': status, 'updated_at': datetime.now(timezone.utc).isoformat()}
    if notes:
        body['notes'] = notes
    if status == 'won':
        body['converted_at'] = datetime.now(timezone.utc).isoformat()
    _sb(f"leads?id=eq.{lead_id}", 'PATCH', body, prefer='return=minimal')
    return True


def log_contact(lead_id: str, followup_hours: int = 48) -> None:
    _sb(f"leads?id=eq.{lead_id}", 'PATCH', {
        'last_contacted_at': datetime.now(timezone.utc).isoformat(),
        'next_followup_at': (datetime.now(timezone.utc) + timedelta(hours=followup_hours)).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }, prefer='return=minimal')


def get_leads(status: str = '', limit: int = 50) -> list:
    path = f"leads?order=created_at.desc&limit={limit}"
    if status:
        path += f"&status=eq.{status}"
    return _sb(path)


def get_overdue_leads() -> list:
    cutoff = datetime.now(timezone.utc).isoformat()
    return _sb(
        f"leads?next_followup_at=lt.{cutoff}"
        f"&status=in.(new,contacted,qualified,proposal,negotiation)"
        f"&order=next_followup_at.asc&limit=20"
    )


# ─── Reports ──────────────────────────────────────────────────────────────────

def build_lead_report() -> str:
    """Build a Telegram-formatted lead pipeline report."""
    all_leads = _sb("leads?select=status,lead_score,estimated_value,created_at&limit=1000")
    if not all_leads:
        return "No leads in pipeline yet."

    by_stage: dict = {s: [] for s in FUNNEL_STAGES}
    for lead in all_leads:
        s = lead.get('status', 'new')
        by_stage.setdefault(s, []).append(lead)

    total_value = sum(float(l.get('estimated_value') or 0) for l in all_leads)
    won = by_stage.get('won', [])
    won_value = sum(float(l.get('estimated_value') or 0) for l in won)

    # 30-day new leads
    cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    new_30d = sum(1 for l in all_leads if (l.get('created_at') or '') > cutoff_30d)

    lines = [
        '<b>Lead Pipeline</b>',
        f"Total leads: {len(all_leads)} | New (30d): {new_30d}",
        f"Pipeline value: ${total_value:,.0f} | Won: ${won_value:,.0f}",
        '',
        '<b>Funnel Breakdown:</b>',
    ]
    stage_icons = {
        'new': '🆕', 'contacted': '📞', 'qualified': '✅', 'proposal': '📋',
        'negotiation': '🤝', 'won': '🏆', 'lost': '❌', 'cold': '🧊',
    }
    for stage in FUNNEL_STAGES:
        count = len(by_stage.get(stage, []))
        if count:
            icon = stage_icons.get(stage, '•')
            lines.append(f"{icon} {stage.title()}: {count}")

    overdue = get_overdue_leads()
    if overdue:
        lines.append(f"\n⚠️ Overdue followups: {len(overdue)}")

    return '\n'.join(lines)


def build_lead_summary_text() -> str:
    """Plain-text summary for CEO briefing inclusion."""
    all_leads = _sb("leads?select=status,estimated_value&limit=1000")
    if not all_leads:
        return "No leads."
    active = [l for l in all_leads if l.get('status') not in ('won', 'lost', 'cold')]
    won = [l for l in all_leads if l.get('status') == 'won']
    return (
        f"{len(all_leads)} total leads | {len(active)} active | {len(won)} won | "
        f"pipeline ${sum(float(l.get('estimated_value') or 0) for l in active):,.0f}"
    )
