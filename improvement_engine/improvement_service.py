"""
Improvement Service.

Review-gated self-improvement system.

DESIGN PRINCIPLE: Candidate generation and scoring are automated.
Promotion to trusted production state ALWAYS requires human approval.
No variant is ever auto-promoted.

Domains supported:
  strategy      — trading/business strategy improvements
  signal        — signal scoring weight adjustments
  funding_logic — funding recommendation threshold changes
  communication — message timing, tone, and reminder patterns
  source        — source selection and scheduling adjustments

Experiment lifecycle:
  proposed → testing → scored → approved → promoted | rejected

Usage:
    from improvement_engine.improvement_service import (
        propose_experiment, add_variant, score_variant,
        approve_variant, reject_variant, get_pending_review,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('ImprovementService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

VALID_DOMAINS    = {'strategy', 'signal', 'funding_logic', 'communication', 'source'}
VALID_EXP_STATUS = {'proposed', 'testing', 'scored', 'approved', 'promoted', 'rejected'}
VALID_VAR_STATUS = {'candidate', 'testing', 'scored', 'approved', 'promoted', 'rejected'}

# Minimum simulated score before a variant is eligible for promotion review
MIN_PROMOTION_SCORE = 0.65


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


# ─── Experiments ──────────────────────────────────────────────────────────────

def propose_experiment(
    domain: str,
    title: str,
    hypothesis: str,
    baseline_config: dict,
    proposed_by: str = 'system',
    org_id: Optional[str] = None,
) -> Optional[dict]:
    """
    Propose a new improvement experiment.
    Starts in 'proposed' status — no action taken yet.
    """
    if domain not in VALID_DOMAINS:
        logger.warning(f"Invalid domain: {domain}")
        return None

    row: dict = {
        'domain':          domain,
        'title':           title,
        'hypothesis':      hypothesis,
        'baseline_config': baseline_config,
        'proposed_by':     proposed_by,
        'status':          'proposed',
    }
    if org_id:
        row['org_id'] = org_id

    result = _sb_post('improvement_experiments', row)
    if result:
        logger.info(f"Experiment proposed: '{title}' domain={domain}")
    return result


def get_experiment(experiment_id: str) -> Optional[dict]:
    rows = _sb_get(f"improvement_experiments?id=eq.{experiment_id}&select=*&limit=1")
    return rows[0] if rows else None


def list_experiments(
    domain: Optional[str]  = None,
    status: Optional[str]  = None,
    limit: int             = 50,
) -> List[dict]:
    parts = [f"select=*&order=created_at.desc&limit={limit}"]
    if domain:
        parts.append(f"domain=eq.{domain}")
    if status:
        parts.append(f"status=eq.{status}")
    return _sb_get(f"improvement_experiments?{'&'.join(parts)}")


def update_experiment_status(experiment_id: str, status: str) -> bool:
    if status not in VALID_EXP_STATUS:
        return False
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"improvement_experiments?id=eq.{experiment_id}",
        {'status': status, 'updated_at': now},
    )


# ─── Candidate Variants ───────────────────────────────────────────────────────

def add_variant(
    experiment_id: str,
    variant_name: str,
    variant_config: dict,
    rationale: str,
    generated_by: str = 'system',
) -> Optional[dict]:
    """
    Add a candidate variant to an experiment.
    Variant starts as 'candidate' — not in production.
    """
    row = {
        'experiment_id': experiment_id,
        'variant_name':  variant_name,
        'variant_config': variant_config,
        'rationale':     rationale,
        'generated_by':  generated_by,
        'status':        'candidate',
        'sim_score':     None,
        'approved_by':   None,
    }
    result = _sb_post('candidate_variants', row)
    if result:
        logger.info(f"Variant added: '{variant_name}' experiment={experiment_id}")
    return result


def score_variant(
    variant_id: str,
    sim_score: float,
    sim_notes: str = '',
) -> bool:
    """
    Record simulated/backtested score for a variant.
    Marks status as 'scored' if score meets minimum.
    """
    status = 'scored' if sim_score >= MIN_PROMOTION_SCORE else 'rejected'
    now    = datetime.now(timezone.utc).isoformat()
    ok = _sb_patch(
        f"candidate_variants?id=eq.{variant_id}",
        {
            'sim_score': sim_score,
            'sim_notes': sim_notes,
            'status':    status,
            'updated_at': now,
        },
    )
    if ok:
        logger.info(f"Variant scored: {variant_id} score={sim_score} → {status}")
    return ok


def approve_variant(
    variant_id: str,
    approved_by: str,
    notes: str = '',
) -> bool:
    """
    Human approves a scored variant for promotion.
    REQUIRED before any variant reaches production state.
    """
    rows = _sb_get(f"candidate_variants?id=eq.{variant_id}&select=status,sim_score&limit=1")
    if not rows:
        return False

    var = rows[0]
    if var.get('status') != 'scored':
        logger.warning(f"Cannot approve variant {variant_id} — status is {var.get('status')}, must be 'scored'")
        return False

    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"candidate_variants?id=eq.{variant_id}",
        {
            'status':      'approved',
            'approved_by': approved_by,
            'approval_notes': notes,
            'approved_at': now,
            'updated_at':  now,
        },
    )


def promote_variant(variant_id: str) -> bool:
    """
    Promote an approved variant to 'promoted' status.
    The consuming system (strategy_review, signal_review, etc.)
    reads 'approved' variants and applies them — this just marks completion.
    """
    rows = _sb_get(f"candidate_variants?id=eq.{variant_id}&select=status&limit=1")
    if not rows or rows[0].get('status') != 'approved':
        logger.warning(f"Cannot promote {variant_id} — must be in 'approved' status")
        return False

    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"candidate_variants?id=eq.{variant_id}",
        {'status': 'promoted', 'promoted_at': now, 'updated_at': now},
    )


def reject_variant(variant_id: str, reason: str = '') -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"candidate_variants?id=eq.{variant_id}",
        {'status': 'rejected', 'rejection_reason': reason, 'updated_at': now},
    )


def get_pending_review(domain: Optional[str] = None, limit: int = 20) -> List[dict]:
    """Variants scored above threshold, awaiting human approval."""
    parts = [f"status=eq.scored&select=*&order=sim_score.desc&limit={limit}"]
    if domain:
        # Join via experiment_id to filter domain (fetch all, filter in Python)
        pass
    rows = _sb_get(f"candidate_variants?{'&'.join(parts)}")
    if domain:
        # Enrich with experiment domain
        enriched = []
        for v in rows:
            exp = get_experiment(v.get('experiment_id', ''))
            if exp and exp.get('domain') == domain:
                v['domain'] = domain
                enriched.append(v)
        return enriched
    return rows


def get_variants_for_experiment(experiment_id: str) -> List[dict]:
    return _sb_get(
        f"candidate_variants?experiment_id=eq.{experiment_id}&select=*&order=sim_score.desc"
    )
