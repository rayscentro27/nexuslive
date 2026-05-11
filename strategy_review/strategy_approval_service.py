"""
Strategy Approval Service.

Takes a scored strategy_candidates row and applies deterministic approval rules.
Writes an immutable strategy_reviews audit row for every decision.
Updates strategy_candidates.review_status → 'approved' | 'rejected'.

Approval rules (all must pass):
  1. score_total >= APPROVAL_SCORE_THRESHOLD (default 50)
  2. confidence_label != 'low'
  3. title is present and >= 5 characters
  4. raw_content length >= 50 characters

Idempotent: returns cached decision if a strategy_reviews row already exists
for this candidate_id.

Usage:
  from strategy_approval_service import approve_strategy_candidate
  result = approve_strategy_candidate(candidate_id, score_dict)
  # result = { 'approved': bool, 'reason': str }
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('StrategyApprovalService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

APPROVAL_SCORE_THRESHOLD = float(os.getenv('STRATEGY_APPROVAL_SCORE_THRESHOLD', '50.0'))


# ─── Supabase helpers ──────────────────────────────────────────────────────────

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


# ─── Approval logic ────────────────────────────────────────────────────────────

def _run_approval_rules(score: dict, candidate: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    score_total      = float(score.get('score_total', 0))
    confidence_label = score.get('confidence_label', 'low')
    title            = (candidate.get('title') or '').strip()
    content          = (candidate.get('raw_content') or '').strip()

    if score_total < APPROVAL_SCORE_THRESHOLD:
        reasons.append(
            f"score_total {score_total} < threshold {APPROVAL_SCORE_THRESHOLD}"
        )

    if confidence_label == 'low':
        reasons.append("confidence label is 'low' — below minimum threshold")

    if len(title) < 5:
        reasons.append("title missing or too short (< 5 chars)")

    if len(content) < 50:
        reasons.append("content too short (< 50 chars) — insufficient for educational use")

    return len(reasons) == 0, reasons


# ─── Public API ───────────────────────────────────────────────────────────────

def approve_strategy_candidate(
    candidate_id: str,
    score: dict,
    candidate: dict,
    reviewer_type: str = 'system',
) -> dict:
    """
    Apply approval rules and write the result to strategy_reviews.
    Idempotent — returns cached decision if review already exists.

    Args:
        candidate_id:  UUID of the strategy_candidates row.
        score:         Score dict from strategy_scoring_service.
        candidate:     The strategy_candidates dict (for title/content checks).
        reviewer_type: 'system' | 'ai' | 'human'

    Returns:
        { 'approved': bool, 'reason': str }
    """
    # Idempotency check
    try:
        existing = _sb_get(
            f"strategy_reviews?candidate_id=eq.{candidate_id}&select=review_action,notes&limit=1"
        )
        if existing:
            cached_action = existing[0].get('review_action', 'reject')
            logger.info(f"Cached review found for candidate {candidate_id} ({cached_action})")
            return {
                'approved': cached_action == 'approve',
                'reason':   existing[0].get('notes', ''),
            }
    except Exception:
        pass

    approved, reasons = _run_approval_rules(score, candidate)
    new_status  = 'approved' if approved else 'rejected'
    reason_text = 'passed all approval rules' if approved else ' | '.join(reasons)

    review_row = {
        'candidate_id':   candidate_id,
        'score_id':       score.get('id'),
        'review_action':  'approve' if approved else 'reject',
        'review_status':  new_status,
        'reviewer_type':  reviewer_type,
        'score_total':    score.get('score_total'),
        'confidence_label': score.get('confidence_label'),
        'difficulty_level': score.get('difficulty_level'),
        'notes':          reason_text,
    }

    try:
        _sb_insert('strategy_reviews', review_row)
        _sb_patch('strategy_candidates', candidate_id, {
            'review_status': new_status,
            'updated_at':    datetime.now(timezone.utc).isoformat(),
        })
        level = 20 if approved else 30   # logging.INFO vs logging.WARNING
        logger.log(
            level,
            f"{'APPROVED' if approved else 'REJECTED'} strategy candidate {candidate_id} "
            f"| score={score.get('score_total')} conf={score.get('confidence_label')} "
            f"diff={score.get('difficulty_level')} | {reason_text}"
        )
    except Exception as e:
        logger.error(f"Approval write failed for candidate {candidate_id}: {e}")

    return {'approved': approved, 'reason': reason_text}


def expire_stale_strategy_candidates(max_age_hours: int = 168) -> None:
    """
    Mark strategy_candidates that are still 'new'/'scored' after max_age_hours
    as 'expired'. Writes a strategy_reviews audit row for each.
    Default 168h (7 days) — strategies are slower-moving than signals.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    ).isoformat()

    try:
        stale = _sb_get(
            f"strategy_candidates"
            f"?review_status=in.(new,scoring,scored)"
            f"&created_at=lt.{cutoff}"
            f"&select=id,title"
        )
    except Exception as e:
        logger.error(f"expire_stale_strategy_candidates fetch failed: {e}")
        return

    for row in stale:
        cid = row['id']
        try:
            _sb_insert('strategy_reviews', {
                'candidate_id':  cid,
                'review_action': 'expire',
                'review_status': 'expired',
                'reviewer_type': 'system',
                'notes':         f"auto-expired after {max_age_hours}h without approval",
            })
            _sb_patch('strategy_candidates', cid, {
                'review_status': 'expired',
                'updated_at':    datetime.now(timezone.utc).isoformat(),
            })
            logger.info(f"Expired stale strategy candidate {cid} ({row.get('title', '')[:60]})")
        except Exception as e:
            logger.error(f"Failed to expire strategy candidate {cid}: {e}")
