"""
Integration Checks.

Each check returns a standardised result dict:
  {
    'integration_key': str,   -- e.g. 'supabase'
    'check_key':       str,   -- e.g. 'connectivity'
    'status':          str,   -- ok | degraded | missing | blocked
    'severity':        str,   -- critical | high | medium | low
    'message':         str,   -- human-readable, NO raw secrets
    'last_checked_at': str,   -- ISO timestamp
  }

SECRET SAFETY:
  - Never include raw token/key values in message or any field
  - Only report: present/missing/length/prefix-hint (no full values)
  - All checks log at DEBUG only — no secrets to stdout/stderr

Usage:
    from readiness.integration_checks import run_all_checks, CHECKS
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger('IntegrationChecks')

# ─── Result factory ───────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _result(
    integration_key: str,
    check_key: str,
    status: str,
    severity: str,
    message: str,
) -> dict:
    return {
        'integration_key': integration_key,
        'check_key':       check_key,
        'status':          status,
        'severity':        severity,
        'message':         message,
        'last_checked_at': _ts(),
    }


def _env_hint(key: str) -> str:
    """Return a safe hint about an env var (no value, just presence/length)."""
    val = os.getenv(key, '')
    if not val:
        return 'not set'
    return f"set ({len(val)} chars)"


# ─── Individual checks ────────────────────────────────────────────────────────

def check_supabase_connectivity() -> dict:
    """Can we reach Supabase REST API?"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')

    if not url_val:
        return _result('supabase', 'connectivity', 'blocked', 'critical',
                       'SUPABASE_URL not set — cannot connect')
    if not key_val:
        return _result('supabase', 'connectivity', 'blocked', 'critical',
                       'SUPABASE_KEY not set — cannot authenticate')

    try:
        url = f"{url_val}/rest/v1/sources?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
        return _result('supabase', 'connectivity', 'ok', 'critical',
                       'Supabase REST API reachable and authenticated')
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Table missing but API is reachable — connectivity ok
            return _result('supabase', 'connectivity', 'ok', 'critical',
                           f'Supabase reachable (table not found: expected during setup)')
        return _result('supabase', 'connectivity', 'degraded', 'critical',
                       f'Supabase HTTP error: {e.code}')
    except Exception as e:
        return _result('supabase', 'connectivity', 'blocked', 'critical',
                       f'Supabase unreachable: {type(e).__name__}')


def check_supabase_required_tables() -> List[dict]:
    """Check each required table is accessible."""
    from nexus_one.readiness_checker import REQUIRED_TABLES

    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return [_result('supabase', 'tables', 'blocked', 'critical',
                        'Cannot check tables — SUPABASE_URL or SUPABASE_KEY missing')]

    results = []
    missing = []
    for table in REQUIRED_TABLES:
        url = f"{url_val}/rest/v1/{table}?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as r:
                r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                missing.append(table)
        except Exception:
            missing.append(table)

    present = len(REQUIRED_TABLES) - len(missing)
    if not missing:
        results.append(_result('supabase', 'tables', 'ok', 'critical',
                               f'All {present} required tables accessible'))
    else:
        results.append(_result('supabase', 'tables', 'blocked', 'critical',
                               f'{len(missing)}/{len(REQUIRED_TABLES)} tables missing: '
                               f'{", ".join(missing[:5])}{"..." if len(missing) > 5 else ""}'))
    return results


def check_telegram() -> dict:
    """Is the Telegram bot token valid and can it send?"""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat  = os.getenv('TELEGRAM_CHAT_ID', '')

    if not token:
        return _result('telegram', 'bot_token', 'missing', 'critical',
                       f'TELEGRAM_BOT_TOKEN not set ({_env_hint("TELEGRAM_BOT_TOKEN")})')
    if not chat:
        return _result('telegram', 'chat_id', 'missing', 'high',
                       f'TELEGRAM_CHAT_ID not set — alerts have no destination')

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        if data.get('ok'):
            bot = data.get('result', {})
            return _result('telegram', 'bot_token', 'ok', 'critical',
                           f'Bot verified: @{bot.get("username", "unknown")} — '
                           f'chat_id {_env_hint("TELEGRAM_CHAT_ID")}')
        return _result('telegram', 'bot_token', 'degraded', 'critical',
                       'getMe returned ok=false — token may be revoked')
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _result('telegram', 'bot_token', 'blocked', 'critical',
                           'TELEGRAM_BOT_TOKEN invalid — 401 Unauthorized')
        return _result('telegram', 'bot_token', 'degraded', 'critical',
                       f'Telegram API error: {e.code}')
    except Exception as e:
        return _result('telegram', 'bot_token', 'degraded', 'high',
                       f'Telegram unreachable: {type(e).__name__}')


def check_hermes() -> dict:
    """Is the Hermes gateway running and authenticated?"""
    token = os.getenv('HERMES_GATEWAY_TOKEN', '')
    if not token:
        return _result('hermes', 'gateway', 'missing', 'high',
                       f'HERMES_GATEWAY_TOKEN not set — AI features degraded')

    try:
        url = 'http://localhost:8642/v1/models'
        req = urllib.request.Request(
            url, headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
        return _result('hermes', 'gateway', 'ok', 'high',
                       'Hermes gateway reachable at localhost:8642')
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return _result('hermes', 'gateway', 'blocked', 'high',
                           'Hermes: HERMES_GATEWAY_TOKEN rejected — 401')
        return _result('hermes', 'gateway', 'degraded', 'high',
                       f'Hermes HTTP error: {e.code}')
    except Exception:
        return _result('hermes', 'gateway', 'degraded', 'high',
                       'Hermes gateway not responding at localhost:8642 — '
                       'start hermes process or check launchd service')


def check_worker_health() -> dict:
    """Have workers run recently?"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return _result('workers', 'recent_runs', 'blocked', 'high',
                       'Cannot check — Supabase not configured')

    try:
        # Check worker_heartbeats — confirms mac-mini-worker is alive and reporting
        from datetime import timezone
        url = (f"{url_val}/rest/v1/worker_heartbeats"
               f"?select=worker_id,status,last_heartbeat_at,in_flight_jobs"
               f"&worker_id=eq.mac-mini-worker-1"
               f"&order=last_seen_at.desc&limit=1")
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())

        if not rows:
            return _result('workers', 'recent_runs', 'degraded', 'high',
                           'No heartbeat rows — mac-mini-worker may not have started yet')

        hb = rows[0]
        last_seen = hb.get('last_heartbeat_at', '')
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            age_s = (datetime.now(timezone.utc) - ts).total_seconds()
            if age_s > 120:
                return _result('workers', 'recent_runs', 'degraded', 'high',
                               f'Heartbeat stale — last seen {int(age_s//60)}m ago')
        except Exception:
            pass

        jobs = hb.get('in_flight_jobs', 0)
        return _result('workers', 'recent_runs', 'ok', 'high',
                       f'Worker online — heartbeat {last_seen[:19]}Z, in_flight={jobs}')
    except Exception as e:
        return _result('workers', 'recent_runs', 'degraded', 'high',
                       f'Worker health check failed: {type(e).__name__}')


def check_command_ingestion() -> dict:
    """Is the admin_commands table reachable for command routing?"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return _result('command_ingestion', 'table_access', 'blocked', 'high',
                       'Cannot check — Supabase not configured')
    try:
        url = f"{url_val}/rest/v1/admin_commands?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
        return _result('command_ingestion', 'table_access', 'ok', 'high',
                       'admin_commands table accessible — command routing ready')
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return _result('command_ingestion', 'table_access', 'missing', 'high',
                           'admin_commands table not found — create via Windows SQL contract')
        return _result('command_ingestion', 'table_access', 'degraded', 'high',
                       f'admin_commands check failed: HTTP {e.code}')
    except Exception as e:
        return _result('command_ingestion', 'table_access', 'degraded', 'high',
                       f'Command ingestion check failed: {type(e).__name__}')


def check_source_registry() -> dict:
    """Is the source registry table accessible?"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return _result('source_registry', 'table_access', 'blocked', 'medium',
                       'Cannot check — Supabase not configured')
    try:
        url = f"{url_val}/rest/v1/sources?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        return _result('source_registry', 'table_access', 'ok', 'medium',
                       f'sources table accessible ({len(rows)} rows sampled)')
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return _result('source_registry', 'table_access', 'missing', 'medium',
                           'sources table not found — research pipeline blocked')
        return _result('source_registry', 'table_access', 'degraded', 'medium',
                       f'Source registry check failed: HTTP {e.code}')
    except Exception as e:
        return _result('source_registry', 'table_access', 'degraded', 'medium',
                       f'Source registry check failed: {type(e).__name__}')


def check_self_healing_engine() -> dict:
    """Is the improvement engine table accessible?"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return _result('self_healing', 'table_access', 'blocked', 'medium',
                       'Cannot check — Supabase not configured')
    try:
        url = f"{url_val}/rest/v1/improvement_experiments?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
        return _result('self_healing', 'table_access', 'ok', 'medium',
                       'improvement_experiments table accessible — self-healing engine ready')
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return _result('self_healing', 'table_access', 'missing', 'medium',
                           'improvement_experiments table not found — '
                           'apply Windows SQL contract (improvement engine schema)')
        return _result('self_healing', 'table_access', 'degraded', 'medium',
                       f'Self-healing check failed: HTTP {e.code}')
    except Exception as e:
        return _result('self_healing', 'table_access', 'degraded', 'medium',
                       f'Self-healing check failed: {type(e).__name__}')


def check_nexus_one_runtime() -> dict:
    """Are all Nexus One runtime prerequisites satisfied?"""
    missing_env = [k for k in ('SUPABASE_URL', 'SUPABASE_KEY', 'TELEGRAM_BOT_TOKEN',
                                'TELEGRAM_CHAT_ID', 'HERMES_GATEWAY_TOKEN')
                   if not os.getenv(k, '')]
    if missing_env:
        return _result('nexus_one', 'runtime', 'blocked', 'critical',
                       f'Missing required env vars: {", ".join(missing_env)}')

    # Check executive_briefings table
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    try:
        url = f"{url_val}/rest/v1/executive_briefings?select=id&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
        return _result('nexus_one', 'runtime', 'ok', 'critical',
                       'Nexus One runtime ready — env configured, briefings table accessible')
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return _result('nexus_one', 'runtime', 'degraded', 'critical',
                           'executive_briefings table missing — '
                           'Nexus One cannot persist briefings. Apply Windows SQL contract.')
        return _result('nexus_one', 'runtime', 'degraded', 'critical',
                       f'Nexus One table check failed: HTTP {e.code}')
    except Exception as e:
        return _result('nexus_one', 'runtime', 'degraded', 'critical',
                       f'Nexus One runtime check failed: {type(e).__name__}')


# ─── Optional checks ──────────────────────────────────────────────────────────

def check_oanda() -> dict:
    """OANDA broker credentials (trading engine)."""
    api_key    = os.getenv('OANDA_API_KEY', '')
    account_id = os.getenv('OANDA_ACCOUNT_ID', '')
    dry_run    = os.getenv('DRY_RUN', 'True').lower() in ('true', '1', 'yes')

    if not api_key or not account_id:
        severity = 'medium' if dry_run else 'high'
        return _result('oanda', 'credentials', 'missing', severity,
                       f'OANDA_API_KEY: {_env_hint("OANDA_API_KEY")}, '
                       f'OANDA_ACCOUNT_ID: {_env_hint("OANDA_ACCOUNT_ID")} — '
                       f'{"DRY_RUN=True (safe)" if dry_run else "WARNING: live mode with missing creds"}')

    return _result('oanda', 'credentials', 'ok', 'medium',
                   f'OANDA credentials present — '
                   f'DRY_RUN={"True (standby)" if dry_run else "False (LIVE MODE)"}')


def check_tradingview_router() -> dict:
    """Is the signal router running on port 8000?"""
    try:
        req = urllib.request.Request('http://localhost:8000/health')
        with urllib.request.urlopen(req, timeout=5) as r:
            r.read()
        return _result('tradingview', 'signal_router', 'ok', 'medium',
                       'Signal router running at localhost:8000 — webhook ingestion ready')
    except Exception:
        return _result('tradingview', 'signal_router', 'degraded', 'medium',
                       'Signal router not responding at localhost:8000 — '
                       'check launchd service com.nexus.signal-router')


def check_manus_readiness() -> dict:
    """Can Manus read executive briefings? (read-only check)"""
    url_val = os.getenv('SUPABASE_URL', '')
    key_val = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return _result('manus', 'briefing_access', 'blocked', 'low',
                       'Cannot check — Supabase not configured')
    try:
        url = f"{url_val}/rest/v1/executive_briefings?select=id&order=created_at.desc&limit=1"
        req = urllib.request.Request(
            url, headers={'apikey': key_val, 'Authorization': f'Bearer {key_val}'}
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            rows = json.loads(r.read())
        if rows:
            return _result('manus', 'briefing_access', 'ok', 'low',
                           'executive_briefings readable — Manus can surface briefings')
        return _result('manus', 'briefing_access', 'degraded', 'low',
                       'executive_briefings table empty — no briefings generated yet')
    except Exception:
        return _result('manus', 'briefing_access', 'missing', 'low',
                       'executive_briefings not accessible — '
                       'create table via Windows SQL contract first')


# ─── Run all checks ───────────────────────────────────────────────────────────

# Check manifest — (fn, is_required)
CHECKS = [
    (check_supabase_connectivity, True),
    (check_telegram,              True),
    (check_hermes,              True),
    (check_worker_health,         True),
    (check_command_ingestion,     True),
    (check_source_registry,       True),
    (check_self_healing_engine,   True),
    (check_nexus_one_runtime,     True),
    (check_oanda,                 False),
    (check_tradingview_router,    False),
    (check_manus_readiness,       False),
]


def run_all_checks(include_optional: bool = True) -> List[dict]:
    """
    Run all integration checks.
    Returns flat list of result dicts — safe to store in Supabase.
    """
    results = []
    for fn, required in CHECKS:
        if not required and not include_optional:
            continue
        try:
            result = fn()
            # fn may return a single dict or a list
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
        except Exception as e:
            logger.warning(f"Check {fn.__name__} raised: {e}")
            results.append(_result(
                fn.__name__, 'exception', 'degraded', 'high',
                f'Check threw exception: {type(e).__name__}',
            ))
    return results


def run_required_checks() -> List[dict]:
    return run_all_checks(include_optional=False)
