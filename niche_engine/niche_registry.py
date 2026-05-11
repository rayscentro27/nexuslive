"""
Niche Registry.

CRUD for niche_candidates table.

Status lifecycle: candidate → validated → launched → rejected

Scores (each 0–100):
  demand_score       — how many people want this
  competition_score  — how crowded (lower = better, inverted on total)
  monetization_score — revenue potential
  total_score        — weighted composite (computed here)

Usage:
    from niche_engine.niche_registry import (
        upsert_niche, get_niche, list_niches,
        update_status, get_top_niches,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('NicheRegistry')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_STATUSES = {'candidate', 'validated', 'launched', 'rejected'}

# Weights for total_score composite
DEMAND_WEIGHT        = 0.40
COMPETITION_WEIGHT   = 0.25   # inverted: low competition is good
MONETIZATION_WEIGHT  = 0.35


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


def _sb_post(path: str, body: dict, prefer: str = 'return=representation') -> Optional[dict]:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    h    = _headers()
    h['Prefer'] = prefer
    req  = urllib.request.Request(url, data=data, headers=h, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            if prefer == 'return=minimal':
                return {}
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


def compute_total_score(demand: float, competition: float, monetization: float) -> float:
    """
    Composite score.
    Competition is inverted: low competition = high score component.
    """
    comp_inverted = 100.0 - min(max(competition, 0), 100)
    total = (
        demand       * DEMAND_WEIGHT +
        comp_inverted * COMPETITION_WEIGHT +
        monetization  * MONETIZATION_WEIGHT
    )
    return round(min(max(total, 0), 100), 2)


def upsert_niche(
    name: str,
    demand_score: float          = 0,
    competition_score: float     = 0,
    monetization_score: float    = 0,
    research_sources: Optional[list] = None,
    notes: Optional[str]         = None,
) -> Optional[dict]:
    """Insert or update a niche candidate (UNIQUE on name)."""
    total = compute_total_score(demand_score, competition_score, monetization_score)
    now   = datetime.now(timezone.utc).isoformat()
    row: dict = {
        'name':               name,
        'demand_score':       demand_score,
        'competition_score':  competition_score,
        'monetization_score': monetization_score,
        'total_score':        total,
        'updated_at':         now,
    }
    if research_sources is not None:
        row['research_sources'] = research_sources
    if notes:
        row['notes'] = notes

    return _sb_post(
        'niche_candidates',
        row,
        prefer='resolution=merge-duplicates,return=representation',
    )


def get_niche(name: str) -> Optional[dict]:
    rows = _sb_get(f"niche_candidates?name=eq.{name}&select=*&limit=1")
    return rows[0] if rows else None


def list_niches(
    status: Optional[str] = None,
    min_score: float       = 0,
    limit: int             = 50,
) -> List[dict]:
    parts = [f"select=*&order=total_score.desc&limit={limit}"]
    if status:
        parts.append(f"status=eq.{status}")
    if min_score > 0:
        parts.append(f"total_score=gte.{min_score}")
    return _sb_get(f"niche_candidates?{'&'.join(parts)}")


def get_top_niches(limit: int = 5) -> List[dict]:
    return list_niches(status='candidate', min_score=60, limit=limit)


def update_status(name: str, status: str) -> bool:
    if status not in VALID_STATUSES:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"niche_candidates?name=eq.{name}",
        {'status': status, 'updated_at': now},
    )
