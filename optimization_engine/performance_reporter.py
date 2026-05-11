"""
Performance Reporter.

Computes pipeline quality metrics for a rolling time window and writes
them to the performance_metrics table.

Metrics computed per run:
  signal_approval_rate   — fraction of signals approved in window
  strategy_approval_rate — fraction of strategies approved in window
  signal_avg_score       — mean score_total for approved signals
  strategy_avg_score     — mean score_total for approved strategies
  weight_drift           — L1 distance from baseline across all weights
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger('PerformanceReporter')

SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')


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
    except urllib.error.HTTPError as e:
        logger.error(f"POST {path} → HTTP {e.code}: {e.read().decode()[:200]}")
        return None
    except Exception as e:
        logger.error(f"POST {path} → {e}")
        return None


# ─── Metric computations ──────────────────────────────────────────────────────

def _compute_review_stats(review_table: str, hours: int) -> dict:
    """Count approved/rejected rows in a review table within the window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows   = _sb_get(
        f"{review_table}?created_at=gt.{cutoff}"
        f"&select=review_action,score_total&limit=500"
    )
    approved = [r for r in rows if r.get('review_action') == 'approve']
    rejected = [r for r in rows if r.get('review_action') == 'reject']
    total    = len(approved) + len(rejected)

    def avg_score(subset):
        scores = [float(r['score_total']) for r in subset if r.get('score_total') is not None]
        return round(sum(scores) / len(scores), 2) if scores else None

    return {
        'total':          total,
        'approved':       len(approved),
        'rejected':       len(rejected),
        'approval_rate':  round(len(approved) / total, 4) if total else None,
        'avg_score':      avg_score(approved),
    }


def compute_signal_metrics(period_hours: int = 24) -> dict:
    return _compute_review_stats('signal_reviews', period_hours)


def compute_strategy_metrics(period_hours: int = 24) -> dict:
    return _compute_review_stats('strategy_reviews', period_hours)


# ─── Metric storage ───────────────────────────────────────────────────────────

def store_metric(
    metric_type: str,
    value: Optional[float],
    period_hours: int,
    scorer_type: Optional[str] = None,
    sample_count: Optional[int] = None,
    meta: Optional[dict] = None,
) -> bool:
    """Write one row to performance_metrics."""
    now    = datetime.now(timezone.utc)
    start  = now - timedelta(hours=period_hours)
    row    = {
        'period_start': start.isoformat(),
        'period_end':   now.isoformat(),
        'metric_type':  metric_type,
        'scorer_type':  scorer_type,
        'value':        value,
        'sample_count': sample_count,
        'meta':         meta or {},
    }
    result = _sb_post('performance_metrics', row)
    return result is not None


def run_report(period_hours: int = 24) -> dict:
    """
    Compute all metrics for the given window, store each row, return a summary.
    """
    from weight_optimizer import compute_weight_drift

    now    = datetime.now(timezone.utc)
    report = {}

    # Signal metrics
    sig = compute_signal_metrics(period_hours)
    if sig['total'] > 0:
        store_metric(
            metric_type='signal_approval_rate',
            value=sig['approval_rate'],
            period_hours=period_hours,
            scorer_type='signal',
            sample_count=sig['total'],
            meta={'approved': sig['approved'], 'rejected': sig['rejected']},
        )
        if sig['avg_score'] is not None:
            store_metric(
                metric_type='signal_avg_score',
                value=sig['avg_score'],
                period_hours=period_hours,
                scorer_type='signal',
                sample_count=sig['approved'],
            )
    report['signal'] = sig

    # Strategy metrics
    strat = compute_strategy_metrics(period_hours)
    if strat['total'] > 0:
        store_metric(
            metric_type='strategy_approval_rate',
            value=strat['approval_rate'],
            period_hours=period_hours,
            scorer_type='strategy',
            sample_count=strat['total'],
            meta={'approved': strat['approved'], 'rejected': strat['rejected']},
        )
        if strat['avg_score'] is not None:
            store_metric(
                metric_type='strategy_avg_score',
                value=strat['avg_score'],
                period_hours=period_hours,
                scorer_type='strategy',
                sample_count=strat['approved'],
            )
    report['strategy'] = strat

    # Weight drift
    sig_drift   = compute_weight_drift('signal')
    strat_drift = compute_weight_drift('strategy')
    store_metric('weight_drift', sig_drift,   period_hours, 'signal')
    store_metric('weight_drift', strat_drift, period_hours, 'strategy')
    report['weight_drift'] = {'signal': sig_drift, 'strategy': strat_drift}

    report['period_hours'] = period_hours
    report['computed_at']  = now.isoformat()
    return report
