"""
Empire Service.

Decision-support layer for empire-level intelligence.
Provides structured outputs for capital deployment, entity management,
workforce allocation, and regional expansion.

THIS MODULE PROVIDES DECISION SUPPORT ONLY.
It produces recommendations and structured data — not automatic execution.
All real-world capital moves require human approval.

Domains:
  entities        — LLCs, trusts, holding companies, operating entities
  capital         — capital deployment tracking and recommendation
  workforce       — AI/human operator assignments and capacity
  regions         — geographic expansion scoring and priority
  reinvestment    — revenue reinvestment strategy recommendations

Usage:
    from empire.empire_service import (
        register_entity, log_capital_event, get_capital_summary,
        score_region, get_workforce_summary, get_reinvestment_recommendation,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('EmpireService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

ENTITY_TYPES    = {'llc', 'trust', 'holding', 'operating', 'fund', 'partnership'}
CAPITAL_SOURCES = {'revenue', 'funding', 'trading_profit', 'investment', 'reinvestment'}
CAPITAL_USES    = {'operations', 'marketing', 'technology', 'hiring', 'expansion', 'reserve'}
WORKFORCE_ROLES = {'ai_agent', 'human_operator', 'va', 'closer', 'researcher', 'developer'}


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


# ─── Entities ─────────────────────────────────────────────────────────────────

def register_entity(
    name: str,
    entity_type: str,
    state: str           = 'TX',
    purpose: str         = '',
    parent_entity_id: Optional[str] = None,
    org_id: Optional[str] = None,
) -> Optional[dict]:
    """Register a legal entity in the empire structure."""
    row: dict = {
        'name':        name,
        'entity_type': entity_type if entity_type in ENTITY_TYPES else 'llc',
        'state':       state,
        'purpose':     purpose,
        'status':      'active',
    }
    if parent_entity_id:
        row['parent_entity_id'] = parent_entity_id
    if org_id:
        row['org_id'] = org_id
    return _sb_post('empire_entities', row)


def get_entity_tree() -> List[dict]:
    """Return all entities, useful for building ownership tree."""
    return _sb_get("empire_entities?select=*&order=created_at.asc")


# ─── Capital ──────────────────────────────────────────────────────────────────

def log_capital_event(
    amount: float,
    source: str,
    use: str,
    description: str,
    entity_id: Optional[str]   = None,
    instance_id: Optional[str] = None,
    period: Optional[str]      = None,
) -> Optional[dict]:
    """
    Log a capital allocation or deployment event.
    These are records for decision-support — not automated transactions.
    """
    p = period or datetime.now(timezone.utc).strftime('%Y-%m')
    row: dict = {
        'amount':      amount,
        'source':      source if source in CAPITAL_SOURCES else 'revenue',
        'use':         use if use in CAPITAL_USES else 'operations',
        'description': description,
        'period':      p,
        'status':      'logged',
    }
    if entity_id:
        row['entity_id'] = entity_id
    if instance_id:
        row['instance_id'] = instance_id
    return _sb_post('capital_deployments', row)


def get_capital_summary(period: Optional[str] = None) -> dict:
    """Capital flow summary for the current or specified period."""
    p       = period or datetime.now(timezone.utc).strftime('%Y-%m')
    rows    = _sb_get(f"capital_deployments?period=eq.{p}&select=amount,source,use")
    by_use  = {}
    by_src  = {}
    total   = 0.0
    for r in rows:
        amt = float(r.get('amount', 0))
        total += amt
        u = r.get('use', 'other')
        s = r.get('source', 'other')
        by_use[u] = by_use.get(u, 0) + amt
        by_src[s] = by_src.get(s, 0) + amt

    return {
        'period':    p,
        'total':     round(total, 2),
        'by_use':    by_use,
        'by_source': by_src,
    }


def get_reinvestment_recommendation(monthly_revenue: float) -> dict:
    """
    Produce a structured reinvestment allocation recommendation.
    Based on standard growth allocation ratios.
    This is a recommendation — not an execution.
    """
    # Standard allocation model
    allocations = {
        'operations':  round(monthly_revenue * 0.30, 2),
        'marketing':   round(monthly_revenue * 0.25, 2),
        'technology':  round(monthly_revenue * 0.15, 2),
        'reserve':     round(monthly_revenue * 0.20, 2),
        'expansion':   round(monthly_revenue * 0.10, 2),
    }
    return {
        'monthly_revenue':  monthly_revenue,
        'recommendation':   allocations,
        'total_allocated':  round(sum(allocations.values()), 2),
        'model':            'standard_30_25_15_20_10',
        'note':             'Review and approve before any capital deployment.',
    }


# ─── Workforce ────────────────────────────────────────────────────────────────

def register_workforce_member(
    name: str,
    role: str,
    capacity: int         = 100,
    entity_id: Optional[str] = None,
    instance_id: Optional[str] = None,
    metadata: Optional[dict]  = None,
) -> Optional[dict]:
    """Register an AI agent or human operator in the workforce registry."""
    row: dict = {
        'name':     name,
        'role':     role if role in WORKFORCE_ROLES else 'ai_agent',
        'capacity': capacity,
        'status':   'active',
        'metadata': metadata or {},
    }
    if entity_id:
        row['entity_id'] = entity_id
    if instance_id:
        row['instance_id'] = instance_id
    return _sb_post('empire_workforce', row)


def get_workforce_summary() -> dict:
    """Summarize workforce capacity and role distribution."""
    rows = _sb_get("empire_workforce?status=eq.active&select=role,capacity")
    by_role: dict = {}
    total_cap = 0
    for r in rows:
        role = r.get('role', 'unknown')
        cap  = int(r.get('capacity', 0))
        by_role[role] = by_role.get(role, 0) + 1
        total_cap += cap

    return {
        'total_members':   sum(by_role.values()),
        'total_capacity':  total_cap,
        'by_role':         by_role,
    }


# ─── Regions ──────────────────────────────────────────────────────────────────

def score_region(
    region_name: str,
    market_size: float    = 0,
    competition: float    = 0,
    regulatory_ease: float = 0,
    existing_presence: bool = False,
    notes: str            = '',
) -> Optional[dict]:
    """
    Score and record a geographic region for expansion analysis.
    total_score = market_size(40%) + competition_inverted(30%) + regulatory(30%)
    """
    comp_inv    = 100.0 - min(max(competition, 0), 100)
    total       = (market_size * 0.40 + comp_inv * 0.30 + regulatory_ease * 0.30)
    row: dict = {
        'region_name':       region_name,
        'market_size_score': market_size,
        'competition_score': competition,
        'regulatory_score':  regulatory_ease,
        'total_score':       round(total, 2),
        'existing_presence': existing_presence,
        'notes':             notes,
        'status':            'candidate',
    }
    return _sb_post('empire_regions', row)


def get_top_expansion_regions(limit: int = 5) -> List[dict]:
    """Return top candidate regions by expansion score."""
    return _sb_get(
        f"empire_regions?status=eq.candidate&select=*&order=total_score.desc&limit={limit}"
    )


def get_empire_state() -> dict:
    """Full empire state summary for CEO briefing."""
    from revenue_engine.revenue_service import get_all_time_total, get_monthly_total
    from portfolio.portfolio_service import get_latest_snapshot

    period   = datetime.now(timezone.utc).strftime('%Y-%m')
    monthly  = get_monthly_total(period=period)
    all_time = get_all_time_total()
    snapshot = get_latest_snapshot()
    cap_sum  = get_capital_summary(period=period)
    wf_sum   = get_workforce_summary()
    regions  = get_top_expansion_regions(3)
    entities = _sb_get("empire_entities?status=eq.active&select=name,entity_type")

    return {
        'period':          period,
        'monthly_revenue': monthly,
        'all_time_revenue': all_time,
        'portfolio':       snapshot,
        'capital':         cap_sum,
        'workforce':       wf_sum,
        'top_regions':     regions,
        'entities':        entities,
    }
