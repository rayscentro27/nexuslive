"""
Strategy Scoring Service.

Applies deterministic 5-dimension text-quality scoring to a strategy_candidate.
No external AI calls — pure keyword/heuristic analysis + one Supabase write.

Score dimensions (20 pts each, 100 pts total):
  clarity             — title quality, content length, strategy type identifiable
  rule_definition     — entry/exit rules present, conditions specified
  risk_explanation    — stop loss concept, risk management, position sizing
  structure           — multiple sections, when_it_works / when_it_fails present
  educational_quality — readable for retail, avoids execution instructions, original

Confidence labels: score ≥ 75 → high | ≥ 50 → medium | < 50 → low
Difficulty levels:
  advanced     — advanced keywords detected
  intermediate — medium-complexity keywords
  beginner     — default / simple content

Usage:
  from strategy_scoring_service import score_strategy_candidate
  score = score_strategy_candidate(candidate_id, candidate_dict)
"""

import os
import json
import re
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('StrategyScoringService')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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


# ─── Scoring helpers ──────────────────────────────────────────────────────────

def _kw(text: str, keywords: list[str]) -> bool:
    """True if ANY keyword found in text (case-insensitive)."""
    t = text.lower()
    return any(kw in t for kw in keywords)


def _count_kw(text: str, keywords: list[str]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


# ─── 5 Dimensions ─────────────────────────────────────────────────────────────

def _score_clarity(title: str, content: str) -> tuple[float, list[str]]:
    """
    0–20 pts. Title quality + content length + strategy identifiability.
    """
    notes = []
    pts = 0.0

    # Title quality
    if len(title) >= 5:
        pts += 5
    else:
        notes.append('title_too_short')

    if len(title) >= 15:
        pts += 3   # descriptive title

    # Content length
    words = len(content.split())
    if words >= 300:
        pts += 7
    elif words >= 100:
        pts += 5
    elif words >= 30:
        pts += 2
    else:
        notes.append('content_too_short')

    # Strategy type identifiable
    type_kws = ['strategy', 'setup', 'pattern', 'signal', 'trade', 'entry', 'indicator']
    if _kw(content + title, type_kws):
        pts += 5
    else:
        notes.append('strategy_type_unclear')

    return min(pts, 20.0), notes


def _score_rule_definition(content: str) -> tuple[float, list[str]]:
    """
    0–20 pts. Entry rules + exit rules + conditions.
    """
    notes = []
    pts = 0.0

    entry_kws = ['entry', 'enter', 'buy when', 'sell when', 'long when', 'short when',
                 'trigger', 'signal fires', 'open position', 'initiate']
    exit_kws  = ['exit', 'close', 'take profit', 'target', 'profit level',
                 'close position', 'sell to close', 'buy to close']
    cond_kws  = ['when', 'if', 'condition', 'requires', 'must', 'only if',
                 'provided that', 'as long as', 'confirms', 'confluence']

    if _count_kw(content, entry_kws) >= 1:
        pts += 7
    else:
        notes.append('no_entry_rules')

    if _count_kw(content, exit_kws) >= 1:
        pts += 7
    else:
        notes.append('no_exit_rules')

    if _count_kw(content, cond_kws) >= 2:
        pts += 6
    elif _count_kw(content, cond_kws) >= 1:
        pts += 3
    else:
        notes.append('no_conditions_defined')

    return min(pts, 20.0), notes


def _score_risk_explanation(content: str) -> tuple[float, list[str]]:
    """
    0–20 pts. Stop loss concept + risk management + position sizing.
    """
    notes = []
    pts = 0.0

    stop_kws  = ['stop loss', 'stop-loss', 'stoploss', 'stop at', 'invalidation',
                 'cut loss', 'cut the loss', 'maximum loss', 'stop order']
    risk_kws  = ['risk management', 'risk:reward', 'risk/reward', 'r:r', 'r/r',
                 'risk management', 'drawdown', 'capital at risk', 'max loss']
    size_kws  = ['position size', 'position sizing', 'lot size', 'units', 'percent of capital',
                 '% of account', 'account risk', 'kelly', 'fixed risk']

    if _kw(content, stop_kws):
        pts += 8
    else:
        notes.append('no_stop_loss_concept')

    if _kw(content, risk_kws):
        pts += 7
    else:
        notes.append('no_risk_management')

    if _kw(content, size_kws):
        pts += 5
    else:
        notes.append('no_position_sizing')

    return min(pts, 20.0), notes


def _score_structure(content: str) -> tuple[float, list[str]]:
    """
    0–20 pts. Multiple sections + when_it_works + when_it_fails concepts.
    """
    notes = []
    pts = 0.0

    # Multiple paragraphs / sections
    paragraphs = [p for p in re.split(r'\n\s*\n', content.strip()) if p.strip()]
    if len(paragraphs) >= 4:
        pts += 7
    elif len(paragraphs) >= 2:
        pts += 4
    else:
        notes.append('single_block_content')

    works_kws = ['works well', 'best in', 'ideal for', 'performs in', 'suited for',
                 'trending market', 'when trend', 'when volatility', 'in this condition']
    fails_kws = ['avoid', 'does not work', "doesn't work", 'fails in', 'not suited',
                 'choppy', 'ranging market', 'low volume', 'when to avoid', 'risk of']

    if _kw(content, works_kws):
        pts += 7
    else:
        notes.append('no_when_it_works')

    if _kw(content, fails_kws):
        pts += 6
    else:
        notes.append('no_when_it_fails')

    return min(pts, 20.0), notes


def _score_educational_quality(title: str, content: str) -> tuple[float, list[str]]:
    """
    0–20 pts. Readable, avoids execution-only framing, educational context.
    """
    notes = []
    pts = 0.0

    # Readable sentence count
    sentences = re.split(r'[.!?]+', content)
    sentences = [s for s in sentences if len(s.strip()) > 10]
    if len(sentences) >= 10:
        pts += 5
    elif len(sentences) >= 4:
        pts += 3
    else:
        notes.append('too_few_sentences')

    # Educational framing (explains concepts)
    explain_kws = ['because', 'this means', 'this indicates', 'the reason', 'in other words',
                   'this works', 'understand', 'note that', 'important', 'key point',
                   'learner', 'educational', 'concept', 'principle']
    if _count_kw(content, explain_kws) >= 3:
        pts += 7
    elif _count_kw(content, explain_kws) >= 1:
        pts += 4
    else:
        notes.append('no_educational_framing')

    # Avoids pure execution framing (no broker-specific execution instructions)
    exec_kws = ['place market order', 'click buy', 'open trade now', 'execute immediately',
                'guaranteed profit', 'always works', '100%']
    if not _kw(content + title, exec_kws):
        pts += 5
    else:
        notes.append('execution_framing_detected')

    # Original / non-trivial content
    if len(content) > 500:
        pts += 3

    return min(pts, 20.0), notes


# ─── Labels ───────────────────────────────────────────────────────────────────

def _confidence_label(total: float) -> str:
    if total >= 75: return 'high'
    if total >= 50: return 'medium'
    return 'low'


_ADVANCED_KW    = ['multi-timeframe', 'correlation', 'arbitrage', 'scalping', 'algorithmic',
                   'quantitative', 'options', 'derivatives', 'statistical', 'pairs trading']
_INTERMEDIATE_KW = ['swing trading', 'fibonacci', 'rsi', 'macd', 'bollinger', 'momentum',
                    'volume analysis', 'candlestick pattern', 'trend line', 'support resistance']


def _difficulty_level(title: str, content: str, total: float) -> str:
    text = (title + ' ' + content).lower()
    if any(kw in text for kw in _ADVANCED_KW):
        return 'advanced'
    if any(kw in text for kw in _INTERMEDIATE_KW):
        return 'intermediate'
    # Score-based fallback
    if total >= 70:
        return 'intermediate'
    return 'beginner'


# ─── Pure compute (no I/O) ────────────────────────────────────────────────────

def compute_score(candidate: dict) -> dict:
    """
    Pure deterministic scoring. No I/O. Safe to call without Supabase.

    Args:
        candidate: strategy_candidates dict with title, raw_content, strategy_type

    Returns:
        Score dict with all dimension scores and labels.
    """
    title   = (candidate.get('title') or '').strip()
    content = (candidate.get('raw_content') or '').strip()

    s_clarity, n1 = _score_clarity(title, content)
    s_rules,   n2 = _score_rule_definition(content)
    s_risk,    n3 = _score_risk_explanation(content)
    s_struct,  n4 = _score_structure(content)
    s_edu,     n5 = _score_educational_quality(title, content)

    total = s_clarity + s_rules + s_risk + s_struct + s_edu
    all_notes = n1 + n2 + n3 + n4 + n5

    return {
        'score_total':               round(total, 2),
        'score_clarity':             round(s_clarity, 2),
        'score_rule_definition':     round(s_rules, 2),
        'score_risk_explanation':    round(s_risk, 2),
        'score_structure':           round(s_struct, 2),
        'score_educational_quality': round(s_edu, 2),
        'confidence_label':          _confidence_label(total),
        'difficulty_level':          _difficulty_level(title, content, total),
        'notes':                     ', '.join(all_notes) if all_notes else None,
    }


# ─── Supabase write (idempotent) ──────────────────────────────────────────────

def score_strategy_candidate(candidate_id: str, candidate: dict) -> Optional[dict]:
    """
    Score a strategy_candidate and persist to strategy_scores.
    Idempotent — returns cached score if already scored.

    Args:
        candidate_id: UUID of the strategy_candidates row.
        candidate:    The strategy_candidates dict (title, raw_content, etc.)

    Returns:
        Score dict, or None on failure.
    """
    # Idempotency check
    try:
        existing = _sb_get(
            f"strategy_scores?candidate_id=eq.{candidate_id}&select=*&limit=1"
        )
        if existing:
            logger.info(f"Cached score found for candidate {candidate_id}")
            return existing[0]
    except Exception:
        pass

    score = compute_score(candidate)
    score_row = {
        'candidate_id':              candidate_id,
        'score_total':               score['score_total'],
        'score_clarity':             score['score_clarity'],
        'score_rule_definition':     score['score_rule_definition'],
        'score_risk_explanation':    score['score_risk_explanation'],
        'score_structure':           score['score_structure'],
        'score_educational_quality': score['score_educational_quality'],
        'confidence_label':          score['confidence_label'],
        'difficulty_level':          score['difficulty_level'],
        'notes':                     score['notes'],
    }

    try:
        inserted = _sb_insert('strategy_scores', score_row)
        score_id = inserted.get('id')
        if not score_id:
            logger.error(f"strategy_scores insert returned no id for candidate {candidate_id}")
            return None

        # Update candidate status to 'scored'
        try:
            _sb_patch('strategy_candidates', candidate_id, {
                'review_status': 'scored',
                'updated_at':    datetime.now(timezone.utc).isoformat(),
            })
        except Exception as pe:
            logger.warning(f"Could not update candidate status to scored: {pe}")

        logger.info(
            f"Scored candidate {candidate_id}: "
            f"total={score['score_total']} conf={score['confidence_label']} "
            f"diff={score['difficulty_level']}"
        )
        return {**score_row, 'id': score_id}

    except Exception as e:
        logger.error(f"Failed to persist score for candidate {candidate_id}: {e}")
        return None
