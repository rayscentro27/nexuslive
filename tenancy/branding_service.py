"""
Branding + White-Label Service.

Manages branding_configs and org_module_configs.
Resellers can brand Nexus under their own identity — their clients
see their brand name, colors, and domain instead of Nexus.

Usage:
    from tenancy.branding_service import get_branding, set_branding

    brand = get_branding(org_id)
    brand_name = brand.get('brand_name', 'Nexus')
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger('BrandingService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Default branding (used when no org-specific config exists)
DEFAULT_BRANDING = {
    'brand_name':      'Nexus',
    'primary_color':   '#1a1a2e',
    'secondary_color': '#16213e',
    'support_email':   'support@nexus.ai',
    'telegram_handle': '@NexusSupport',
}

# All available modules
ALL_MODULES = [
    'funding', 'trading', 'grants', 'saas',
    'voice', 'ads', 'research', 'credit',
]


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


def _upsert(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Upsert {path} → {e}")
        return False


# ─── Branding ─────────────────────────────────────────────────────────────────

def get_branding(org_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Return branding config for an org.
    Falls back to DEFAULT_BRANDING for any missing fields.
    """
    if not org_id:
        return DEFAULT_BRANDING.copy()

    rows = _sb_get(f"branding_configs?org_id=eq.{org_id}&select=*&limit=1")
    if not rows:
        return DEFAULT_BRANDING.copy()

    config = DEFAULT_BRANDING.copy()
    config.update({k: v for k, v in rows[0].items() if v is not None})
    return config


def set_branding(
    org_id: str,
    brand_name: Optional[str]      = None,
    logo_url: Optional[str]        = None,
    primary_color: Optional[str]   = None,
    secondary_color: Optional[str] = None,
    domain: Optional[str]          = None,
    support_email: Optional[str]   = None,
    telegram_handle: Optional[str] = None,
) -> bool:
    now  = datetime.now(timezone.utc).isoformat()
    row: dict = {'org_id': org_id, 'updated_at': now}
    if brand_name:
        row['brand_name'] = brand_name
    if logo_url:
        row['logo_url'] = logo_url
    if primary_color:
        row['primary_color'] = primary_color
    if secondary_color:
        row['secondary_color'] = secondary_color
    if domain:
        row['domain'] = domain
    if support_email:
        row['support_email'] = support_email
    if telegram_handle:
        row['telegram_handle'] = telegram_handle
    return _upsert('branding_configs', row)


def get_brand_name(org_id: Optional[str] = None) -> str:
    return get_branding(org_id).get('brand_name', 'Nexus')


# ─── Module Config ────────────────────────────────────────────────────────────

def get_enabled_modules(org_id: str) -> list:
    """Return list of enabled module names for an org."""
    rows = _sb_get(
        f"org_module_configs?org_id=eq.{org_id}&enabled=eq.true&select=module_name"
    )
    enabled = [r['module_name'] for r in rows]
    # Default: all modules enabled if no explicit config
    return enabled if enabled else ALL_MODULES[:]


def enable_module(org_id: str, module_name: str) -> bool:
    from tenancy.rbac import set_module_enabled
    return set_module_enabled(org_id, module_name, True)


def disable_module(org_id: str, module_name: str) -> bool:
    from tenancy.rbac import set_module_enabled
    return set_module_enabled(org_id, module_name, False)


def seed_all_modules_enabled(org_id: str) -> int:
    """Enable all modules for an org (e.g. on new reseller setup)."""
    count = 0
    for module in ALL_MODULES:
        ok = enable_module(org_id, module)
        if ok:
            count += 1
    return count
