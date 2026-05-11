"""
Role-Based Access Control (RBAC).

Role hierarchy (highest to lowest):
  admin > manager > agent > client

Usage:
    from tenancy.rbac import require_role, has_permission, can_access_module

    # Check if user has at least 'manager' level in an org
    if not has_permission(user_id, org_id, required_role='manager'):
        raise PermissionError("Insufficient access")

    # Check if a module is enabled for an org
    if not can_access_module(org_id, 'trading'):
        return {'error': 'Module not enabled for this org'}
"""

import os
import json
import logging
import urllib.request
from typing import Optional

logger = logging.getLogger('RBAC')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Role hierarchy — lower index = more privileged
ROLE_HIERARCHY = ['admin', 'manager', 'agent', 'client']


def _role_level(role: str) -> int:
    """Lower number = more privileged. Returns 999 if unknown."""
    try:
        return ROLE_HIERARCHY.index(role)
    except ValueError:
        return 999


def _sb_get(path: str) -> list:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"RBAC GET {path} → {e}")
        return []


def has_permission(user_id: str, org_id: str, required_role: str = 'client') -> bool:
    """
    Return True if the user's role in the org is at least required_role.
    admin can do everything. client can only do client-level things.
    """
    rows = _sb_get(
        f"organization_users?org_id=eq.{org_id}&user_id=eq.{user_id}"
        f"&status=eq.active&select=role&limit=1"
    )
    if not rows:
        return False
    user_role = rows[0].get('role', 'client')
    return _role_level(user_role) <= _role_level(required_role)


def get_user_orgs(user_id: str) -> list:
    """Return all orgs and roles for a user."""
    return _sb_get(
        f"organization_users?user_id=eq.{user_id}&status=eq.active&select=org_id,role"
    )


def can_access_module(org_id: str, module_name: str) -> bool:
    """
    Return True if a module is enabled for an org.
    Defaults to True if no explicit config exists (opt-out model).
    """
    rows = _sb_get(
        f"org_module_configs?org_id=eq.{org_id}&module_name=eq.{module_name}&select=enabled&limit=1"
    )
    if not rows:
        return True  # no config = enabled by default
    return bool(rows[0].get('enabled', True))


def require_role(user_id: str, org_id: str, required_role: str = 'client') -> None:
    """Raise PermissionError if user lacks the required role."""
    if not has_permission(user_id, org_id, required_role):
        raise PermissionError(
            f"User {user_id} does not have '{required_role}' access in org {org_id}"
        )


def set_module_enabled(org_id: str, module_name: str, enabled: bool) -> bool:
    """Enable or disable a module for an org."""
    from datetime import datetime, timezone
    key  = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/org_module_configs"
    body = json.dumps({
        'org_id':      org_id,
        'module_name': module_name,
        'enabled':     enabled,
        'updated_at':  datetime.now(timezone.utc).isoformat(),
    }).encode()
    h = {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'resolution=merge-duplicates,return=minimal',
    }
    req = urllib.request.Request(url, data=body, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Set module enabled → {e}")
        return False
