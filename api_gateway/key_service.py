"""
API Key Service.

Manages api_keys and api_usage_logs.

Key format:  nxs_<random_32_chars>
Stored as:   sha256(full_key) in key_hash column
Display as:  first 12 chars (nxs_XXXXXXXX...)

Available scopes:
  funding_analysis, credit_analysis, strategy_insights,
  research_data, lead_management, admin

Usage:
    from api_gateway.key_service import create_key, validate_key, log_usage

    key_str, key_id = create_key(org_id=org_id, scopes=['funding_analysis'], label='My App')
    key_data = validate_key(key_str)  # returns row or None
    log_usage(key_id, '/api/funding/analyze', status_code=200, response_ms=140)
"""

import os
import json
import hashlib
import secrets
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Tuple, List

logger = logging.getLogger('KeyService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_SCOPES = {
    'funding_analysis', 'credit_analysis', 'strategy_insights',
    'research_data', 'lead_management', 'admin',
}
KEY_PREFIX = 'nxs_'


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


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"PATCH {path} → {e}")
        return False


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ─── Key Management ───────────────────────────────────────────────────────────

def create_key(
    org_id: Optional[str]     = None,
    scopes: Optional[List[str]] = None,
    label: str                = '',
    expires_at: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Create a new API key.
    Returns (raw_key_string, key_id).
    raw_key_string is shown ONCE — store it securely.
    """
    scopes = scopes or ['funding_analysis']
    valid_scopes = [s for s in scopes if s in VALID_SCOPES]

    raw_key  = KEY_PREFIX + secrets.token_urlsafe(32)
    key_hash = _hash_key(raw_key)
    prefix   = raw_key[:12]

    row: dict = {
        'key_hash':   key_hash,
        'key_prefix': prefix,
        'label':      label or 'API Key',
        'scopes':     valid_scopes,
        'status':     'active',
    }
    if org_id:
        row['org_id'] = org_id
    if expires_at:
        row['expires_at'] = expires_at

    result = _sb_post('api_keys', row)
    key_id = result.get('id') if result else None

    logger.info(f"API key created: prefix={prefix} org={org_id} scopes={valid_scopes}")
    return raw_key, key_id


def validate_key(raw_key: str) -> Optional[dict]:
    """
    Validate an API key. Returns the key row (with scopes) or None.
    Updates last_used_at on success.
    """
    if not raw_key.startswith(KEY_PREFIX):
        return None

    key_hash = _hash_key(raw_key)
    rows     = _sb_get(
        f"api_keys?key_hash=eq.{key_hash}&status=eq.active&select=*&limit=1"
    )
    if not rows:
        return None

    row = rows[0]

    # Check expiry
    expires = row.get('expires_at')
    if expires:
        try:
            exp = datetime.fromisoformat(expires.replace('Z', '+00:00'))
            if exp < datetime.now(timezone.utc):
                return None
        except Exception:
            pass

    # Update last_used_at async (fire and forget)
    try:
        _sb_patch(
            f"api_keys?id=eq.{row['id']}",
            {'last_used_at': datetime.now(timezone.utc).isoformat()},
        )
    except Exception:
        pass

    return row


def revoke_key(key_id: str) -> bool:
    return _sb_patch(f"api_keys?id=eq.{key_id}", {'status': 'revoked'})


def has_scope(key_row: dict, required_scope: str) -> bool:
    """Check if a validated key has a specific scope."""
    scopes = key_row.get('scopes') or []
    return required_scope in scopes or 'admin' in scopes


def get_org_keys(org_id: str) -> List[dict]:
    return _sb_get(
        f"api_keys?org_id=eq.{org_id}&order=created_at.desc&select=id,key_prefix,label,scopes,status,last_used_at,created_at"
    )


# ─── Usage Logging ────────────────────────────────────────────────────────────

def log_usage(
    api_key_id: str,
    endpoint: str,
    method: str        = 'POST',
    status_code: int   = 200,
    response_ms: int   = 0,
    org_id: Optional[str] = None,
) -> None:
    """Fire-and-forget usage log."""
    row: dict = {
        'api_key_id':  api_key_id,
        'endpoint':    endpoint,
        'method':      method,
        'status_code': status_code,
        'response_ms': response_ms,
    }
    if org_id:
        row['org_id'] = org_id
    try:
        _sb_post('api_usage_logs', row)
    except Exception:
        pass


def get_usage_stats(api_key_id: str, limit: int = 1000) -> dict:
    rows = _sb_get(
        f"api_usage_logs?api_key_id=eq.{api_key_id}&order=created_at.desc&limit={limit}&select=*"
    )
    total       = len(rows)
    success     = sum(1 for r in rows if (r.get('status_code') or 0) < 400)
    endpoints   = {}
    for r in rows:
        ep = r.get('endpoint', 'unknown')
        endpoints[ep] = endpoints.get(ep, 0) + 1
    return {
        'total_calls': total,
        'success_calls': success,
        'error_calls': total - success,
        'endpoints': endpoints,
    }
