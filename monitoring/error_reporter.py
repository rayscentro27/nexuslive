"""
Error Reporter.

Writes structured errors to the error_log table.
Drop-in for any except block.

Usage:
    from monitoring.error_reporter import log_error

    try:
        ...
    except Exception as e:
        import traceback
        log_error('signal_poller', str(e), trace=traceback.format_exc())
"""

import os
import json
import logging
import traceback as tb
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger('ErrorReporter')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
    }


def log_error(
    source: str,
    message: str,
    trace: Optional[str]  = None,
    level: str            = 'error',
    meta: Optional[dict]  = None,
) -> bool:
    """
    Insert one row into error_log. Fire-and-forget — never raises.
    level: 'warning' | 'error' | 'critical'
    """
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/error_log"
    row  = {
        'source':  source,
        'level':   level,
        'message': message[:1000],
        'trace':   (trace or '')[:3000] or None,
        'meta':    meta or {},
    }
    data = json.dumps(row).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=6) as _:
            return True
    except Exception:
        # Never let the error reporter crash the caller
        return False


def log_exception(source: str, exc: Exception, meta: Optional[dict] = None) -> bool:
    """Convenience wrapper — captures current traceback automatically."""
    return log_error(
        source=source,
        message=str(exc),
        trace=tb.format_exc(),
        level='error',
        meta=meta,
    )


def log_warning(source: str, message: str, meta: Optional[dict] = None) -> bool:
    return log_error(source, message, level='warning', meta=meta)


def log_critical(source: str, message: str, meta: Optional[dict] = None) -> bool:
    return log_error(source, message, level='critical', meta=meta)
