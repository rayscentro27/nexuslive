"""
Signal Scoring Service — deterministic first-pass scorer.

Scores a signal_candidates row across four dimensions (each max 25, total max 100):

  1. score_setup_quality  — technical merit: symbol, direction, timeframe, setup_type, entry
  2. score_risk_quality   — stop/target completeness and R:R ratio
  3. score_confirmation   — AI reviewer confidence and strategy match
  4. score_clarity        — data completeness and zone quality

Confidence label  (derived from score_total):
  >= 75 → high
  >= 50 → medium
  <  50 → low

Risk label (derived from R:R and stop completeness):
  R:R >= 2.5 and stop present → low
  R:R >= 1.5                  → medium
  otherwise                   → high

Writes one row to signal_scores and updates signal_candidates.review_status → 'scored'.

Usage (standalone):
  from signal_scoring_service import score_signal_candidate
  score = score_signal_candidate(candidate_id, signal_row, ai_review_dict)
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('SignalScoringService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

SCORING_VERSION = '1.0'

# Approval threshold used by signal_approval_service — exported so it's one place
APPROVAL_SCORE_THRESHOLD = float(os.getenv('SIGNAL_APPROVAL_SCORE_THRESHOLD', '50.0'))


# ─── Supabase helpers ──────────────────────────────────────────────────────────

def _sb_get_list(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


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


# ─── Scoring dimensions ────────────────────────────────────────────────────────

def _score_setup_quality(candidate: dict) -> tuple[float, dict]:
    """
    Max 25 pts. Checks 5 key technical fields: 5 pts each.
    Fields: symbol, direction, setup_type, timeframe, entry_zone price.
    """
    breakdown = {}
    score = 0.0

    # symbol
    if candidate.get('symbol'):
        score += 5
        breakdown['symbol'] = 5
    else:
        breakdown['symbol'] = 0

    # direction
    direction = (candidate.get('direction') or '').lower()
    if direction in ('long', 'short', 'buy', 'sell'):
        score += 5
        breakdown['direction'] = 5
    else:
        breakdown['direction'] = 0

    # setup_type
    known_setup_types = {
        'breakout', 'reversal', 'trend_continuation', 'range',
        'pullback', 'momentum', 'support_bounce', 'resistance_reject',
        'fakeout', 'inside_bar', 'engulfing', 'pin_bar',
    }
    setup_type = (candidate.get('setup_type') or '').lower()
    if setup_type in known_setup_types:
        score += 5
        breakdown['setup_type'] = 5
    elif setup_type:
        score += 3  # partial: present but unrecognised
        breakdown['setup_type'] = 3
    else:
        breakdown['setup_type'] = 0

    # timeframe
    known_timeframes = {'1m', '3m', '5m', '15m', '30m', '1h', '4h', '1d', '1w', '1mo',
                        '1', '3', '5', '15', '30', '60', '240', 'd', 'w'}
    timeframe = str(candidate.get('timeframe') or '').lower()
    if timeframe in known_timeframes:
        score += 5
        breakdown['timeframe'] = 5
    elif timeframe:
        score += 2
        breakdown['timeframe'] = 2
    else:
        breakdown['timeframe'] = 0

    # entry_zone — expects {"price": numeric}
    entry_zone = candidate.get('entry_zone') or {}
    if isinstance(entry_zone, str):
        try:
            entry_zone = json.loads(entry_zone)
        except Exception:
            entry_zone = {}
    entry_price = entry_zone.get('price', 0) if isinstance(entry_zone, dict) else 0
    if entry_price and float(entry_price) > 0:
        score += 5
        breakdown['entry_zone'] = 5
    else:
        breakdown['entry_zone'] = 0

    return min(score, 25.0), breakdown


def _score_risk_quality(candidate: dict) -> tuple[float, dict, float]:
    """
    Max 25 pts. Derived from R:R ratio, stop completeness, and target presence.
    Also returns the calculated rr_ratio for the score record.
    """
    breakdown = {}
    score = 0.0
    rr_ratio = 0.0

    entry_zone  = candidate.get('entry_zone') or {}
    stop_zone   = candidate.get('stop_zone') or {}
    target_zone = candidate.get('target_zone') or {}

    if isinstance(entry_zone, str):
        try: entry_zone = json.loads(entry_zone)
        except Exception: entry_zone = {}
    if isinstance(stop_zone, str):
        try: stop_zone = json.loads(stop_zone)
        except Exception: stop_zone = {}
    if isinstance(target_zone, str):
        try: target_zone = json.loads(target_zone)
        except Exception: target_zone = {}

    entry  = float(entry_zone.get('price', 0) if isinstance(entry_zone, dict) else 0)
    stop   = float(stop_zone.get('price', 0)  if isinstance(stop_zone, dict) else 0)
    target = float(target_zone.get('price', 0) if isinstance(target_zone, dict) else 0)

    # Fallback: check raw_payload for entry_price, stop_loss, take_profit
    raw = candidate.get('raw_payload') or {}
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except Exception: raw = {}
    if not entry:  entry  = float(raw.get('entry_price', 0) or 0)
    if not stop:   stop   = float(raw.get('stop_loss', 0)   or 0)
    if not target: target = float(raw.get('take_profit', 0) or 0)

    # Missing stop → hard 0 on risk quality, also flagged in notes
    if not stop or stop == 0:
        breakdown['stop_present'] = 0
        breakdown['rr_ratio']     = 0
        return 0.0, breakdown, 0.0

    breakdown['stop_present'] = 5
    score += 5

    # Calculate R:R
    if entry and target:
        risk   = abs(entry - stop)
        reward = abs(target - entry)
        rr_ratio = reward / risk if risk > 0 else 0.0
    else:
        rr_ratio = 0.0

    # Score R:R
    if rr_ratio >= 3.0:
        rr_score = 20
    elif rr_ratio >= 2.5:
        rr_score = 17
    elif rr_ratio >= 2.0:
        rr_score = 14
    elif rr_ratio >= 1.5:
        rr_score = 10
    elif rr_ratio >= 1.0:
        rr_score = 6
    elif rr_ratio > 0:
        rr_score = 2
    else:
        rr_score = 0

    score += rr_score
    breakdown['rr_ratio'] = round(rr_ratio, 3)
    breakdown['rr_score'] = rr_score

    return min(score, 25.0), breakdown, round(rr_ratio, 3)


def _score_confirmation(ai_review: dict) -> tuple[float, dict]:
    """
    Max 25 pts. Based on AI reviewer output stored in ai_review dict.
    ai_review should contain: confidence (0.0–1.0), strategy_match, ai_available.
    """
    breakdown = {}
    score = 0.0

    if not ai_review:
        breakdown['ai_available'] = 0
        return 0.0, breakdown

    ai_available = ai_review.get('ai_available', False)
    confidence   = float(ai_review.get('confidence', 0) or 0)
    strategy     = ai_review.get('strategy_match')

    # Base score from confidence
    if confidence >= 0.85:
        conf_score = 18
    elif confidence >= 0.70:
        conf_score = 15
    elif confidence >= 0.55:
        conf_score = 12
    elif confidence >= 0.40:
        conf_score = 8
    elif confidence >= 0.20:
        conf_score = 5
    else:
        conf_score = 2

    score += conf_score
    breakdown['confidence_score'] = conf_score
    breakdown['confidence_value'] = round(confidence, 3)

    # Bonus: real AI (not heuristic fallback) +4
    if ai_available:
        score += 4
        breakdown['ai_bonus'] = 4
    else:
        breakdown['ai_bonus'] = 0

    # Bonus: strategy match identified +3
    if strategy:
        score += 3
        breakdown['strategy_match_bonus'] = 3
    else:
        breakdown['strategy_match_bonus'] = 0

    return min(score, 25.0), breakdown


def _score_clarity(candidate: dict) -> tuple[float, dict]:
    """
    Max 25 pts. Completeness: all three zones, market_type, source traceability, timeframe specificity.
    """
    breakdown = {}
    score = 0.0

    def _has_price(zone_val):
        if not zone_val:
            return False
        if isinstance(zone_val, str):
            try: zone_val = json.loads(zone_val)
            except Exception: return False
        return isinstance(zone_val, dict) and float(zone_val.get('price', 0) or 0) > 0

    # Both stop and target present with numeric prices: 10 pts
    stop_ok   = _has_price(candidate.get('stop_zone'))
    target_ok = _has_price(candidate.get('target_zone'))

    # Fallback check raw_payload
    raw = candidate.get('raw_payload') or {}
    if isinstance(raw, str):
        try: raw = json.loads(raw)
        except Exception: raw = {}
    if not stop_ok:   stop_ok   = float(raw.get('stop_loss',   0) or 0) > 0
    if not target_ok: target_ok = float(raw.get('take_profit', 0) or 0) > 0

    if stop_ok and target_ok:
        score += 10
        breakdown['all_zones'] = 10
    elif stop_ok or target_ok:
        score += 5
        breakdown['all_zones'] = 5
    else:
        breakdown['all_zones'] = 0

    # market_type classified: 5 pts
    known_markets = {'forex', 'crypto', 'equity', 'futures', 'options', 'commodities', 'indices'}
    market_type = (candidate.get('market_type') or '').lower()
    if market_type in known_markets:
        score += 5
        breakdown['market_type'] = 5
    elif market_type:
        score += 2
        breakdown['market_type'] = 2
    else:
        breakdown['market_type'] = 0

    # source_signal_id present (traceable): 5 pts
    if candidate.get('source_signal_id'):
        score += 5
        breakdown['traceable'] = 5
    else:
        breakdown['traceable'] = 0

    # Timeframe specific (not 'unknown', not empty): 5 pts
    tf = str(candidate.get('timeframe') or '').lower().strip()
    if tf and tf not in ('unknown', 'n/a', 'none', '?'):
        score += 5
        breakdown['timeframe_specific'] = 5
    else:
        breakdown['timeframe_specific'] = 0

    return min(score, 25.0), breakdown


# ─── Labels ───────────────────────────────────────────────────────────────────

def _confidence_label(score_total: float) -> str:
    if score_total >= 75:
        return 'high'
    if score_total >= 50:
        return 'medium'
    return 'low'


def _risk_label(rr_ratio: float, has_stop: bool) -> str:
    if not has_stop:
        return 'high'
    if rr_ratio >= 2.5:
        return 'low'
    if rr_ratio >= 1.5:
        return 'medium'
    return 'high'


# ─── Public API ───────────────────────────────────────────────────────────────

def compute_score(candidate: dict, ai_review: dict) -> dict:
    """
    Pure scoring function — no Supabase I/O.
    Returns the full score dict.
    """
    notes = []

    sq, sq_bd           = _score_setup_quality(candidate)
    rq, rq_bd, rr_ratio = _score_risk_quality(candidate)
    sc, sc_bd           = _score_confirmation(ai_review)
    cl, cl_bd           = _score_clarity(candidate)

    # Reject signals missing a stop loss — hard gate
    if rr_ratio == 0.0 and rq == 0.0:
        notes.append('missing_stop_loss')

    total = sq + rq + sc + cl
    conf_label = _confidence_label(total)
    risk_lbl   = _risk_label(rr_ratio, 'missing_stop_loss' not in notes)

    if total < APPROVAL_SCORE_THRESHOLD:
        notes.append(f'below_approval_threshold_{APPROVAL_SCORE_THRESHOLD}')

    breakdown = {
        'setup_quality':  sq_bd,
        'risk_quality':   rq_bd,
        'confirmation':   sc_bd,
        'clarity':        cl_bd,
    }

    return {
        'score_total':         round(total, 2),
        'score_setup_quality': round(sq, 2),
        'score_risk_quality':  round(rq, 2),
        'score_confirmation':  round(sc, 2),
        'score_clarity':       round(cl, 2),
        'confidence_label':    conf_label,
        'risk_label':          risk_lbl,
        'rr_ratio':            rr_ratio,
        'scoring_version':     SCORING_VERSION,
        'score_breakdown':     breakdown,
        'notes':               ' | '.join(notes) if notes else None,
    }


def score_signal_candidate(
    candidate_id: str,
    candidate: dict,
    ai_review: dict,
    tenant_id: str = None,
) -> Optional[dict]:
    """
    Score a signal_candidate row, write signal_scores, update candidate status.

    Args:
        candidate_id: UUID of the signal_candidates row.
        candidate:    The signal_candidates dict (already fetched by caller).
        ai_review:    The AI review dict from signal_reviewer.review_signal().
        tenant_id:    Optional tenant UUID.

    Returns:
        The score dict on success, None on failure.
    """
    logger.info(f"Scoring candidate {candidate_id}")

    try:
        # Idempotency — return existing score if already scored
        existing = _sb_get_list(
            f"signal_scores?candidate_id=eq.{candidate_id}&select=*&order=created_at.desc&limit=1"
        )
        if existing:
            row = existing[0]
            logger.info(f"Score already exists for candidate {candidate_id} — returning cached")
            return {
                'score_total':         float(row.get('score_total', 0)),
                'score_setup_quality': float(row.get('score_setup_quality', 0)),
                'score_risk_quality':  float(row.get('score_risk_quality', 0)),
                'score_confirmation':  float(row.get('score_confirmation', 0)),
                'score_clarity':       float(row.get('score_clarity', 0)),
                'confidence_label':    row.get('confidence_label'),
                'risk_label':          row.get('risk_label'),
                'rr_ratio':            float(row.get('rr_ratio', 0)),
                'scoring_version':     row.get('scoring_version', SCORING_VERSION),
                'score_breakdown':     row.get('score_breakdown'),
                'notes':               row.get('notes'),
            }

        score = compute_score(candidate, ai_review)

        score_row = {
            'candidate_id':        candidate_id,
            'signal_candidate_id': candidate_id,
            'score_total':         score['score_total'],
            'score_setup_quality': score['score_setup_quality'],
            'score_risk_quality':  score['score_risk_quality'],
            'score_confirmation':  score['score_confirmation'],
            'score_clarity':       score['score_clarity'],
            'confidence_label':    score['confidence_label'],
            'risk_label':          score['risk_label'],
            'rr_ratio':            score['rr_ratio'],
            'scoring_version':     score['scoring_version'],
            'score_breakdown':     json.dumps(score['score_breakdown']),
            'notes':               score['notes'],
        }
        if tenant_id:
            score_row['tenant_id'] = tenant_id

        _sb_insert('signal_scores', score_row)
        _sb_patch('signal_candidates', candidate_id, {
            'review_status': 'scored',
            'updated_at':    datetime.now(timezone.utc).isoformat(),
        })

        logger.info(
            f"Scored {candidate_id} — total={score['score_total']} "
            f"conf={score['confidence_label']} risk={score['risk_label']} "
            f"R:R={score['rr_ratio']}"
        )
        return score

    except Exception as e:
        logger.error(f"Scoring failed for candidate {candidate_id}: {e}")
        return None
