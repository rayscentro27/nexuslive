"""
Organization Service.

Manages organizations and organization_users.
Each organization is an isolated tenant — all agent logic
should pass org_id to filter data appropriately.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('OrgService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_ORG_TYPES = {'client', 'reseller', 'internal'}
VALID_ROLES     = {'admin', 'manager', 'agent', 'client'}


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
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return None
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
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


# ─── Organizations ────────────────────────────────────────────────────────────

def create_org(
    org_name: str,
    org_type: str          = 'client',
    owner_email: str       = '',
) -> Optional[dict]:
    if org_type not in VALID_ORG_TYPES:
        logger.warning(f"Invalid org_type: {org_type}")
        org_type = 'client'
    return _sb_post('organizations', {
        'org_name':    org_name,
        'org_type':    org_type,
        'owner_email': owner_email,
        'status':      'active',
    })


def get_org(org_id: str) -> Optional[dict]:
    rows = _sb_get(f"organizations?id=eq.{org_id}&select=*&limit=1")
    return rows[0] if rows else None


def get_org_by_name(org_name: str) -> Optional[dict]:
    import urllib.parse
    rows = _sb_get(
        f"organizations?org_name=eq.{urllib.parse.quote(org_name)}&select=*&limit=1"
    )
    return rows[0] if rows else None


def get_all_orgs(active_only: bool = True) -> List[dict]:
    f = "&status=eq.active" if active_only else ""
    return _sb_get(f"organizations?select=*{f}&order=org_name.asc")


def deactivate_org(org_id: str) -> bool:
    return _sb_patch(f"organizations?id=eq.{org_id}", {'status': 'inactive'})


# ─── Organization Users ───────────────────────────────────────────────────────

def add_user_to_org(
    org_id: str,
    user_id: str,
    role: str = 'client',
) -> Optional[dict]:
    if role not in VALID_ROLES:
        logger.warning(f"Invalid role: {role}, defaulting to client")
        role = 'client'
    return _sb_post('organization_users', {
        'org_id':  org_id,
        'user_id': user_id,
        'role':    role,
        'status':  'active',
    })


def get_user_role(org_id: str, user_id: str) -> Optional[str]:
    rows = _sb_get(
        f"organization_users?org_id=eq.{org_id}&user_id=eq.{user_id}&select=role&limit=1"
    )
    return rows[0].get('role') if rows else None


def get_org_members(org_id: str, role: Optional[str] = None) -> List[dict]:
    extra = f"&role=eq.{role}" if role else ''
    return _sb_get(
        f"organization_users?org_id=eq.{org_id}{extra}&status=eq.active&select=*"
    )


def update_user_role(org_id: str, user_id: str, new_role: str) -> bool:
    if new_role not in VALID_ROLES:
        return False
    return _sb_patch(
        f"organization_users?org_id=eq.{org_id}&user_id=eq.{user_id}",
        {'role': new_role},
    )
