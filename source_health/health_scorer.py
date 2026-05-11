"""
Source Health Scorer.

Computes a composite health score (0-100) for each research source.

Score components:
  freshness_score       0-20  — how recently the source was scanned
  content_quality_score 0-30  — ratio of useful artifacts (summaries) to scans
  signal_yield_score    0-25  — how many signals the source produced
  strategy_yield_score  0-15  — how many strategies the source produced
  noise_score           0-20  — inverted noise penalty (many errors = low score)

score_total = sum of all five components (max 100)

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m source_health.health_scorer
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('HealthScorer')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Freshness thresholds
FRESH_HOURS  = 24    # scanned within 24h → full freshness
STALE_HOURS  = 168   # scanned within 7 days → partial
DEAD_HOURS   = 720   # > 30 days → zero freshness


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


# ─── Score Components ──────────────────────────────────────────────────────────

def _freshness_score(source: dict) -> float:
    """0-20 based on time since last scan."""
    updated_raw = source.get('updated_at') or source.get('created_at', '')
    if not updated_raw:
        return 0.0
    try:
        updated = datetime.fromisoformat(updated_raw.replace('Z', '+00:00'))
        age_hours = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
    except Exception:
        return 0.0

    if age_hours <= FRESH_HOURS:
        return 20.0
    if age_hours <= STALE_HOURS:
        # linear decay from 20 → 10
        frac = (age_hours - FRESH_HOURS) / (STALE_HOURS - FRESH_HOURS)
        return round(20.0 - (frac * 10.0), 2)
    if age_hours <= DEAD_HOURS:
        # linear decay from 10 → 2
        frac = (age_hours - STALE_HOURS) / (DEAD_HOURS - STALE_HOURS)
        return round(10.0 - (frac * 8.0), 2)
    return 2.0


def _content_quality_score(source_id: str) -> float:
    """0-30 based on ratio of research rows to scans attempted."""
    rows = _sb_get(
        f"research?source_id=eq.{source_id}&select=id&limit=200"
    )
    count = len(rows)
    if count == 0:
        return 0.0
    if count >= 20:
        return 30.0
    # linear scale: 1 row=1.5, 20 rows=30
    return round(count * 1.5, 2)


def _signal_yield_score(source_id: str) -> float:
    """0-25 based on number of signals attributed to this source."""
    rows = _sb_get(
        f"research_artifacts?source_id=eq.{source_id}&artifact_type=eq.signal&select=id&limit=100"
    )
    count = len(rows)
    if count == 0:
        return 0.0
    if count >= 10:
        return 25.0
    return round(count * 2.5, 2)


def _strategy_yield_score(source_id: str) -> float:
    """0-15 based on number of strategy extractions from this source."""
    rows = _sb_get(
        f"research_artifacts?source_id=eq.{source_id}&artifact_type=eq.strategy&select=id&limit=100"
    )
    count = len(rows)
    if count == 0:
        return 0.0
    if count >= 5:
        return 15.0
    return round(count * 3.0, 2)


def _noise_score(source: dict) -> float:
    """0-20 inverted: sources with status=error lose points."""
    status = source.get('status', '')
    if status == 'error':
        return 0.0
    if status == 'pending_scan':
        return 10.0   # neutral — not yet evaluated
    return 20.0        # active = full noise score (clean source)


# ─── Public API ───────────────────────────────────────────────────────────────

def score_source(source: dict) -> dict:
    """
    Compute all health score components for a single source dict.
    Returns a dict suitable for upsert into source_health_scores.
    """
    source_id = source.get('id', '')

    freshness  = _freshness_score(source)
    quality    = _content_quality_score(source_id)
    signal     = _signal_yield_score(source_id)
    strategy   = _strategy_yield_score(source_id)
    noise      = _noise_score(source)
    total      = round(freshness + quality + signal + strategy + noise, 2)

    return {
        'source_id':             source_id,
        'score_total':           total,
        'content_quality_score': quality,
        'signal_yield_score':    signal,
        'strategy_yield_score':  strategy,
        'freshness_score':       freshness,
        'noise_score':           noise,
        'last_evaluated_at':     datetime.now(timezone.utc).isoformat(),
    }


def upsert_health_score(score_row: dict) -> bool:
    """Upsert a health score row (UNIQUE on source_id)."""
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/source_health_scores"
    data = json.dumps(score_row).encode()
    h    = _headers()
    h['Prefer'] = 'resolution=merge-duplicates,return=minimal'
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except Exception as e:
        logger.error(f"Upsert health score → {e}")
        return False


def score_all_sources(limit: int = 200) -> int:
    """
    Score every active + pending source.
    Returns count of sources scored.
    """
    sources = _sb_get(
        f"research_sources?status=in.(active,pending_scan,error)&select=*&limit={limit}"
    )
    scored = 0
    for src in sources:
        row = score_source(src)
        ok  = upsert_health_score(row)
        if ok:
            scored += 1
            logger.info(
                f"Scored: {src.get('label', src.get('id','?'))} "
                f"total={row['score_total']} "
                f"(fresh={row['freshness_score']}, "
                f"quality={row['content_quality_score']}, "
                f"signal={row['signal_yield_score']}, "
                f"strategy={row['strategy_yield_score']}, "
                f"noise={row['noise_score']})"
            )
    return scored


def get_health_scores(min_score: float = 0, limit: int = 100) -> list:
    """Return health scores sorted by total descending."""
    return _sb_get(
        f"source_health_scores?score_total=gte.{min_score}"
        f"&order=score_total.desc&limit={limit}&select=*"
    )


def get_low_health_sources(threshold: float = 40, limit: int = 50) -> list:
    """Return sources with health score below threshold."""
    return _sb_get(
        f"source_health_scores?score_total=lt.{threshold}"
        f"&order=score_total.asc&limit={limit}&select=*"
    )
