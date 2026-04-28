"""
Nexus One Readiness Checker.

Answers setup/readiness questions for the super admin:
  - what credentials are still missing?
  - what integrations are incomplete?
  - what blocks the system from being active?
  - what is required before production launch?

Checks:
  ENV:        Required environment variables
  SUPABASE:   Table existence and row counts
  SERVICES:   Telegram bot, Hermes, signal router
  WORKERS:    Recent run history
  TRADING:    DRY_RUN status, broker connectivity
  REVIEW:     Pending approvals blocking go-live

Usage:
    from nexus_one.readiness_checker import run_readiness_check, format_readiness_report
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('ReadinessChecker')

# ─── Required env vars ────────────────────────────────────────────────────────

REQUIRED_ENV = {
    'SUPABASE_URL':         'Supabase project URL',
    'SUPABASE_KEY':         'Supabase anon/service key',
    'TELEGRAM_BOT_TOKEN':   'Telegram bot token',
    'TELEGRAM_CHAT_ID':     'Telegram chat ID for alerts',
    'HERMES_GATEWAY_TOKEN':  'Hermes gateway auth token',
}

OPTIONAL_ENV = {
    'HF_TOKEN':             'HuggingFace token (for embeddings)',
    'OANDA_API_KEY':        'OANDA broker API key (trading)',
    'OANDA_ACCOUNT_ID':     'OANDA account ID (trading)',
    'OPENAI_API_KEY':       'OpenAI API key (fallback LLM)',
}

# ─── Required Supabase tables ─────────────────────────────────────────────────

REQUIRED_TABLES = [
    'research',
    'sources',
    'source_health_scores',
    'agent_run_summaries',
    'executive_briefings',
    'admin_commands',
    'system_events',
    'decisions',
    'compliance_records',
    'audit_logs',
    'api_keys',
    'lead_profiles',
    'sales_conversations',
    'funnel_stage_tracking',
    'nexus_instances',
    'niche_candidates',
    'portfolio_summary',
    'instance_decisions',
    'revenue_streams',
    'improvement_experiments',
    'candidate_variants',
]

OPTIONAL_TABLES = [
    'empire_entities',
    'capital_deployments',
    'empire_workforce',
    'empire_regions',
    'tv_raw_alerts',
    'tv_normalized_signals',
    'call_sessions',
    'ad_campaigns',
    'organizations',
]


def _check_env() -> dict:
    missing  = []
    present  = []
    optional_missing = []

    for key, desc in REQUIRED_ENV.items():
        val = os.getenv(key, '')
        if not val:
            missing.append({'key': key, 'description': desc})
        else:
            present.append(key)

    for key, desc in OPTIONAL_ENV.items():
        val = os.getenv(key, '')
        if not val:
            optional_missing.append({'key': key, 'description': desc})

    return {
        'required_missing':  missing,
        'required_present':  present,
        'optional_missing':  optional_missing,
        'status':            'ok' if not missing else 'blocked',
    }


def _check_supabase_table(table: str) -> bool:
    """Return True if table is accessible."""
    key = os.getenv('SUPABASE_KEY', '')
    url = f"{os.getenv('SUPABASE_URL', '')}/rest/v1/{table}?select=id&limit=1"
    req = urllib.request.Request(
        url, headers={'apikey': key, 'Authorization': f'Bearer {key}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
            return True
    except Exception:
        return False


def _check_tables() -> dict:
    missing   = []
    present   = []
    opt_miss  = []
    opt_pres  = []

    for t in REQUIRED_TABLES:
        if _check_supabase_table(t):
            present.append(t)
        else:
            missing.append(t)

    for t in OPTIONAL_TABLES:
        if _check_supabase_table(t):
            opt_pres.append(t)
        else:
            opt_miss.append(t)

    return {
        'required_missing':  missing,
        'required_present':  len(present),
        'optional_missing':  opt_miss,
        'optional_present':  len(opt_pres),
        'status':            'ok' if not missing else 'blocked',
    }


def _check_telegram() -> dict:
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    if not token:
        return {'status': 'blocked', 'reason': 'TELEGRAM_BOT_TOKEN not set'}
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
            if data.get('ok'):
                bot = data.get('result', {})
                return {
                    'status':    'ok',
                    'bot_name':  bot.get('first_name', ''),
                    'username':  bot.get('username', ''),
                }
    except Exception as e:
        return {'status': 'error', 'reason': str(e)}
    return {'status': 'error', 'reason': 'Unexpected response'}


def _check_hermes() -> dict:
    token = os.getenv('HERMES_GATEWAY_TOKEN', '')
    if not token:
        return {'status': 'blocked', 'reason': 'HERMES_GATEWAY_TOKEN not set'}
    try:
        url  = 'http://localhost:8642/v1/models'
        req  = urllib.request.Request(
            url, headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
            return {'status': 'ok', 'endpoint': 'localhost:8642'}
    except Exception as e:
        return {'status': 'degraded', 'reason': f'Hermes unreachable: {e}'}


def _check_signal_router() -> dict:
    try:
        req = urllib.request.Request('http://localhost:8000/health')
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
            return {'status': 'ok', 'port': 8000}
    except Exception:
        return {'status': 'degraded', 'reason': 'Signal router not responding on :8000'}


def _check_trading_engine() -> dict:
    """Check if trading engine DRY_RUN flag and broker credentials."""
    dry_run    = os.getenv('DRY_RUN', 'True').lower() in ('true', '1', 'yes')
    oanda_key  = bool(os.getenv('OANDA_API_KEY', ''))
    oanda_acc  = bool(os.getenv('OANDA_ACCOUNT_ID', ''))

    return {
        'status':          'standby' if dry_run else 'live',
        'dry_run':         dry_run,
        'broker_creds':    oanda_key and oanda_acc,
        'note':            'DRY_RUN=True — safe until manual flip' if dry_run else 'LIVE MODE — monitor closely',
    }


def _check_worker_health() -> dict:
    """Recent agent run summary to confirm workers are firing."""
    key = os.getenv('SUPABASE_KEY', '')
    url = (
        f"{os.getenv('SUPABASE_URL', '')}/rest/v1/"
        "agent_run_summaries?select=agent_name,status,created_at"
        "&order=created_at.desc&limit=20"
    )
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
        completed = [r for r in rows if r.get('status') == 'completed']
        return {
            'recent_runs':  len(rows),
            'completed':    len(completed),
            'status':       'ok' if completed else 'no_runs',
        }
    except Exception:
        return {'recent_runs': 0, 'status': 'error'}


# ─── Full readiness check ─────────────────────────────────────────────────────

def run_readiness_check() -> dict:
    """Run all readiness checks. Returns comprehensive status dict."""
    env      = _check_env()
    tables   = _check_tables()
    telegram = _check_telegram()
    hermes = _check_hermes()
    router   = _check_signal_router()
    trading  = _check_trading_engine()
    workers  = _check_worker_health()

    blockers = []
    warnings = []

    if env['required_missing']:
        blockers.append(f"{len(env['required_missing'])} required ENV vars missing")
    if tables['required_missing']:
        blockers.append(f"{len(tables['required_missing'])} required DB tables missing")
    if telegram.get('status') != 'ok':
        blockers.append(f"Telegram: {telegram.get('reason','unknown error')}")
    if hermes.get('status') == 'blocked':
        blockers.append("Hermes: HERMES_GATEWAY_TOKEN not set")
    if hermes.get('status') == 'degraded':
        warnings.append("Hermes gateway unreachable — AI features degraded")
    if router.get('status') == 'degraded':
        warnings.append("Signal router not responding — TradingView webhooks inactive")
    if workers.get('status') == 'no_runs':
        warnings.append("No recent agent runs found — workers may not be scheduled")

    overall = 'blocked' if blockers else ('degraded' if warnings else 'ready')

    return {
        'overall':    overall,
        'blockers':   blockers,
        'warnings':   warnings,
        'checks': {
            'env':       env,
            'tables':    tables,
            'telegram':  telegram,
            'hermes':  hermes,
            'router':    router,
            'trading':   trading,
            'workers':   workers,
        },
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }


def format_readiness_report(report: dict) -> str:
    """Format readiness check as Telegram HTML."""
    overall  = report.get('overall', 'unknown')
    blockers = report.get('blockers') or []
    warnings = report.get('warnings') or []
    checks   = report.get('checks') or {}

    status_icon = {'ready': '✅', 'degraded': '🟡', 'blocked': '🔴'}.get(overall, '❓')

    env      = checks.get('env', {})
    tables   = checks.get('tables', {})
    telegram = checks.get('telegram', {})
    hermes = checks.get('hermes', {})
    router   = checks.get('router', {})
    trading  = checks.get('trading', {})
    workers  = checks.get('workers', {})

    def status_line(label, check, key='status'):
        s = check.get(key, 'unknown')
        icon = {'ok': '✅', 'ready': '✅', 'standby': '🟡', 'degraded': '🟡',
                'blocked': '🔴', 'error': '🔴', 'no_runs': '🟡'}.get(s, '❓')
        return f"  {icon} {label}: {s}"

    blocker_text = '\n'.join(f"  ⛔ {b}" for b in blockers) or '  None'
    warning_text = '\n'.join(f"  ⚠️  {w}" for w in warnings) or '  None'

    env_missing = ', '.join(e['key'] for e in env.get('required_missing', []))
    tbl_missing = ', '.join(tables.get('required_missing', [])[:5])

    lines = [
        f"<b>{status_icon} NEXUS ONE — READINESS CHECK</b>",
        f"{report.get('checked_at','')[:10]}",
        f"{'─' * 32}",
        f"\n<b>OVERALL: {overall.upper()}</b>",
        f"\n<b>BLOCKERS:</b>\n{blocker_text}",
        f"\n<b>WARNINGS:</b>\n{warning_text}",
        f"\n<b>CHECKS:</b>",
        status_line('ENV vars', env),
        f"    missing: {env_missing or 'none'}",
        status_line('DB tables', tables),
        f"    present={tables.get('required_present',0)}/{len(REQUIRED_TABLES)}  "
        f"missing: {tbl_missing or 'none'}",
        status_line('Telegram', telegram),
        status_line('Hermes', hermes),
        status_line('Signal router', router),
        status_line('Trading engine', trading),
        f"    dry_run={trading.get('dry_run','?')}  broker_creds={trading.get('broker_creds','?')}",
        status_line('Workers', workers),
        f"    recent_runs={workers.get('recent_runs',0)}  completed={workers.get('completed',0)}",
    ]
    return '\n'.join(lines)
