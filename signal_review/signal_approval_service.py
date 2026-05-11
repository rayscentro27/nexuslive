"""
Signal Approval Service.

Takes a scored signal_candidates row and applies deterministic approval rules.
Writes an immutable signal_reviews audit row for every decision.
Updates signal_candidates.review_status → 'approved' | 'rejected'.

Approval rules (all must pass):
  1. score_total >= APPROVAL_SCORE_THRESHOLD (default 50, env: SIGNAL_APPROVAL_SCORE_THRESHOLD)
  2. risk_quality > 0  (stop loss must be present — no missing stop)
  3. confidence_label != 'low'  (configurable via SIGNAL_REQUIRE_MEDIUM_CONFIDENCE=true)
  4. rr_ratio >= MIN_RR_RATIO   (default 1.5, env: SIGNAL_MIN_RR_RATIO)
  5. No 'missing_stop_loss' in score notes

Usage:
  from signal_approval_service import approve_signal_candidate
  result = approve_signal_candidate(candidate_id, score_dict)
  # result = { 'approved': bool, 'reason': str }
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone

logger = logging.getLogger('SignalApprovalService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

APPROVAL_SCORE_THRESHOLD    = float(os.getenv('SIGNAL_APPROVAL_SCORE_THRESHOLD', '50.0'))
MIN_RR_RATIO                = float(os.getenv('SIGNAL_MIN_RR_RATIO', '1.5'))
REQUIRE_MEDIUM_CONFIDENCE   = os.getenv('SIGNAL_REQUIRE_MEDIUM_CONFIDENCE', 'true').lower() == 'true'


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_patch(table: str, row_id: str, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method='PATCH',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'return=minimal',
        }
    )
    with urllib.request.urlopen(req, timeout=10):
        pass


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _sb_insert(table: str, data: dict) -> dict:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body, method='POST',
        headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type':  'application/json',
            'Prefer':        'return=representation',
        }
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        rows = json.loads(r.read())
        return rows[0] if rows else {}


# ─── Approval logic ────────────────────────────────────────────────────────────

def _run_approval_rules(score: dict) -> tuple[bool, list[str]]:
    """
    Apply deterministic approval rules to a score dict.

    Returns:
        (approved: bool, rejection_reasons: list[str])
    """
    reasons = []

    score_total    = float(score.get('score_total', 0))
    risk_quality   = float(score.get('score_risk_quality', 0))
    confidence_lbl = score.get('confidence_label', 'low')
    rr_ratio       = float(score.get('rr_ratio', 0))
    notes          = score.get('notes', '') or ''

    # Rule 1: minimum total score
    if score_total < APPROVAL_SCORE_THRESHOLD:
        reasons.append(
            f"score_total {score_total} < threshold {APPROVAL_SCORE_THRESHOLD}"
        )

    # Rule 2: stop loss must be present
    if risk_quality == 0 or 'missing_stop_loss' in notes:
        reasons.append("missing stop loss — risk quality is zero")

    # Rule 3: confidence label must be medium or high
    if REQUIRE_MEDIUM_CONFIDENCE and confidence_lbl == 'low':
        reasons.append("confidence label is 'low' — below medium threshold")

    # Rule 4: minimum R:R ratio
    if rr_ratio > 0 and rr_ratio < MIN_RR_RATIO:
        reasons.append(
            f"rr_ratio {rr_ratio:.2f} < minimum {MIN_RR_RATIO}"
        )
    elif rr_ratio == 0:
        reasons.append("rr_ratio is zero (target or entry missing)")

    approved = len(reasons) == 0
    return approved, reasons


# ─── Public API ───────────────────────────────────────────────────────────────

def approve_signal_candidate(
    candidate_id: str,
    score: dict,
    tenant_id: str = None,
    reviewer_type: str = 'system',
) -> dict:
    """
    Apply approval rules to a scored signal_candidates row.

    Writes:
      - signal_reviews row (immutable audit record)
      - Updates signal_candidates.review_status → 'approved' | 'rejected'

    Args:
        candidate_id:  UUID of the signal_candidates row.
        score:         Score dict returned by signal_scoring_service.score_signal_candidate().
        tenant_id:     Optional tenant UUID.
        reviewer_type: 'system' | 'ai' | 'human' (default: 'system').

    Returns:
        { 'approved': bool, 'reason': str }
    """
    # Idempotency — return cached result if already reviewed
    try:
        existing = _sb_get(
            f"signal_reviews?candidate_id=eq.{candidate_id}&select=review_status,notes&limit=1"
        )
        if existing:
            cached_status = existing[0].get('review_status', 'rejected')
            logger.info(f"Review already exists for candidate {candidate_id} ({cached_status})")
            return {'approved': cached_status == 'approved', 'reason': existing[0].get('notes', '')}
    except Exception:
        pass  # Proceed if check fails

    approved, reasons = _run_approval_rules(score)

    new_status  = 'approved' if approved else 'rejected'
    reason_text = 'passed all approval rules' if approved else ' | '.join(reasons)

    review_row = {
        'candidate_id':        candidate_id,
        'signal_candidate_id': candidate_id,
        'review_status':       'approved' if approved else 'rejected',
        'review_action':       'approve' if approved else 'reject',
        'reviewer_type':       reviewer_type,
        'score_total':         score.get('score_total'),
        'confidence_label':    score.get('confidence_label'),
        'risk_label':          score.get('risk_label'),
        'notes':               reason_text,
    }
    if tenant_id:
        review_row['tenant_id'] = tenant_id

    try:
        _sb_insert('signal_reviews', review_row)
        _sb_patch('signal_candidates', candidate_id, {
            'review_status': new_status,
            'updated_at':    datetime.now(timezone.utc).isoformat(),
        })

        level = logging.INFO if approved else logging.WARNING
        logger.log(
            level,
            f"{'APPROVED' if approved else 'REJECTED'} candidate {candidate_id} "
            f"| score={score.get('score_total')} conf={score.get('confidence_label')} "
            f"R:R={score.get('rr_ratio')} | {reason_text}"
        )
    except Exception as e:
        logger.error(f"Approval write failed for candidate {candidate_id}: {e}")

    return {'approved': approved, 'reason': reason_text}


def expire_stale_candidates(max_age_hours: int = 24, tenant_id: str = None):
    """
    Mark signal_candidates that are still 'new' or 'scored' after max_age_hours as 'expired'.
    Writes a signal_reviews audit row for each.

    Called by the poller or a scheduler — not by the main ingest path.
    """
    from datetime import timedelta
    import urllib.parse

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).strftime('%Y-%m-%dT%H:%M:%SZ')
    params = {
        'review_status': 'in.(new,scoring,scored)',
        'created_at':    f'lt.{cutoff}',
        'select':        'id,symbol,confidence',
    }
    if tenant_id:
        params['tenant_id'] = f'eq.{tenant_id}'

    try:
        query = urllib.parse.urlencode(params, safe='(),.*')
        url = f"{SUPABASE_URL}/rest/v1/signal_candidates?{query}"
        req = urllib.request.Request(url, headers={
            'apikey':        SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            stale = json.loads(r.read())
    except Exception as e:
        logger.error(f"expire_stale_candidates fetch failed: {e}")
        return

    for row in stale:
        cid = row['id']
        try:
            _sb_insert('signal_reviews', {
                'signal_candidate_id': cid,
                'review_action':       'expire',
                'reviewer_type':       'system',
                'notes':               f"auto-expired after {max_age_hours}h without scoring/approval",
            })
            _sb_patch('signal_candidates', cid, {
                'review_status': 'expired',
                'updated_at':    datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"Expired stale candidate {cid} ({row.get('symbol')})")
        except Exception as e:
            logger.error(f"Failed to expire candidate {cid}: {e}")
