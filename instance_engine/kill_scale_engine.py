"""
Kill / Scale Decision Engine.

Analyzes each active/testing instance and generates kill or scale decisions
stored in the `instance_decisions` table.

Decision types:
  scale — instance is profitable, replicate it
  hold  — instance needs more time / minor optimization
  kill  — instance is underperforming past grace period

Decision thresholds:
  SCALE_REVENUE_THRESHOLD  — monthly revenue to trigger scale recommendation
  KILL_REVENUE_THRESHOLD   — monthly revenue below which kill is considered
  KILL_AGE_DAYS            — minimum age before kill decisions are made
  SCALE_AGE_DAYS           — minimum age before scale is considered

All decisions are stored as 'pending' — humans or the approval engine execute them.

Usage:
    from instance_engine.kill_scale_engine import (
        run_kill_scale_analysis, approve_decision, get_pending_decisions,
    )
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional, List

logger = logging.getLogger('KillScaleEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Thresholds
SCALE_REVENUE_THRESHOLD = 3000.0   # $3k/mo → scale signal
KILL_REVENUE_THRESHOLD  = 200.0    # <$200/mo after grace → kill signal
KILL_AGE_DAYS           = 21       # Must be 21+ days old to kill
SCALE_AGE_DAYS          = 14       # Must be 14+ days old to scale
HOLD_REVENUE_THRESHOLD  = 500.0    # Between kill and scale = hold

# Confidence levels
CONFIDENCE_SCALE = 0.85
CONFIDENCE_KILL  = 0.80
CONFIDENCE_HOLD  = 0.70


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


# ─── Decision logic ───────────────────────────────────────────────────────────

def _age_days(created_at: str) -> int:
    try:
        created = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        return (datetime.now(timezone.utc) - created).days
    except Exception:
        return 0


def _pending_decision_exists(instance_id: str, decision: str) -> bool:
    rows = _sb_get(
        f"instance_decisions?instance_id=eq.{instance_id}"
        f"&decision=eq.{decision}&status=eq.pending&select=id&limit=1"
    )
    return len(rows) > 0


def _store_decision(
    instance_id: str,
    decision: str,
    reason: str,
    confidence: float,
) -> Optional[dict]:
    """Store a pending decision. Skip if identical pending decision already exists."""
    if _pending_decision_exists(instance_id, decision):
        return None

    row = {
        'instance_id': instance_id,
        'decision':    decision,
        'reason':      reason,
        'confidence':  confidence,
        'status':      'pending',
    }
    result = _sb_post('instance_decisions', row)
    if result:
        logger.info(f"Decision stored: {decision} for {instance_id[:8]}... confidence={confidence}")
    return result


def _evaluate_instance(
    instance: dict,
    monthly_revenue: float,
) -> Optional[dict]:
    """
    Evaluate a single instance and return a decision dict or None.
    """
    iid      = instance['id']
    niche    = instance.get('niche', '?')
    status   = instance.get('status', 'testing')
    age      = _age_days(instance.get('created_at', ''))
    name     = instance.get('display_name') or niche

    # Too new — no decision yet
    if age < KILL_AGE_DAYS and monthly_revenue < KILL_REVENUE_THRESHOLD:
        return None

    # SCALE: strong revenue + mature enough
    if monthly_revenue >= SCALE_REVENUE_THRESHOLD and age >= SCALE_AGE_DAYS:
        return _store_decision(
            instance_id=iid,
            decision='scale',
            reason=(
                f"Instance '{name}' generating ${monthly_revenue:,.0f}/mo "
                f"after {age} days — ready to replicate."
            ),
            confidence=CONFIDENCE_SCALE,
        )

    # KILL: too little revenue + past grace period
    if monthly_revenue < KILL_REVENUE_THRESHOLD and age >= KILL_AGE_DAYS:
        return _store_decision(
            instance_id=iid,
            decision='kill',
            reason=(
                f"Instance '{name}' only ${monthly_revenue:,.0f}/mo "
                f"after {age} days — below kill threshold ${KILL_REVENUE_THRESHOLD:,.0f}."
            ),
            confidence=CONFIDENCE_KILL,
        )

    # HOLD: mid-range revenue or not old enough to kill
    if KILL_REVENUE_THRESHOLD <= monthly_revenue < SCALE_REVENUE_THRESHOLD:
        if age >= SCALE_AGE_DAYS:
            return _store_decision(
                instance_id=iid,
                decision='hold',
                reason=(
                    f"Instance '{name}' at ${monthly_revenue:,.0f}/mo — "
                    f"needs optimization to reach scale threshold ${SCALE_REVENUE_THRESHOLD:,.0f}."
                ),
                confidence=CONFIDENCE_HOLD,
            )

    return None


def run_kill_scale_analysis(limit: int = 50) -> List[dict]:
    """
    Analyze all active/testing instances and generate kill/scale/hold decisions.
    Returns list of new decision records created.
    """
    from revenue_engine.revenue_service import get_monthly_total

    instances = _sb_get(
        f"nexus_instances?status=in.(active,testing)&select=*"
        f"&order=created_at.asc&limit={limit}"
    )

    period   = datetime.now(timezone.utc).strftime('%Y-%m')
    decisions = []

    for instance in instances:
        monthly = get_monthly_total(
            instance_id=instance['id'],
            period=period,
        )
        decision = _evaluate_instance(instance, monthly)
        if decision:
            decisions.append(decision)

    logger.info(f"Kill/scale analysis: {len(instances)} instances → {len(decisions)} decisions")
    return decisions


# ─── Decision execution ───────────────────────────────────────────────────────

def approve_decision(decision_id: str) -> bool:
    """
    Approve and execute a pending decision.
    Scale → clones the instance.
    Kill  → sets instance status to killed.
    Hold  → marks decision executed with no status change.
    """
    rows = _sb_get(
        f"instance_decisions?id=eq.{decision_id}&select=*&limit=1"
    )
    if not rows:
        return False

    dec        = rows[0]
    instance_id = dec.get('instance_id')
    decision    = dec.get('decision')
    now         = datetime.now(timezone.utc).isoformat()

    if decision == 'scale':
        from instance_engine.replication_service import clone_instance
        from funnel_engine.funnel_deployer import deploy_all_funnels_for_instance

        clone = clone_instance(source_id=instance_id)
        if clone:
            deploy_all_funnels_for_instance(
                instance_id=clone['id'],
                niche=clone.get('niche'),
            )
            logger.info(f"Scale executed: cloned {instance_id[:8]} → {clone['id'][:8]}")
        else:
            logger.warning(f"Scale failed: could not clone {instance_id}")

    elif decision == 'kill':
        from instance_engine.instance_registry import update_status
        update_status(instance_id, 'killed')
        logger.info(f"Kill executed: {instance_id[:8]} → killed")

    elif decision == 'hold':
        logger.info(f"Hold acknowledged: {instance_id[:8]}")

    # Mark decision executed
    _sb_patch(
        f"instance_decisions?id=eq.{decision_id}",
        {'status': 'executed', 'executed_at': now},
    )
    return True


def override_decision(decision_id: str) -> bool:
    """Human override — mark as overridden without executing."""
    return _sb_patch(
        f"instance_decisions?id=eq.{decision_id}",
        {'status': 'overridden'},
    )


def get_pending_decisions(limit: int = 20) -> List[dict]:
    return _sb_get(
        f"instance_decisions?status=eq.pending&select=*"
        f"&order=created_at.desc&limit={limit}"
    )


def get_decisions_for_instance(instance_id: str) -> List[dict]:
    return _sb_get(
        f"instance_decisions?instance_id=eq.{instance_id}"
        f"&select=*&order=created_at.desc"
    )
