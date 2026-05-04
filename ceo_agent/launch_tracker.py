"""
Launch Tracker — Parts 7 & 8.

Records and reports on launch KPIs (daily/weekly/monthly).
Also generates daily launch checklists, content topics, and outreach targets.
"""

import logging
import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('LaunchTracker')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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


def _week_label() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def _today_label() -> str:
    return datetime.now(timezone.utc).date().isoformat()


# ─── Recording ────────────────────────────────────────────────────────────────

def record_metric(metric_name: str, value: float, target: float = 0,
                  unit: str = 'count', period: str = 'daily',
                  period_label: str = '', notes: str = '') -> None:
    if not period_label:
        period_label = _week_label() if period == 'weekly' else _today_label()
    _sb('launch_metrics', 'POST', {
        'metric_name': metric_name,
        'metric_value': round(value, 4),
        'target_value': round(target, 4) if target else None,
        'unit': unit,
        'period': period,
        'period_label': period_label,
        'notes': notes or None,
    }, prefer='return=minimal')


def upsert_metric(metric_name: str, value: float, target: float = 0,
                  unit: str = 'count', period: str = 'daily',
                  period_label: str = '', notes: str = '') -> None:
    """Upsert by (metric_name, period, period_label)."""
    if not period_label:
        period_label = _week_label() if period == 'weekly' else _today_label()
    _sb('launch_metrics', 'POST', {
        'metric_name': metric_name,
        'metric_value': round(value, 4),
        'target_value': round(target, 4) if target else None,
        'unit': unit,
        'period': period,
        'period_label': period_label,
        'notes': notes or None,
    }, prefer='resolution=merge-duplicates,return=minimal')


# ─── Queries ──────────────────────────────────────────────────────────────────

def get_today_metrics() -> list:
    return _sb(f"launch_metrics?period=eq.daily&period_label=eq.{_today_label()}&order=metric_name.asc&limit=50")


def get_week_metrics() -> list:
    return _sb(f"launch_metrics?period=eq.weekly&period_label=eq.{_week_label()}&order=metric_name.asc&limit=50")


def get_recent_metrics(days: int = 7) -> list:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    return _sb(f"launch_metrics?period_label=gte.{cutoff}&order=period_label.desc,metric_name.asc&limit=200")


# ─── Reports ──────────────────────────────────────────────────────────────────

def build_launch_report(period: str = 'daily') -> str:
    metrics = get_today_metrics() if period == 'daily' else get_week_metrics()
    label = _today_label() if period == 'daily' else _week_label()

    if not metrics:
        return f"No {period} launch metrics recorded for {label}."

    lines = [f'<b>Launch Report ({period.title()}) — {label}</b>']
    on_track, behind, no_target = [], [], []

    for m in metrics:
        val = float(m.get('metric_value', 0))
        tgt = m.get('target_value')
        name = m.get('metric_name', '?')
        unit = m.get('unit', '')
        unit_str = f" {unit}" if unit not in ('count', '') else ''

        if tgt:
            tgt_f = float(tgt)
            pct = (val / tgt_f * 100) if tgt_f else 0
            entry = f"{name}: {val:.1f}{unit_str} / {tgt_f:.1f} ({pct:.0f}%)"
            if pct >= 100:
                on_track.append(f"✅ {entry}")
            elif pct >= 70:
                behind.append(f"🔶 {entry}")
            else:
                behind.append(f"❌ {entry}")
        else:
            no_target.append(f"• {name}: {val:.1f}{unit_str}")

    if on_track:
        lines.append('\n<b>On Track:</b>')
        lines.extend(on_track)
    if behind:
        lines.append('\n<b>Needs Attention:</b>')
        lines.extend(behind)
    if no_target:
        lines.append('\n<b>Tracked (no target):</b>')
        lines.extend(no_target)

    return '\n'.join(lines)


# ─── Part 8: Daily Checklist & Content Topics ─────────────────────────────────

def build_daily_checklist() -> str:
    """Generate today's launch execution checklist."""
    today = datetime.now(timezone.utc).strftime('%A, %B %d')
    overdue_leads = _sb(
        f"leads?next_followup_at=lt.{datetime.now(timezone.utc).isoformat()}"
        f"&status=in.(new,contacted,qualified)&select=name&limit=5"
    )
    pending_approvals = _sb("owner_approval_queue?status=eq.pending&select=id&limit=10")
    grant_deadlines = _sb(
        f"grants_catalog?deadline=lte.{(datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat()}"
        f"&deadline=gte.{datetime.now(timezone.utc).date().isoformat()}"
        f"&is_active=eq.true&select=title,deadline&limit=5"
    )

    lines = [f'<b>Daily Launch Checklist — {today}</b>', '']

    lines.append('<b>Morning Actions:</b>')
    lines.append('☐ Review overnight alerts and AI reports')
    lines.append('☐ Check and respond to client messages')
    if overdue_leads:
        lines.append(f"☐ Follow up with {len(overdue_leads)} overdue leads")
    if pending_approvals:
        lines.append(f"☐ Review {len(pending_approvals)} pending approvals: /approvals")
    if grant_deadlines:
        lines.append(f"☐ Grant deadlines this week: {', '.join(g.get('title','?')[:25] for g in grant_deadlines[:3])}")
    lines.append('☐ Post daily content piece (social/blog/email)')
    lines.append('')

    lines.append('<b>Sales Actions:</b>')
    lines.append('☐ Add 3+ new leads to pipeline')
    lines.append('☐ Send 5+ personalized outreach messages')
    lines.append('☐ Follow up on proposal-stage leads')
    lines.append('')

    lines.append('<b>End of Day:</b>')
    lines.append('☐ Log revenue events for today')
    lines.append('☐ Update launch metrics: /launch')
    lines.append('☐ Queue tomorrow\'s content topics')

    return '\n'.join(lines)


CONTENT_TOPICS = [
    "How to qualify for a $25k+ small business grant (step-by-step)",
    "5 credit score mistakes killing your funding chances",
    "The 30-day business funding roadmap for beginners",
    "Why your business credit score matters more than personal credit",
    "Grant vs loan: which is right for your business stage?",
    "How we helped a minority-owned business secure $50k in 60 days",
    "The hidden funding sources most entrepreneurs don't know about",
    "Improving your business readiness score: what lenders actually look at",
    "Understanding the SBA loan process from application to approval",
    "3 AI tools changing how small businesses get funded in 2026",
    "Women entrepreneur grants: the complete guide to federal programs",
    "How to build business credit from scratch (0 to 80 in 90 days)",
    "The truth about crowdfunding vs. traditional business financing",
    "Case study: rural business development grant success story",
    "Why most grant applications get rejected (and how to avoid it)",
]


def get_content_topics(count: int = 5) -> str:
    now = datetime.now(timezone.utc)
    start_idx = (now.timetuple().tm_yday * 3) % len(CONTENT_TOPICS)
    topics = [CONTENT_TOPICS[(start_idx + i) % len(CONTENT_TOPICS)] for i in range(count)]
    lines = [f'<b>Content Topics for Today ({now.strftime("%B %d")})</b>', '']
    for i, t in enumerate(topics, 1):
        lines.append(f"{i}. {t}")
    return '\n'.join(lines)


OUTREACH_SEGMENTS = [
    ("Women entrepreneurs", "businesses qualifying for gender-based grants"),
    ("Minority business owners", "MBDA and underserved community funding"),
    ("Rural small businesses", "USDA rural development grants"),
    ("Tech startups", "NSF SBIR/STTR and innovation grants"),
    ("Businesses with poor credit", "credit repair + alternative funding path"),
    ("5-year-old businesses", "growth-stage funding and MCA alternatives"),
    ("Franchise owners", "SBA 7(a) and franchise-specific loans"),
    ("Veteran entrepreneurs", "VA small business programs and SBA vetfran"),
]


def get_outreach_targets(count: int = 3) -> str:
    now = datetime.now(timezone.utc)
    start_idx = now.timetuple().tm_yday % len(OUTREACH_SEGMENTS)
    segments = [OUTREACH_SEGMENTS[(start_idx + i) % len(OUTREACH_SEGMENTS)] for i in range(count)]
    lines = [f'<b>Outreach Targets for Today</b>', '']
    for i, (seg, context) in enumerate(segments, 1):
        lines.append(f"{i}. <b>{seg}</b>")
        lines.append(f"   Focus: {context}")
    return '\n'.join(lines)
