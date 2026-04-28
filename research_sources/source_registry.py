"""
Source Registry.

Manages research_sources — the persistent list of YouTube channels,
websites, and feeds that the research pipeline scans.

Source types: youtube_channel, website, rss_feed, generic

Handoff flow:
  admin_command → add_source() → research_sources row created
               → system_event(source_scan_queued) emitted
               → research agent picks up event → scans → writes summary
"""

import os
import json
import logging
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger('SourceRegistry')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

ALLOWED_SOURCE_TYPES = {'youtube_channel', 'website', 'rss_feed', 'generic'}


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
        if e.code == 409:
            return None  # duplicate — handled by caller
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


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_url(url: str) -> Tuple[bool, str]:
    """Return (valid, error_message)."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False, f'URL scheme must be http or https, got: {parsed.scheme}'
        if not parsed.netloc:
            return False, 'URL missing domain'
        return True, ''
    except Exception as e:
        return False, str(e)


def _extract_domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lstrip('www.') or url[:60]
    except Exception:
        return url[:60]


def _normalise_url(url: str) -> str:
    """Strip trailing slashes and fragments for consistent dedup."""
    try:
        p = urllib.parse.urlparse(url.strip())
        return urllib.parse.urlunparse((
            p.scheme, p.netloc, p.path.rstrip('/'), p.params, p.query, ''
        ))
    except Exception:
        return url.strip()


# ─── Public API ───────────────────────────────────────────────────────────────

def check_duplicate(source_url: str) -> Optional[dict]:
    """Return existing source row if this URL already exists, else None."""
    norm = _normalise_url(source_url)
    rows = _sb_get(
        f"research_sources?source_url=eq.{urllib.parse.quote(norm)}&select=*&limit=1"
    )
    return rows[0] if rows else None


def add_source(
    source_type: str,
    source_url: str,
    label: Optional[str]      = None,
    domain: Optional[str]     = None,
    priority: str             = 'medium',
    added_by: str             = 'admin',
    command_id: Optional[str] = None,
) -> Tuple[Optional[str], str]:
    """
    Add a new research source.
    Returns (source_id, message) — source_id is None on failure.
    """
    # Validate source type
    if source_type not in ALLOWED_SOURCE_TYPES:
        return None, f'Invalid source_type: {source_type}. Allowed: {ALLOWED_SOURCE_TYPES}'

    # Validate URL
    url_ok, url_err = _validate_url(source_url)
    if not url_ok:
        return None, f'URL validation failed: {url_err}'

    # Normalise
    norm_url = _normalise_url(source_url)

    # Duplicate check
    existing = check_duplicate(norm_url)
    if existing:
        return None, f'Source already exists (id={existing["id"]}, status={existing["status"]})'

    # Derive domain and label
    resolved_domain = domain or _extract_domain(norm_url)
    resolved_label  = label or resolved_domain

    now = datetime.now(timezone.utc).isoformat()
    row: dict = {
        'source_type': source_type,
        'source_url':  norm_url,
        'label':       resolved_label,
        'domain':      resolved_domain,
        'status':      'pending_scan',
        'priority':    priority,
        'added_by':    added_by,
        'updated_at':  now,
    }

    result = _sb_post('research_sources', row)
    if not result:
        return None, 'Failed to insert into research_sources'

    source_id = result.get('id')
    logger.info(f"Source added: {source_type} {norm_url} id={source_id}")

    # Auto-apply scan policy (creates schedule)
    try:
        from source_scheduling.policy_service import apply_policy_to_source
        policy = apply_policy_to_source(
            source_id=source_id,
            source_type=source_type,
            domain=resolved_domain,
        )
        # Override priority from policy if higher
        policy_priority = policy.get('default_priority', priority)
        if policy_priority != priority:
            _sb_patch(
                f"research_sources?id=eq.{source_id}",
                {'priority': policy_priority, 'updated_at': now},
            )
    except Exception as e:
        logger.warning(f"Policy apply failed for {source_id}: {e}")

    # Emit event so the research agent can pick it up
    try:
        from autonomy.event_emitter import emit_event
        emit_event(
            event_type='source_scan_queued',
            client_id=None,
            payload={
                'source_id':   source_id,
                'source_type': source_type,
                'source_url':  norm_url,
                'label':       resolved_label,
                'domain':      resolved_domain,
                'priority':    priority,
                'command_id':  command_id or '',
            },
        )
    except Exception as e:
        logger.warning(f"Could not emit source_scan_queued event: {e}")

    return source_id, f'Source added: {resolved_label} ({source_type})'


def queue_rescan(label_or_url: str) -> Tuple[bool, str]:
    """Find an existing source by label or URL and set it to pending_scan."""
    val  = label_or_url.strip()
    norm = _normalise_url(val)

    # Try URL match
    rows = _sb_get(
        f"research_sources?source_url=eq.{urllib.parse.quote(norm)}&select=id,label,source_type&limit=1"
    )
    # Try label match if URL not found
    if not rows:
        rows = _sb_get(
            f"research_sources?label=ilike.{urllib.parse.quote('%' + val[:60] + '%')}&select=id,label,source_type&limit=1"
        )

    if not rows:
        return False, f'Source not found: {val}'

    source = rows[0]
    now    = datetime.now(timezone.utc).isoformat()
    ok     = _sb_patch(
        f"research_sources?id=eq.{source['id']}",
        {'status': 'pending_scan', 'updated_at': now}
    )
    if ok:
        # Emit rescan event
        try:
            from autonomy.event_emitter import emit_event
            emit_event(
                event_type='source_rescan_queued',
                client_id=None,
                payload={'source_id': source['id'], 'label': source.get('label')},
            )
        except Exception:
            pass
        return True, f'Rescan queued for: {source.get("label", val)}'

    return False, 'Failed to update source status'


def get_active_sources(source_type: Optional[str] = None, limit: int = 100) -> list:
    """Return active sources, optionally filtered by type."""
    parts = ['status=eq.active', f'limit={limit}', 'select=*', 'order=priority.asc,created_at.asc']
    if source_type:
        parts.append(f'source_type=eq.{source_type}')
    return _sb_get(f"research_sources?{'&'.join(parts)}")


def get_pending_sources(limit: int = 50) -> list:
    """Return sources queued for scanning."""
    return _sb_get(
        f"research_sources?status=eq.pending_scan&order=priority.asc,updated_at.asc&limit={limit}&select=*"
    )


def mark_source_scanned(source_id: str) -> bool:
    """Mark a source as active after a successful scan."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"research_sources?id=eq.{source_id}",
        {'status': 'active', 'updated_at': now}
    )


def mark_source_error(source_id: str, error_msg: str = '') -> bool:
    """Mark a source as error after a failed scan."""
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"research_sources?id=eq.{source_id}",
        {'status': 'error', 'updated_at': now}
    )
