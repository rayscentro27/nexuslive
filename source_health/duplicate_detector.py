"""
Duplicate Source Detector.

Flags likely duplicate research sources based on:
  1. Exact normalized URL match (already prevented by unique constraint —
     still checks for near-duplicates with trailing params stripped)
  2. Same domain + same source_type
  3. Same label (case-insensitive, stripped)

Writes flagged pairs to source_duplicates.
Does NOT auto-delete — human review required.
similarity_score is 0-1 (1 = certain duplicate).

Run standalone:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m source_health.duplicate_detector
"""

import os
import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import List, Optional, Tuple

logger = logging.getLogger('DuplicateDetector')

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
            return None  # already flagged
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


def _strip_url(url: str) -> str:
    """Normalize URL: lowercase scheme+netloc, strip path trailing slash, drop query/fragment."""
    try:
        p = urllib.parse.urlparse(url.strip().lower())
        return urllib.parse.urlunparse((
            p.scheme, p.netloc, p.path.rstrip('/'), '', '', ''
        ))
    except Exception:
        return url.strip().lower()


def _flag_duplicate(
    source_id: str,
    duplicate_of: str,
    similarity: float,
    reason: str,
) -> bool:
    """Insert a source_duplicates row (UNIQUE — silently skips if already flagged)."""
    # Ensure canonical order (lower UUID first) to avoid (A,B) and (B,A) both inserted
    a, b = sorted([source_id, duplicate_of])
    row = {
        'source_id':              a,
        'duplicate_of_source_id': b,
        'similarity_score':       round(similarity, 3),
        'reason':                 reason,
        'status':                 'flagged',
    }
    result = _sb_post('source_duplicates', row)
    return result is not None


# ─── Detection strategies ──────────────────────────────────────────────────────

def _detect_url_near_duplicates(sources: List[dict]) -> int:
    """Flag sources whose stripped URLs are identical."""
    seen: dict = {}
    flagged = 0
    for src in sources:
        key = _strip_url(src.get('source_url', ''))
        if not key:
            continue
        if key in seen:
            ok = _flag_duplicate(
                src['id'], seen[key],
                similarity=0.99,
                reason='near-duplicate URL (params stripped)',
            )
            if ok:
                flagged += 1
                logger.info(f"URL near-dup: {src.get('label')} ↔ strip={key[:60]}")
        else:
            seen[key] = src['id']
    return flagged


def _detect_domain_type_duplicates(sources: List[dict]) -> int:
    """Flag sources with the same domain + source_type."""
    seen: dict = {}
    flagged = 0
    for src in sources:
        domain  = (src.get('domain') or '').strip().lower()
        stype   = (src.get('source_type') or '').strip().lower()
        if not domain or not stype:
            continue
        key = f"{stype}::{domain}"
        if key in seen:
            ok = _flag_duplicate(
                src['id'], seen[key],
                similarity=0.85,
                reason=f'same domain+type ({stype}, {domain})',
            )
            if ok:
                flagged += 1
                logger.info(f"Domain+type dup: {src.get('label')} ({key})")
        else:
            seen[key] = src['id']
    return flagged


def _detect_label_duplicates(sources: List[dict]) -> int:
    """Flag sources with the same normalised label."""
    seen: dict = {}
    flagged = 0
    for src in sources:
        label = (src.get('label') or '').strip().lower()
        if not label or len(label) < 4:
            continue
        if label in seen:
            ok = _flag_duplicate(
                src['id'], seen[label],
                similarity=0.80,
                reason=f'identical label: "{label}"',
            )
            if ok:
                flagged += 1
                logger.info(f"Label dup: '{label}'")
        else:
            seen[label] = src['id']
    return flagged


# ─── Public API ───────────────────────────────────────────────────────────────

def run_duplicate_detection(limit: int = 500) -> int:
    """
    Run all duplicate detection strategies against active sources.
    Returns total number of new pairs flagged.
    """
    sources = _sb_get(
        f"research_sources?status=in.(active,pending_scan)&select=*&limit={limit}"
    )
    if not sources:
        logger.info("No sources to check for duplicates")
        return 0

    total = 0
    total += _detect_url_near_duplicates(sources)
    total += _detect_domain_type_duplicates(sources)
    total += _detect_label_duplicates(sources)

    logger.info(f"Duplicate detection complete: {total} new pair(s) flagged")
    return total


def get_flagged_duplicates(limit: int = 100) -> List[dict]:
    """Return all flagged (unresolved) duplicate pairs."""
    return _sb_get(
        f"source_duplicates?status=eq.flagged&order=similarity_score.desc&limit={limit}&select=*"
    )


def resolve_duplicate(source_id: str, duplicate_of_source_id: str, resolution: str = 'confirmed') -> bool:
    """
    Mark a duplicate pair as resolved.
    resolution: 'confirmed' | 'dismissed'
    """
    a, b = sorted([source_id, duplicate_of_source_id])
    url  = (
        f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/"
        f"source_duplicates"
        f"?source_id=eq.{a}&duplicate_of_source_id=eq.{b}"
    )
    body = json.dumps({'status': resolution}).encode()
    h    = _headers()
    h['Prefer'] = 'return=minimal'
    req  = urllib.request.Request(url, data=body, headers=h, method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Resolve duplicate → {e}")
        return False


if __name__ == '__main__':
    import sys
    _env = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(_env):
        with open(_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    flagged = run_duplicate_detection()
    print(f"Flagged {flagged} duplicate pair(s)")
