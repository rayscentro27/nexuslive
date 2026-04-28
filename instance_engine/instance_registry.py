"""
Instance Registry.

CRUD for nexus_instances and instance_configs.

Instance status lifecycle: testing → active → scaled → killed

Usage:
    from instance_engine.instance_registry import (
        create_instance, get_instance, update_status,
        set_config, get_config, list_instances,
    )
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('InstanceRegistry')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_STATUSES = {'testing', 'active', 'scaled', 'killed'}


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


# ─── Instance CRUD ────────────────────────────────────────────────────────────

def create_instance(
    niche: str,
    display_name: Optional[str]    = None,
    status: str                    = 'testing',
    config: Optional[dict]         = None,
    parent_instance_id: Optional[str] = None,
) -> Optional[dict]:
    """Create a new nexus instance."""
    row: dict = {
        'niche':  niche,
        'status': status,
        'config': config or {},
    }
    if display_name:
        row['display_name'] = display_name
    if parent_instance_id:
        row['parent_instance_id'] = parent_instance_id
    result = _sb_post('nexus_instances', row)
    if result:
        logger.info(f"Instance created: {result.get('id')} niche={niche}")
    return result


def get_instance(instance_id: str) -> Optional[dict]:
    rows = _sb_get(f"nexus_instances?id=eq.{instance_id}&select=*&limit=1")
    return rows[0] if rows else None


def list_instances(
    status: Optional[str] = None,
    niche: Optional[str]  = None,
    limit: int            = 100,
) -> List[dict]:
    parts = [f"select=*&order=created_at.desc&limit={limit}"]
    if status:
        parts.append(f"status=eq.{status}")
    if niche:
        parts.append(f"niche=eq.{niche}")
    return _sb_get(f"nexus_instances?{'&'.join(parts)}")


def update_status(instance_id: str, status: str) -> bool:
    if status not in VALID_STATUSES:
        logger.warning(f"Invalid status: {status}")
        return False
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"nexus_instances?id=eq.{instance_id}",
        {'status': status, 'updated_at': now},
    )


def update_config(instance_id: str, config: dict) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"nexus_instances?id=eq.{instance_id}",
        {'config': config, 'updated_at': now},
    )


# ─── Instance Configs (key-value store) ───────────────────────────────────────

def set_config(instance_id: str, key: str, value: str) -> bool:
    """Upsert a config key for an instance."""
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/instance_configs"
    body = {'instance_id': instance_id, 'config_key': key, 'config_value': value}
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"set_config {key} → {e}")
        return False


def get_config(instance_id: str, key: str) -> Optional[str]:
    rows = _sb_get(
        f"instance_configs?instance_id=eq.{instance_id}&config_key=eq.{key}&select=config_value&limit=1"
    )
    return rows[0].get('config_value') if rows else None


def get_all_configs(instance_id: str) -> dict:
    rows = _sb_get(
        f"instance_configs?instance_id=eq.{instance_id}&select=config_key,config_value"
    )
    return {r['config_key']: r['config_value'] for r in rows}


def get_instances_by_status() -> dict:
    """Return count per status — used by portfolio manager."""
    rows = _sb_get("nexus_instances?select=status")
    counts: dict = {}
    for r in rows:
        s = r.get('status', 'unknown')
        counts[s] = counts.get(s, 0) + 1
    return counts
