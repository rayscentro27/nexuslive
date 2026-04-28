"""
Briefing Service.

Stores and retrieves executive_briefings produced by the CEO agent.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List

logger = logging.getLogger('BriefingService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=representation',
    }


def _sb_post(path: str, body: dict) -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            rows = json.loads(r.read())
            return rows[0] if rows else None
    except urllib.error.HTTPError as e:
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def store_briefing(
    headline: str,
    summary: str,
    brief_type: str              = 'periodic',
    top_updates: Optional[list]  = None,
    blockers: Optional[list]     = None,
    recommended_actions: Optional[list] = None,
) -> Optional[str]:
    """Write a new executive briefing. Returns row id."""
    row = {
        'brief_type':           brief_type,
        'headline':             headline,
        'summary':              summary,
        'top_updates':          top_updates or [],
        'blockers':             blockers or [],
        'recommended_actions':  recommended_actions or [],
    }
    result = _sb_post('executive_briefings', row)
    if result:
        logger.info(f"Briefing [{brief_type}] stored id={result.get('id')}")
        return result.get('id')
    return None


def get_latest_briefing(brief_type: Optional[str] = None) -> Optional[dict]:
    """Return the most recent briefing, optionally filtered by type."""
    parts = ['order=created_at.desc', 'limit=1', 'select=*']
    if brief_type:
        parts.append(f'brief_type=eq.{brief_type}')
    rows = _sb_get(f"executive_briefings?{'&'.join(parts)}")
    return rows[0] if rows else None


def get_recent_briefings(
    hours: int = 48,
    brief_type: Optional[str] = None,
    limit: int = 10,
) -> List[dict]:
    """Return recent briefings."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    parts  = [
        f'created_at=gt.{cutoff}',
        'order=created_at.desc',
        f'limit={limit}',
        'select=*',
    ]
    if brief_type:
        parts.append(f'brief_type=eq.{brief_type}')
    return _sb_get(f"executive_briefings?{'&'.join(parts)}")
