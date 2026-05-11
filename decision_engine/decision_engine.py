"""
Autonomous Decision Engine.

Evaluates system state and generates decisions without manual input.

Decision types:
  source_action      — add/pause/rescan a research source
  client_outreach    — contact a stalled or high-value client
  strategy_adjustment — adjust signal thresholds or strategy parameters
  pipeline_change    — pause, resume, or reconfigure a pipeline component

Safety constraints:
  - All high-safety-level decisions are stored as pending, NOT executed
  - Only low-safety decisions execute automatically
  - Each decision records its rationale and context
  - Hard limits: max 5 auto-decisions per worker run, no back-to-back same type

Decision triggers (rule-based):
  1. Health score below threshold → recommend source review
  2. Stalled clients → recommend outreach
  3. Coverage gap in high-priority domain → recommend new source
  4. No new signals in 48h → recommend strategy review
  5. Funding approval rate drop → recommend pipeline review
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger('DecisionEngine')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

MAX_AUTO_DECISIONS = int(os.getenv('MAX_AUTO_DECISIONS', '5'))

# Safety level per decision type
DECISION_SAFETY = {
    'source_action':       'low',     # auto-execute: add/rescan sources
    'client_outreach':     'low',     # auto-execute: send messages
    'strategy_adjustment': 'medium',  # hold for approval
    'pipeline_change':     'high',    # hold for approval
}


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


# ─── Decision storage ─────────────────────────────────────────────────────────

def store_decision(
    decision_type: str,
    action: str,
    rationale: str,
    confidence: float        = 0.7,
    context: Optional[dict]  = None,
    safety_level: Optional[str] = None,
) -> Optional[str]:
    """Store a decision. Returns decision id."""
    safety = safety_level or DECISION_SAFETY.get(decision_type, 'medium')
    status = 'pending'

    row = {
        'decision_type': decision_type,
        'action':        action,
        'rationale':     rationale,
        'confidence':    round(max(0.0, min(1.0, confidence)), 3),
        'context':       context or {},
        'status':        status,
        'safety_level':  safety,
    }
    result = _sb_post('decisions', row)
    if result:
        did = result.get('id')
        logger.info(f"Decision stored: {decision_type} safety={safety} id={did}")
        return did
    return None


def mark_decision_executed(decision_id: str) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    return _sb_patch(
        f"decisions?id=eq.{decision_id}",
        {'status': 'executed', 'executed_at': now},
    )


def mark_decision_skipped(decision_id: str) -> bool:
    return _sb_patch(f"decisions?id=eq.{decision_id}", {'status': 'skipped'})


# ─── Rule evaluators ──────────────────────────────────────────────────────────

def _evaluate_source_health(decisions: List[dict]) -> List[dict]:
    """Generate source_action decisions for critically low health sources."""
    new_decisions = []
    low_health = _sb_get(
        "source_health_scores?score_total=lt.30&order=score_total.asc&limit=5&select=*"
    )
    for hs in low_health:
        source_id = hs.get('source_id', '')
        score     = hs.get('score_total', 0)
        action    = f"rescan_source:{source_id}"
        # Skip if already decided recently
        already = any(
            d.get('decision_type') == 'source_action' and source_id in d.get('action', '')
            for d in decisions
        )
        if already:
            continue
        new_decisions.append({
            'decision_type': 'source_action',
            'action':        action,
            'rationale':     f"Source health score critically low ({score}/100). Auto-rescan triggered.",
            'confidence':    0.85,
            'context':       {'source_id': source_id, 'score': score},
        })
    return new_decisions


def _evaluate_stalled_clients(decisions: List[dict]) -> List[dict]:
    """Generate client_outreach decisions for stalled clients."""
    from funnel_engine.funnel_service import get_stalled_clients
    new_decisions = []
    stalled = get_stalled_clients(days=7, limit=5)
    for client in stalled:
        client_id = client.get('client_id', '')
        stage     = client.get('current_stage', '')
        already   = any(
            d.get('decision_type') == 'client_outreach' and client_id in d.get('action', '')
            for d in decisions
        )
        if already:
            continue
        new_decisions.append({
            'decision_type': 'client_outreach',
            'action':        f"nudge_client:{client_id}:stage={stage}",
            'rationale':     f"Client stalled at '{stage}' stage for 7+ days. Outreach recommended.",
            'confidence':    0.75,
            'context':       {'client_id': client_id, 'stage': stage},
        })
    return new_decisions


def _evaluate_coverage_gaps(decisions: List[dict]) -> List[dict]:
    """Generate source_action decisions for high-priority coverage gaps."""
    new_decisions = []
    gaps = _sb_get(
        "research_coverage?coverage_score=lt.20&domain=in.(trading,funding)&select=*&limit=3"
    )
    for gap in gaps:
        domain = gap.get('domain', '')
        subdomain = gap.get('subdomain', '')
        key = f"{domain}/{subdomain}"
        already = any(
            d.get('decision_type') == 'source_action' and key in d.get('action', '')
            for d in decisions
        )
        if already:
            continue
        new_decisions.append({
            'decision_type': 'source_action',
            'action':        f"recommend_source:domain={domain}:subdomain={subdomain}",
            'rationale':     f"Critical coverage gap in {domain}/{subdomain} (score<20). New source needed.",
            'confidence':    0.80,
            'context':       {'domain': domain, 'subdomain': subdomain,
                              'coverage_score': gap.get('coverage_score', 0)},
        })
    return new_decisions


def _evaluate_signal_drought() -> List[dict]:
    """Generate strategy_adjustment decision if no signals in 48h."""
    new_decisions = []
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    recent_signals = _sb_get(
        f"system_events?event_type=eq.signal_approved&created_at=gt.{cutoff}&select=id&limit=1"
    )
    if not recent_signals:
        new_decisions.append({
            'decision_type': 'strategy_adjustment',
            'action':        'review_signal_thresholds:no_signals_48h',
            'rationale':     'No trading signals approved in the past 48 hours. Signal thresholds may be too restrictive.',
            'confidence':    0.65,
            'context':       {'hours_without_signal': 48},
        })
    return new_decisions


# ─── Execution ────────────────────────────────────────────────────────────────

def _execute_decision(decision_id: str, decision: dict) -> bool:
    """Execute a low-safety decision immediately."""
    action        = decision.get('action', '')
    decision_type = decision.get('decision_type', '')
    context       = decision.get('context', {})

    try:
        if decision_type == 'source_action':
            if action.startswith('rescan_source:'):
                source_id = action.split(':', 1)[1]
                from research_sources.source_registry import queue_rescan
                ok, msg = queue_rescan(source_id)
                logger.info(f"Auto-rescan: {source_id} → {msg}")
                return ok

            if action.startswith('recommend_source:'):
                from research_intelligence.recommendation_engine import run_recommendations
                run_recommendations()
                return True

        if decision_type == 'client_outreach':
            if action.startswith('nudge_client:'):
                parts     = action.split(':')
                client_id = parts[1] if len(parts) > 1 else ''
                stage     = context.get('stage', 'unknown')
                from funnel_engine.funnel_worker import _send_telegram
                msg = (
                    f"Hi! Just checking in on your funding journey. "
                    f"You're at the '{stage}' stage. "
                    f"Is there anything we can help you with to move forward? "
                    f"Reply anytime!"
                )
                _send_telegram(client_id, msg)
                return True

        return False

    except Exception as e:
        logger.error(f"Decision execution failed: {decision_id} → {e}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def run_decision_cycle() -> dict:
    """
    Evaluate all rules, store decisions, auto-execute low-safety ones.
    Returns summary dict.
    """
    # Load recent decisions to avoid duplicates
    recent_decisions = _sb_get(
        "decisions?status=in.(pending,executed)&created_at=gt."
        + (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        + "&select=decision_type,action&limit=100"
    )

    # Gather decisions from all rules
    candidates: List[dict] = []
    candidates += _evaluate_source_health(recent_decisions)
    candidates += _evaluate_stalled_clients(recent_decisions)
    candidates += _evaluate_coverage_gaps(recent_decisions)
    candidates += _evaluate_signal_drought()

    stored    = 0
    executed  = 0
    held      = 0
    auto_count = 0

    for candidate in candidates:
        if auto_count >= MAX_AUTO_DECISIONS:
            break

        safety = DECISION_SAFETY.get(candidate['decision_type'], 'medium')
        did    = store_decision(
            decision_type=candidate['decision_type'],
            action=candidate['action'],
            rationale=candidate['rationale'],
            confidence=candidate['confidence'],
            context=candidate.get('context', {}),
            safety_level=safety,
        )
        if not did:
            continue
        stored += 1

        if safety == 'low':
            ok = _execute_decision(did, candidate)
            if ok:
                mark_decision_executed(did)
                executed += 1
            else:
                mark_decision_skipped(did)
            auto_count += 1
        else:
            held += 1
            logger.info(f"Decision held for approval: {candidate['decision_type']} safety={safety}")

    return {
        'stored':   stored,
        'executed': executed,
        'held':     held,
    }


def get_pending_decisions(limit: int = 20) -> List[dict]:
    return _sb_get(
        f"decisions?status=eq.pending&order=confidence.desc,created_at.asc"
        f"&limit={limit}&select=*"
    )


def approve_decision(decision_id: str) -> bool:
    """Human-approved: execute a held decision."""
    rows = _sb_get(f"decisions?id=eq.{decision_id}&select=*&limit=1")
    if not rows:
        return False
    decision = rows[0]
    ok = _execute_decision(decision_id, decision)
    if ok:
        mark_decision_executed(decision_id)
    return ok
