"""
Weight Optimizer.

Reads scoring_weights from Supabase and adjusts them based on outcome patterns.

Adjustment logic:
  - If a dimension's associated signals/strategies mostly get approved →
    slight upward nudge (reinforce what works).
  - If a dimension is consistently full but outcomes are rejected →
    slight downward nudge (dimension may be noise).
  - Weight is capped at [baseline * 0.6, baseline * 1.5] to prevent drift.
  - A single run adjusts by at most MAX_DELTA per dimension.

This module never touches signal_scores or strategy_scores directly —
it only updates the scoring_weights table that the scoring services
read at startup (or dynamically if they choose to fetch weights).
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, List, Dict

logger = logging.getLogger('WeightOptimizer')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Maximum per-run delta as a fraction of the baseline weight
MAX_DELTA = float(os.getenv('WEIGHT_MAX_DELTA', '0.05'))
# Minimum sample count before any adjustment is made
MIN_SAMPLES = int(os.getenv('WEIGHT_MIN_SAMPLES', '10'))


def _headers() -> dict:
    key = os.getenv('SUPABASE_KEY', SUPABASE_KEY)
    return {
        'apikey':        key,
        'Authorization': f'Bearer {key}',
        'Content-Type':  'application/json',
        'Prefer':        'return=minimal',
    }


def _sb_get(path: str) -> list:
    url = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={**_headers(), 'Prefer': ''})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


def _sb_patch(path: str, body: dict) -> bool:
    url  = f"{os.getenv('SUPABASE_URL', SUPABASE_URL)}/rest/v1/{path}"
    data = json.dumps(body).encode()
    req  = urllib.request.Request(url, data=data, headers=_headers(), method='PATCH')
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            return True
    except urllib.error.HTTPError as e:
        logger.error(f"PATCH {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return False
    except Exception as e:
        logger.error(f"PATCH {path} → {e}")
        return False


# ─── Weight retrieval ─────────────────────────────────────────────────────────

def get_active_weights(scorer_type: str) -> Dict[str, float]:
    """
    Return {dimension: weight} for all active rows of the given scorer_type.
    Falls back to 1.0 for any missing dimension.
    """
    rows = _sb_get(
        f"scoring_weights?scorer_type=eq.{scorer_type}"
        f"&is_active=eq.true&select=dimension,weight&limit=20"
    )
    return {r['dimension']: float(r.get('weight') or 1.0) for r in rows}


def get_weight_rows(scorer_type: str) -> List[dict]:
    """Return full scoring_weights rows for a scorer_type."""
    return _sb_get(
        f"scoring_weights?scorer_type=eq.{scorer_type}"
        f"&is_active=eq.true&select=*&limit=20"
    )


# ─── Adjustment logic ─────────────────────────────────────────────────────────

def _clamp(value: float, baseline: float) -> float:
    lo = baseline * 0.6
    hi = baseline * 1.5
    return max(lo, min(hi, value))


def compute_signal_adjustments(outcome_rows: List[dict]) -> Dict[str, float]:
    """
    Given recent outcome_events rows for signals, compute suggested weight deltas
    per dimension.

    Heuristic:
    - approved outcomes with high scores → positive delta for dimensions
      that tend to be populated in good signals
    - rejected outcomes with scores above threshold → negative delta
      (the score was high but the signal still got rejected, suggesting
      over-weighting of some dimension)

    Returns {dimension: delta} — deltas are small (≤ MAX_DELTA).
    Since we don't have per-dimension breakdown in outcome_events, we use
    the overall approval/rejection ratio as a proxy signal.
    """
    approved = [r for r in outcome_rows if 'approved' in r.get('event_type', '')]
    rejected = [r for r in outcome_rows if 'rejected' in r.get('event_type', '')]
    total    = len(approved) + len(rejected)

    if total < MIN_SAMPLES:
        logger.info(f"Signal: only {total} samples (min {MIN_SAMPLES}), skipping adjustment")
        return {}

    approval_rate = len(approved) / total

    # Global adjustment based on approval rate
    # Target rate: ~0.6 (aim for quality gate at 60%)
    target_rate = 0.6
    delta = (approval_rate - target_rate) * MAX_DELTA

    # Apply same delta to all signal dimensions (global nudge)
    dimensions = ['setup_quality', 'risk_quality', 'confirmation', 'clarity']
    logger.info(
        f"Signal: total={total} approval={approval_rate:.2%} "
        f"target={target_rate:.2%} delta={delta:+.4f}"
    )
    return {dim: delta for dim in dimensions}


def compute_strategy_adjustments(outcome_rows: List[dict]) -> Dict[str, float]:
    """Same heuristic applied to strategy outcomes."""
    approved = [r for r in outcome_rows if 'approved' in r.get('event_type', '')]
    rejected = [r for r in outcome_rows if 'rejected' in r.get('event_type', '')]
    total    = len(approved) + len(rejected)

    if total < MIN_SAMPLES:
        logger.info(f"Strategy: only {total} samples (min {MIN_SAMPLES}), skipping adjustment")
        return {}

    approval_rate = len(approved) / total
    target_rate   = 0.55
    delta = (approval_rate - target_rate) * MAX_DELTA

    dimensions = [
        'clarity', 'rule_definition', 'risk_explanation',
        'structure', 'educational_quality',
    ]
    logger.info(
        f"Strategy: total={total} approval={approval_rate:.2%} "
        f"target={target_rate:.2%} delta={delta:+.4f}"
    )
    return {dim: delta for dim in dimensions}


def apply_adjustments(scorer_type: str, deltas: Dict[str, float]) -> int:
    """
    Apply computed deltas to scoring_weights rows.
    Returns count of rows actually updated.
    """
    if not deltas:
        return 0

    rows    = get_weight_rows(scorer_type)
    updated = 0
    now     = datetime.now(timezone.utc).isoformat()

    for row in rows:
        dim      = row['dimension']
        delta    = deltas.get(dim)
        if delta is None or abs(delta) < 1e-6:
            continue

        baseline    = float(row.get('baseline') or 1.0)
        current     = float(row.get('weight')   or 1.0)
        new_weight  = _clamp(current + delta, baseline)

        if abs(new_weight - current) < 1e-6:
            continue  # clamped to no change

        reason = (
            f"Auto-adjusted {delta:+.4f} on {now[:10]} "
            f"(approval rate nudge, {scorer_type})"
        )
        ok = _sb_patch(
            f"scoring_weights?scorer_type=eq.{scorer_type}&dimension=eq.{dim}",
            {'weight': round(new_weight, 4), 'adjustment_reason': reason, 'updated_at': now},
        )
        if ok:
            logger.info(
                f"Weight updated: {scorer_type}/{dim} "
                f"{current:.4f} → {new_weight:.4f} (Δ{delta:+.4f})"
            )
            updated += 1

    return updated


def compute_weight_drift(scorer_type: str) -> float:
    """
    Return L1 distance of current weights from baseline (sum of |w - b|).
    Zero means no drift from defaults.
    """
    rows  = get_weight_rows(scorer_type)
    drift = sum(
        abs(float(r.get('weight') or 1.0) - float(r.get('baseline') or 1.0))
        for r in rows
    )
    return round(drift, 4)
