"""
scoring/scorer.py — Deterministic 10-dimension strategy scorer.

Scores strategy_candidates (status='draft') against the actual strategy_scores schema.

Dimensions (each 0–10):
  clarity_score           — title quality + content length + identifiable setup
  risk_definition_score   — stop loss + risk:reward + invalidation concept
  testability_score       — clear entry/exit conditions that can be backtested
  replicability_score     — rules another trader can follow without interpretation
  asset_fit_score         — content matches the inferred asset class
  data_availability_score — uses standard indicators (not exotic/proprietary)
  quality_score           — overall educational value + originality
  complexity_score        — appropriate complexity (not too simple, not too convoluted)
  risk_score              — explicit risk management framing
  penalty_score           — deductions for red flags (executions instructions, guaranteed claims)

total_score = sum(all except penalty) - penalty_score  (capped 0–100)

recommendation: total >= 70 → 'approve' | >= 45 → 'review' | < 45 → 'reject'
"""

import sys
import re
import json
import logging
from pathlib import Path

_LAB_ROOT   = Path(__file__).resolve().parent.parent
_NEXUS_ROOT = _LAB_ROOT.parent
for _p in (_LAB_ROOT, _NEXUS_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from config import settings
settings.validate()

from db import supabase_client as db

logger = logging.getLogger(__name__)


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _kw(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _count_kw(text: str, keywords: list) -> int:
    t = text.lower()
    return sum(1 for k in keywords if k in t)


# ── 10 Dimension scorers (each returns 0.0–10.0) ─────────────────────────────

def _clarity(name: str, content: str) -> float:
    pts = 0.0
    if len(name) >= 5: pts += 2
    if len(name) >= 20: pts += 1
    words = len(content.split())
    if words >= 300: pts += 4
    elif words >= 100: pts += 3
    elif words >= 30: pts += 1
    if _kw(content + name, ['strategy', 'setup', 'signal', 'entry', 'indicator', 'pattern']):
        pts += 3
    return min(pts, 10.0)


def _risk_definition(content: str) -> float:
    pts = 0.0
    if _kw(content, ['stop loss', 'stop-loss', 'stoploss', 'invalidation', 'cut loss']):
        pts += 4
    if _kw(content, ['risk:reward', 'risk/reward', 'r:r', 'r/r', '2:1', '3:1']):
        pts += 3
    if _kw(content, ['position size', 'position sizing', 'account risk', '% of capital']):
        pts += 3
    return min(pts, 10.0)


def _testability(content: str) -> float:
    pts = 0.0
    entry_count = _count_kw(content, ['entry', 'enter', 'buy when', 'sell when', 'long when',
                                       'short when', 'signal fires', 'trigger'])
    exit_count  = _count_kw(content, ['exit', 'close', 'take profit', 'target', 'profit level'])
    if entry_count >= 2: pts += 4
    elif entry_count >= 1: pts += 2
    if exit_count >= 2: pts += 4
    elif exit_count >= 1: pts += 2
    if _kw(content, ['backtest', 'historically', 'tested', 'win rate', 'accuracy']):
        pts += 2
    return min(pts, 10.0)


def _replicability(content: str) -> float:
    pts = 0.0
    sentences = [s for s in re.split(r'[.!?\n]+', content) if len(s.strip()) > 10]
    if len(sentences) >= 10: pts += 3
    elif len(sentences) >= 5: pts += 2
    indicator_kws = ['rsi', 'macd', 'ema', 'sma', 'bollinger', 'atr', 'stochastic',
                     'fibonacci', 'vwap', 'volume', 'moving average']
    kw_hits = _count_kw(content, indicator_kws)
    if kw_hits >= 3: pts += 4
    elif kw_hits >= 1: pts += 2
    if _kw(content, ['step 1', 'step 2', 'first', 'then', 'next', 'finally']):
        pts += 3
    return min(pts, 10.0)


def _asset_fit(name: str, content: str, asset_class: str) -> float:
    asset_kws = {
        'forex':    ['forex', 'currency', 'pip', 'eurusd', 'gbpusd', 'fx'],
        'crypto':   ['bitcoin', 'crypto', 'ethereum', 'blockchain', 'altcoin'],
        'equities': ['stock', 'equity', 'share', 'nasdaq', 'earnings'],
        'futures':  ['futures', 'contract', 'commodity', 'rollover'],
        'options':  ['option', 'call', 'put', 'premium', 'expiry', 'strike'],
    }
    if asset_class in asset_kws:
        hits = _count_kw(name + ' ' + content, asset_kws[asset_class])
        if hits >= 3: return 10.0
        if hits >= 1: return 7.0
        return 4.0
    return 6.0  # multi-asset — neutral


def _data_availability(content: str) -> float:
    standard_kws = ['rsi', 'macd', 'ema', 'sma', 'bollinger bands', 'atr', 'stochastic',
                     'open', 'high', 'low', 'close', 'volume', 'candlestick', 'price action',
                     'support', 'resistance', 'trend line', 'fibonacci']
    exotic_kws = ['proprietary', 'exclusive indicator', 'custom algorithm', 'black box',
                  'neural network', 'ml model', 'ai signal']
    hits = _count_kw(content, standard_kws)
    if _kw(content, exotic_kws):
        return 3.0
    if hits >= 5: return 10.0
    if hits >= 3: return 8.0
    if hits >= 1: return 6.0
    return 4.0


def _quality(name: str, content: str) -> float:
    pts = 0.0
    if len(content) > 1000: pts += 3
    elif len(content) > 500: pts += 2
    explain_kws = ['because', 'this means', 'this indicates', 'the reason', 'understand',
                   'concept', 'principle', 'important', 'note that']
    if _count_kw(content, explain_kws) >= 3: pts += 4
    elif _count_kw(content, explain_kws) >= 1: pts += 2
    if _kw(content, ['when it works', 'when it fails', 'avoid', 'best in', 'ideal for']):
        pts += 3
    return min(pts, 10.0)


def _complexity(content: str) -> float:
    """
    Appropriate complexity = 5–8. Too simple or too complex both score lower.
    """
    words = len(content.split())
    indicator_count = _count_kw(content,
        ['rsi', 'macd', 'ema', 'sma', 'bollinger', 'atr', 'fibonacci',
         'stochastic', 'volume', 'vwap', 'ichimoku', 'parabolic', 'adx'])
    if 2 <= indicator_count <= 5 and 200 <= words <= 2000:
        return 8.0
    if indicator_count == 1 or words < 100:
        return 4.0
    if indicator_count > 7 or words > 5000:
        return 5.0
    return 6.0


def _risk_score(content: str) -> float:
    """Overall risk management framing score."""
    pts = 0.0
    if _kw(content, ['risk management', 'capital preservation', 'protect']):
        pts += 4
    if _kw(content, ['drawdown', 'max loss', 'losing streak']):
        pts += 3
    if _kw(content, ['journal', 'track', 'review trades', 'improvement']):
        pts += 3
    return min(pts, 10.0)


def _penalty(name: str, content: str) -> float:
    """Deduction score for red flags. Higher = more deducted."""
    pts = 0.0
    red_flags = ['guaranteed profit', 'always works', '100% accuracy', 'never lose',
                 'click buy', 'execute now', 'open trade immediately', 'place market order now']
    hits = _count_kw(name + ' ' + content, red_flags)
    if hits >= 2: pts += 6
    elif hits >= 1: pts += 3
    if _kw(content, ['contact us', 'buy our course', 'subscribe', 'discount code']):
        pts += 2
    return min(pts, 10.0)


# ── Compute + persist ─────────────────────────────────────────────────────────

def compute_score(candidate: dict) -> dict:
    """
    Pure deterministic score computation. No I/O.
    candidate must have: candidate_name, asset_class, and text from transcript.
    """
    name    = (candidate.get('strategy_name') or candidate.get('candidate_name') or candidate.get('title') or '').strip()
    content = (candidate.get('_transcript_text') or '').strip()
    asset   = candidate.get('market') or candidate.get('asset_class') or 'multi'

    clarity   = _clarity(name, content)
    risk_def  = _risk_definition(content)
    testable  = _testability(content)
    replica   = _replicability(content)
    asset_fit = _asset_fit(name, content, asset)
    data_avail = _data_availability(content)
    quality   = _quality(name, content)
    complexity = _complexity(content)
    risk      = _risk_score(content)
    penalty   = _penalty(name, content)

    positive_sum = (clarity + risk_def + testable + replica + asset_fit +
                    data_avail + quality + complexity + risk)
    # Scale to 100: 9 dimensions × 10 = 90 max positive; normalise to 100
    total = round(min(100.0, (positive_sum / 90.0) * 100.0 - penalty), 2)
    total = max(0.0, total)

    if total >= 70:
        recommendation = 'approve'
    elif total >= 45:
        recommendation = 'review'
    else:
        recommendation = 'reject'

    reasoning = (
        f"clarity={clarity} risk_def={risk_def} testable={testable} replica={replica} "
        f"asset_fit={asset_fit} data={data_avail} quality={quality} "
        f"complexity={complexity} risk={risk} penalty={penalty} → total={total}"
    )

    return {
        'clarity_score':            round(clarity, 2),
        'risk_definition_score':    round(risk_def, 2),
        'testability_score':        round(testable, 2),
        'replicability_score':      round(replica, 2),
        'asset_fit_score':          round(asset_fit, 2),
        'data_availability_score':  round(data_avail, 2),
        'quality_score':            round(quality, 2),
        'complexity_score':         round(complexity, 2),
        'risk_score':               round(risk, 2),
        'penalty_score':            round(penalty, 2),
        'total_score':              total,
        'overall_score':            total,    # legacy column alias
        'recommendation':           recommendation,
        'reasoning':                reasoning,
        'scored_by':                'deterministic_v1',
    }


def score_candidate(candidate_id: str, candidate: dict) -> dict | None:
    """
    Score a candidate and persist to strategy_scores.
    Fetches transcript text from strategy_transcripts if not already on candidate.
    Idempotent — returns cached score if already scored.
    """
    # Idempotency — strategy_scores uses strategy_uuid as the FK
    try:
        existing = db.select('strategy_scores',
                             f'strategy_uuid=eq.{candidate_id}&select=*&limit=1')
        if existing:
            logger.info(f"Cached score for strategy {candidate_id}")
            return existing[0]
    except Exception:
        pass

    # Build text for scoring from strategy_library fields
    if not candidate.get('_transcript_text'):
        name    = candidate.get('strategy_name') or candidate.get('title') or ''
        summary = candidate.get('summary') or ''
        rules   = ' '.join([
            json.dumps(candidate.get('entry_rules') or {}),
            json.dumps(candidate.get('exit_rules') or {}),
            json.dumps(candidate.get('risk_rules') or {}),
        ])
        candidate['_transcript_text'] = f"{summary} {rules}"

    score = compute_score(candidate)
    score_row = {**score, 'strategy_uuid': candidate_id, 'evidence': {}}

    try:
        inserted = db.insert('strategy_scores', score_row)
        score_id = inserted.get('id')
        if not score_id:
            logger.error(f"strategy_scores insert returned no id for candidate {candidate_id}")
            return None

        # Update strategy_library status
        try:
            db.update('strategy_library',
                      {'status': 'scored'},
                      f'id=eq.{candidate_id}')
        except Exception as ue:
            logger.warning(f"Could not update strategy_library status: {ue}")

        logger.info(
            f"Scored candidate {candidate_id}: total={score['total_score']} "
            f"rec={score['recommendation']}"
        )
        return {**score_row, 'id': score_id}

    except Exception as e:
        logger.error(f"strategy_scores insert failed for candidate {candidate_id}: {e}")
        return None


def run_scoring(batch_size: int = 20) -> dict:
    """Fetch 'draft' strategy_library entries and score each one."""
    try:
        candidates = db.select(
            'strategy_library',
            f'status=eq.draft&select=*&order=created_at.asc&limit={batch_size}'
        )
    except Exception as e:
        logger.error(f"Could not fetch candidates: {e}")
        return {'scored': 0, 'cached': 0, 'errors': 1}

    if not candidates:
        logger.info("No unscored candidates found.")
        return {'scored': 0, 'cached': 0, 'errors': 0}

    scored = cached = errors = 0
    for candidate in candidates:
        cid = candidate.get('id')
        try:
            result = score_candidate(cid, candidate)
            if result:
                # Distinguish new vs cached
                cached += 1 if result.get('scored_by') and 'candidate_id' in result else 0
                scored += 1
            else:
                errors += 1
        except Exception as e:
            logger.error(f"Scoring error for candidate {cid}: {e}")
            errors += 1

    logger.info(f"Scoring: scored={scored} errors={errors}")
    return {'scored': scored, 'cached': cached, 'errors': errors}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    stats = run_scoring()
    print(f"\nScoring complete: {stats}")
