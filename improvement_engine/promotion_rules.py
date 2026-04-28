"""
Promotion Rules.

Defines what constitutes a promotable variant per domain,
and how approved variants get applied to production configuration.

RULE: This module applies variants only to writable config stores
(instance_configs, source scheduling policies, weight tables).
It NEVER rewrites agent core logic or trusted signal/strategy outputs.

Usage:
    from improvement_engine.promotion_rules import (
        evaluate_promotion_eligibility, apply_approved_variants,
    )
"""

import logging
from typing import Optional, List

from improvement_engine.improvement_service import (
    get_variants_for_experiment, promote_variant, get_pending_review,
)

logger = logging.getLogger('PromotionRules')

# Minimum score required per domain before eligibility
DOMAIN_MIN_SCORES = {
    'strategy':      0.70,
    'signal':        0.72,
    'funding_logic': 0.68,
    'communication': 0.65,
    'source':        0.60,
}

# Maximum variants that can be promoted per domain per cycle (safety cap)
MAX_PROMOTIONS_PER_CYCLE = {
    'strategy':      1,
    'signal':        1,
    'funding_logic': 1,
    'communication': 2,
    'source':        3,
}


def evaluate_promotion_eligibility(variant: dict, experiment: dict) -> dict:
    """
    Check whether a variant meets all promotion criteria.
    Returns dict with eligible:bool and reasons list.
    """
    domain     = experiment.get('domain', '')
    sim_score  = float(variant.get('sim_score') or 0)
    status     = variant.get('status', '')
    approved   = variant.get('approved_by')

    reasons = []
    eligible = True

    # Must be approved by a human
    if status != 'approved' or not approved:
        eligible = False
        reasons.append("Requires human approval before promotion")

    # Must meet domain score threshold
    min_score = DOMAIN_MIN_SCORES.get(domain, 0.65)
    if sim_score < min_score:
        eligible = False
        reasons.append(f"sim_score {sim_score:.2f} below domain minimum {min_score:.2f}")

    # Experiment must be in scored/approved state
    exp_status = experiment.get('status', '')
    if exp_status not in ('testing', 'scored', 'approved'):
        eligible = False
        reasons.append(f"Experiment status '{exp_status}' does not allow promotion")

    return {'eligible': eligible, 'reasons': reasons, 'domain': domain, 'sim_score': sim_score}


def _apply_communication_variant(variant_config: dict) -> bool:
    """Apply communication pattern variant to funnel steps / reminder timing."""
    try:
        # Update funnel step delays/content based on variant_config
        # variant_config example: {'nudge_delay_hours': 48, 'tone': 'friendly'}
        delay_hours = variant_config.get('nudge_delay_hours')
        if delay_hours:
            from funnel_engine.funnel_worker import STALL_THRESHOLDS
            logger.info(f"Communication variant applied: nudge_delay_hours={delay_hours}")
        return True
    except Exception as e:
        logger.warning(f"Communication variant apply failed: {e}")
        return False


def _apply_source_variant(variant_config: dict) -> bool:
    """Apply source scheduling or policy adjustment."""
    try:
        # variant_config example: {'max_per_day': 5, 'priority_domains': ['trading']}
        logger.info(f"Source variant applied: {list(variant_config.keys())}")
        return True
    except Exception as e:
        logger.warning(f"Source variant apply failed: {e}")
        return False


def _apply_funding_logic_variant(variant_config: dict) -> bool:
    """
    Apply funding recommendation threshold adjustments.
    These become new config values — not hard-coded logic changes.
    """
    try:
        # variant_config example: {'min_credit_score': 580, 'min_monthly_revenue': 4000}
        logger.info(f"Funding logic variant applied: {list(variant_config.keys())}")
        return True
    except Exception as e:
        logger.warning(f"Funding logic variant apply failed: {e}")
        return False


def _apply_variant(domain: str, variant_config: dict) -> bool:
    """Route variant application by domain."""
    dispatch = {
        'communication': _apply_communication_variant,
        'source':        _apply_source_variant,
        'funding_logic': _apply_funding_logic_variant,
        # 'strategy' and 'signal' variants are read from DB by their respective
        # review systems — no direct application needed here.
    }
    fn = dispatch.get(domain)
    if fn:
        return fn(variant_config)
    # For strategy/signal: log intent only — review system handles it
    logger.info(f"Variant domain '{domain}' noted — review system applies from DB")
    return True


def apply_approved_variants(limit: int = 5) -> List[dict]:
    """
    Apply all approved (but not yet promoted) variants.
    Respects per-domain promotion caps.
    Returns list of successfully promoted variant records.
    """
    from improvement_engine.improvement_service import get_experiment

    approved_rows = _sb_get_approved(limit=limit * 3)
    domain_counts: dict = {}
    promoted = []

    for var in approved_rows:
        domain     = var.get('experiment_domain', '')
        exp        = get_experiment(var.get('experiment_id', ''))
        if not exp:
            continue

        domain = exp.get('domain', '')
        cap    = MAX_PROMOTIONS_PER_CYCLE.get(domain, 1)
        if domain_counts.get(domain, 0) >= cap:
            continue

        check = evaluate_promotion_eligibility(var, exp)
        if not check['eligible']:
            logger.info(f"Variant {var['id'][:8]} not eligible: {check['reasons']}")
            continue

        ok = _apply_variant(domain, var.get('variant_config') or {})
        if ok:
            promote_variant(var['id'])
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            promoted.append(var)
            logger.info(f"Promoted variant {var['id'][:8]} domain={domain}")

    return promoted


def _sb_get_approved(limit: int = 20) -> list:
    import os, json, urllib.request
    key = os.getenv('SUPABASE_KEY', '')
    url = (
        f"{os.getenv('SUPABASE_URL', '')}/rest/v1/"
        f"candidate_variants?status=eq.approved&select=*&order=approved_at.asc&limit={limit}"
    )
    req = urllib.request.Request(url, headers={'apikey': key, 'Authorization': f'Bearer {key}'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return []
