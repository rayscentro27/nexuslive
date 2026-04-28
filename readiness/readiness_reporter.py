"""
Readiness Reporter.

Aggregates integration check results into structured reports
for Nexus One, the Windows Credential System, and Telegram.

Answers:
  - what is configured?
  - what is missing?
  - what is degraded?
  - what is blocking pilot?

Usage:
    from readiness.readiness_reporter import (
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14
        build_report, get_blockers, get_nexus_one_summary,
        store_results, format_telegram_report,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger('ReadinessReporter')

# Status priority for sorting (lower = more urgent)
STATUS_PRIORITY = {'blocked': 0, 'missing': 1, 'degraded': 2, 'ok': 3}
SEVERITY_PRIORITY = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}


def _sort_key(result: dict) -> tuple:
    return (
        STATUS_PRIORITY.get(result.get('status', 'ok'), 9),
        SEVERITY_PRIORITY.get(result.get('severity', 'low'), 9),
    )


def build_report(results: List[dict]) -> dict:
    """
    Aggregate raw check results into a structured report.
    Safe to serialise — no secrets.
    """
    blocked   = [r for r in results if r.get('status') in ('blocked', 'missing')]
    degraded  = [r for r in results if r.get('status') == 'degraded']
    ok_checks = [r for r in results if r.get('status') == 'ok']

    critical_blockers = [r for r in blocked if r.get('severity') == 'critical']
    pilot_ready = (
        len(critical_blockers) == 0 and
        len([r for r in degraded if r.get('severity') == 'critical']) == 0
    )

    overall = (
        'blocked'  if critical_blockers else
        'degraded' if degraded else
        'ready'
    )

    return {
        'overall':           overall,
        'pilot_ready':       pilot_ready,
        'total_checks':      len(results),
        'ok_count':          len(ok_checks),
        'degraded_count':    len(degraded),
        'blocked_count':     len(blocked),
        'critical_blockers': critical_blockers,
        'by_status': {
            'blocked':  sorted(blocked,  key=_sort_key),
            'degraded': sorted(degraded, key=_sort_key),
            'ok':       ok_checks,
        },
        'results':       sorted(results, key=_sort_key),
        'generated_at':  datetime.now(timezone.utc).isoformat(),
    }


def get_blockers(report: dict) -> List[str]:
    """Return plain-English blocker messages for Nexus One."""
    messages = []
    for r in report.get('critical_blockers', []):
        messages.append(
            f"[{r['integration_key'].upper()}] {r['message']}"
        )
    for r in report.get('by_status', {}).get('blocked', []):
        if r.get('severity') != 'critical':
            messages.append(
                f"[{r['integration_key'].upper()}] {r['message']}"
            )
    return messages


def get_nexus_one_summary(report: dict) -> dict:
    """
    Structured summary for Nexus One reporting layer.
    Answers: configured / missing / degraded / blocking_pilot
    """
    results = report.get('results', [])

    configured = [
        r['integration_key']
        for r in results if r.get('status') == 'ok'
    ]
    missing = [
        {'key': r['integration_key'], 'check': r['check_key'], 'msg': r['message']}
        for r in results if r.get('status') in ('missing', 'blocked')
    ]
    degraded = [
        {'key': r['integration_key'], 'check': r['check_key'], 'msg': r['message']}
        for r in results if r.get('status') == 'degraded'
    ]
    blocking_pilot = [
        r['message'] for r in results
        if r.get('status') in ('blocked', 'missing') and r.get('severity') == 'critical'
    ]

    return {
        'pilot_ready':     report.get('pilot_ready', False),
        'overall':         report.get('overall', 'unknown'),
        'configured':      list(set(configured)),
        'missing':         missing,
        'degraded':        degraded,
        'blocking_pilot':  blocking_pilot,
        'generated_at':    report.get('generated_at'),
    }


def store_results(results: List[dict]) -> bool:
    """
    Persist check results to integration_readiness table.
    Upsert on (integration_key, check_key) — one live row per check.
    """
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        logger.warning("Cannot store readiness results — Supabase not configured")
        return False

    url = f"{url_val}/rest/v1/integration_readiness"
    h   = {
        'apikey':        key_val,
        'Authorization': f'Bearer {key_val}',
        'Content-Type':  'application/json',
        'Prefer':        'resolution=merge-duplicates,return=minimal',
    }

    ok = True
    for row in results:
        # Never store raw secrets — results already sanitised by checks
        try:
            data = json.dumps(row).encode()
            req  = urllib.request.Request(url, data=data, headers=h, method='POST')
            urllib.request.urlopen(req, timeout=8)
        except Exception as e:
            logger.warning(f"Store failed for {row.get('integration_key')}: {e}")
            ok = False
    return ok


def format_telegram_report(report: dict) -> str:
    """Telegram HTML readiness report — no secrets, concise."""
    overall      = report.get('overall', 'unknown')
    pilot_ready  = report.get('pilot_ready', False)
    total        = report.get('total_checks', 0)
    ok_count     = report.get('ok_count', 0)
    degraded_ct  = report.get('degraded_count', 0)
    blocked_ct   = report.get('blocked_count', 0)
    generated    = report.get('generated_at', '')[:16]

    icon = {'ready': '✅', 'degraded': '🟡', 'blocked': '🔴'}.get(overall, '❓')
    pilot_line = '✅ Pilot ready' if pilot_ready else '⛔ Pilot BLOCKED — see issues below'

    # Blocked items
    blocked = report.get('by_status', {}).get('blocked', [])
    blocked_lines = '\n'.join(
        f"  🔴 [{r['integration_key']}] {r['message']}"
        for r in blocked[:5]
    ) or '  None'

    # Degraded items
    degraded = report.get('by_status', {}).get('degraded', [])
    degraded_lines = '\n'.join(
        f"  🟡 [{r['integration_key']}] {r['message']}"
        for r in degraded[:4]
    ) or '  None'

    # OK items — just keys
    ok_keys = list(set(r['integration_key'] for r in report.get('by_status', {}).get('ok', [])))
    ok_line = ', '.join(ok_keys) or 'none'

    return (
        f"<b>{icon} NEXUS ONE — INTEGRATION READINESS</b>\n"
        f"{generated} UTC\n"
        f"{'─' * 32}\n"
        f"\n<b>OVERALL: {overall.upper()}</b>  |  {pilot_line}\n"
        f"\nChecks: {total} total  |  {ok_count} OK  {degraded_ct} degraded  {blocked_ct} blocked\n"
        f"\n<b>BLOCKED / MISSING:</b>\n{blocked_lines}\n"
        f"\n<b>DEGRADED:</b>\n{degraded_lines}\n"
        f"\n<b>CONFIGURED OK:</b>\n  {ok_line}"
    )
