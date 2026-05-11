"""
Nexus One Output Formatter.

Standard Telegram-friendly output formats for all Nexus One response types.

A. Executive Brief
B. Command Acknowledgment
C. Critical Alert
D. Daily Summary
E. Attention Required

All formats are concise and operator-friendly.
Telegram HTML is used for emphasis — no markdown.

Usage:
    from nexus_one.output_formatter import (
        format_executive_brief, format_command_ack,
        format_critical_alert, format_daily_summary,
        format_attention_required,
    )
"""

from datetime import datetime, timezone
from typing import Optional, List

from nexus_one.identity import URGENCY


# ─── A. Executive Brief ───────────────────────────────────────────────────────

def format_executive_brief(brief: dict) -> str:
    """Format daily_brief() output as Telegram HTML."""
    urgency_label = URGENCY.get(brief.get('urgency', 'low'), '🟢 LOW')
    revenue       = brief.get('revenue_month', 0)
    portfolio     = brief.get('portfolio') or {}
    blockers      = brief.get('blockers') or []
    worker_hlt    = brief.get('worker_health') or {}
    source_hlt    = brief.get('source_health') or {}
    pending       = brief.get('pending') or {}
    decisions     = pending.get('decisions') or {}
    variants      = pending.get('variants') or []
    commands      = pending.get('commands') or []

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    # State
    active  = portfolio.get('active_instances', 0)
    testing = portfolio.get('testing_instances', 0)
    scaled  = portfolio.get('scaled_instances', 0)

    state_line = (
        f"Revenue: <b>${revenue:,.2f}/mo</b>  |  "
        f"Instances: {active} active  {testing} testing  {scaled} scaled"
    )

    # Blockers
    blocker_text = ''
    if blockers:
        blocker_text = '\n<b>BLOCKERS:</b>\n' + '\n'.join(f"  ⛔ {b}" for b in blockers)
    else:
        blocker_text = '\n<b>BLOCKERS:</b>\n  None — system clear'

    # Pending
    total_pending = decisions.get('total', 0) + len(variants) + len(commands)
    pending_text = (
        f"\n<b>PENDING APPROVALS ({total_pending}):</b>\n"
        f"  • Decisions: {decisions.get('total',0)} "
        f"(kill={decisions.get('kill',0)} scale={decisions.get('scale',0)})\n"
        f"  • Improvement variants: {len(variants)}\n"
        f"  • Commands: {len(commands)}"
    )

    # Health
    health_text = (
        f"\n<b>HEALTH:</b>\n"
        f"  Workers: {worker_hlt.get('failure_count',0)} failures  "
        f"{worker_hlt.get('skipped_count',0)} skipped\n"
        f"  Sources: {source_hlt.get('count',0)} scored  "
        f"avg={source_hlt.get('avg_score',0)}  "
        f"critical={source_hlt.get('critical_count',0)}"
    )

    # Recommendation
    if blockers:
        recommendation = f"  → Address blocker: {blockers[0]}"
    elif decisions.get('kill', 0) > 0:
        recommendation = f"  → Review {decisions['kill']} kill decision(s) — instance revenue below threshold"
    elif len(variants) > 0:
        recommendation = f"  → Review {len(variants)} improvement variant(s) ready for approval"
    elif total_pending > 0:
        recommendation = f"  → {total_pending} items pending your decision"
    else:
        recommendation = "  → System operating normally. Monitor next briefing."

    return (
        f"<b>📋 NEXUS ONE — EXECUTIVE BRIEF</b>\n"
        f"{ts}  {urgency_label}\n"
        f"{'─' * 32}\n"
        f"\n<b>STATE:</b>\n  {state_line}"
        f"{blocker_text}"
        f"{pending_text}"
        f"{health_text}\n"
        f"\n<b>NEXT ACTION:</b>\n{recommendation}"
    )


# ─── B. Command Acknowledgment ────────────────────────────────────────────────

def format_command_ack(
    raw_command: str,
    understood: str,
    action: str,
    requires_approval: bool,
    risk_level: str        = 'low',
    expected_result: str   = 'Processing — check next briefing.',
    command_id: Optional[str] = None,
) -> str:
    approval_line = (
        '  ⚠️  <b>Approval required</b> before execution.'
        if requires_approval
        else '  ✅ Queued for immediate execution.'
    )
    risk_label = {'low': '🟢', 'medium': '🟡', 'high': '🟠', 'critical': '🔴'}.get(risk_level, '🟢')
    id_line    = f"\n  Command ID: <code>{command_id[:8]}...</code>" if command_id else ''

    return (
        f"<b>⚡ NEXUS ONE — COMMAND RECEIVED</b>\n"
        f"{'─' * 32}\n"
        f"\n<b>UNDERSTOOD:</b>\n  {understood}\n"
        f"\n<b>ROUTING:</b>\n  {action}\n"
        f"\n<b>APPROVAL:</b>\n{approval_line}"
        f"\n\n<b>RISK:</b>  {risk_label} {risk_level.upper()}"
        f"{id_line}\n"
        f"\n<b>EXPECT:</b>\n  {expected_result}"
    )


# ─── C. Critical Alert ────────────────────────────────────────────────────────

def format_critical_alert(
    issue: str,
    impact: str,
    recommended_action: str,
    urgency: str = 'high',
) -> str:
    urgency_label = URGENCY.get(urgency, '🟠 HIGH')
    return (
        f"<b>🚨 NEXUS ONE — {urgency_label} ALERT</b>\n"
        f"{'─' * 32}\n"
        f"\n<b>ISSUE:</b>\n  {issue}\n"
        f"\n<b>IMPACT:</b>\n  {impact}\n"
        f"\n<b>ACTION REQUIRED:</b>\n  {recommended_action}"
    )


# ─── D. Daily Summary ─────────────────────────────────────────────────────────

def format_daily_summary(brief: dict, changed: dict) -> str:
    """Compact daily summary combining brief + delta."""
    urgency_label = URGENCY.get(brief.get('urgency', 'low'), '🟢 LOW')
    revenue       = brief.get('revenue_month', 0)
    portfolio     = brief.get('portfolio') or {}
    blockers      = brief.get('blockers') or []
    pending       = brief.get('pending') or {}
    decisions     = pending.get('decisions') or {}
    variants      = pending.get('variants') or []
    commands      = pending.get('commands') or []

    completed_agents = changed.get('completed_agents', 0)
    failed_agents    = changed.get('failed_agents', 0)
    new_decisions    = len(changed.get('new_decisions') or [])
    since_hours      = changed.get('since_hours', 24)

    total_pending = decisions.get('total', 0) + len(variants) + len(commands)

    blocker_section = '\n'.join(f"  ⛔ {b}" for b in blockers) if blockers else '  None'

    next_actions = []
    if decisions.get('kill', 0) > 0:
        next_actions.append(f"Review {decisions['kill']} kill decision(s)")
    if len(variants) > 0:
        next_actions.append(f"Approve {len(variants)} improvement variant(s)")
    if len(commands) > 0:
        next_actions.append(f"Approve {len(commands)} pending command(s)")
    if not next_actions:
        next_actions.append("No action required — monitor next cycle")

    actions_text = '\n'.join(f"  {i+1}. {a}" for i, a in enumerate(next_actions[:3]))

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    return (
        f"<b>📊 NEXUS ONE — DAILY SUMMARY</b>\n"
        f"{ts}  {urgency_label}\n"
        f"{'─' * 32}\n"
        f"\n<b>SYSTEM HEALTH:</b>\n"
        f"  Agents last {since_hours}h:  {completed_agents} OK  {failed_agents} failed\n"
        f"  Revenue this month:  <b>${revenue:,.2f}</b>\n"
        f"  Active instances:  {portfolio.get('active_instances',0)}\n"
        f"\n<b>COMPLETED WORK:</b>\n"
        f"  {completed_agents} agent runs completed  |  {new_decisions} new decisions generated\n"
        f"\n<b>PENDING APPROVALS ({total_pending}):</b>\n"
        f"  Decisions: {decisions.get('total',0)}  |  Variants: {len(variants)}  |  Commands: {len(commands)}\n"
        f"\n<b>BLOCKERS:</b>\n{blocker_section}\n"
        f"\n<b>NEXT ACTIONS:</b>\n{actions_text}"
    )


# ─── E. Attention Required ────────────────────────────────────────────────────

def format_attention_required(attention: dict) -> str:
    items = attention.get('items') or []
    if not items:
        return (
            "<b>✅ NEXUS ONE — ALL CLEAR</b>\n"
            "No items require your attention right now.\n"
            "System is running. Next briefing on schedule."
        )

    lines = []
    for item in items[:8]:
        urgency = item.get('urgency', 'medium')
        icon    = {'high': '🟠', 'critical': '🔴', 'medium': '🟡', 'low': '🟢'}.get(urgency, '🟡')
        itype   = item.get('type', '').replace('_', ' ').title()
        text    = item.get('text', '')[:70]
        iid     = item.get('id', '')
        id_str  = f" <code>[{iid[:6]}]</code>" if iid else ''
        lines.append(f"  {icon} <b>{itype}</b>{id_str}\n    {text}")

    return (
        f"<b>⚡ NEXUS ONE — ATTENTION REQUIRED ({len(items)} items)</b>\n"
        f"{'─' * 32}\n\n" +
        '\n\n'.join(lines)
    )
