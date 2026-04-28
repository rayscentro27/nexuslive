"""
Optimization Worker.

Orchestrates the full auto-optimization loop:
  1. Record outcome events from recent signal and strategy pipeline results
     (approved → 'win', rejected → 'loss', expired → 'neutral')
  2. Compute weight adjustments based on recent outcome patterns
  3. Apply adjustments to scoring_weights
  4. Run performance metrics report
  5. Send Telegram alert if significant weight changes were made

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m optimization_engine.optimization_worker

Or via cron (every 6 hours):
  0 */6 * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m optimization_engine.optimization_worker >> \\
      logs/optimization_worker.log 2>&1
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional

# Load .env
_env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _, _v = _line.partition('=')
                os.environ.setdefault(_k.strip(), _v.strip())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
logger = logging.getLogger('OptimizationWorker')

from optimization_engine.outcome_tracker      import record_outcome, get_recent_outcomes, get_approval_stats
from optimization_engine.weight_optimizer     import (
    compute_signal_adjustments,
    compute_strategy_adjustments,
    apply_adjustments,
    compute_weight_drift,
)
from optimization_engine.performance_reporter import run_report
from optimization_engine.optimization_summary_job import run as run_agent_summary

SUPABASE_URL        = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY        = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN  = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID    = os.getenv('TELEGRAM_CHAT_ID', '')

LOOKBACK_HOURS      = int(os.getenv('OPTIM_LOOKBACK_HOURS', '24'))
REPORT_PERIOD_HOURS = int(os.getenv('OPTIM_REPORT_HOURS', '24'))
# Only alert when total adjusted dimension count exceeds this threshold
ALERT_THRESHOLD     = int(os.getenv('OPTIM_ALERT_THRESHOLD', '2'))


def _sb_get(path: str) -> list:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        'apikey':        SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
    })
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        logger.warning(f"GET {path} → {e}")
        return []


# ─── Outcome ingestion ────────────────────────────────────────────────────────

def _already_recorded(source_id: str, event_type: str) -> bool:
    """Prevent duplicate outcome rows for the same event."""
    rows = _sb_get(
        f"outcome_events?source_id=eq.{source_id}"
        f"&event_type=eq.{event_type}&select=id&limit=1"
    )
    return len(rows) > 0


def ingest_signal_outcomes(hours: int) -> int:
    """Record outcome events for recently approved/rejected signals."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    recorded = 0

    # Approved signals
    approved = _sb_get(
        f"approved_signals?created_at=gt.{cutoff}"
        f"&select=id,candidate_id,score_total,symbol,direction&limit=200"
    )
    for row in approved:
        sid = row.get('id')
        if not sid or _already_recorded(sid, 'signal_approved'):
            continue
        record_outcome(
            event_type='signal_approved',
            outcome='win',
            source_id=sid,
            source_type='signal',
            score_at_time=row.get('score_total'),
            meta={'symbol': row.get('symbol'), 'direction': row.get('direction')},
        )
        recorded += 1

    # Rejected signals (from signal_reviews)
    rejected = _sb_get(
        f"signal_reviews?created_at=gt.{cutoff}"
        f"&review_action=eq.reject"
        f"&select=id,candidate_id,score_total,notes&limit=200"
    )
    for row in rejected:
        rid = row.get('id')
        if not rid or _already_recorded(rid, 'signal_rejected'):
            continue
        record_outcome(
            event_type='signal_rejected',
            outcome='loss',
            source_id=rid,
            source_type='signal',
            score_at_time=row.get('score_total'),
            notes=row.get('notes'),
        )
        recorded += 1

    return recorded


def ingest_strategy_outcomes(hours: int) -> int:
    """Record outcome events for recently approved/rejected strategies."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    recorded = 0

    approved = _sb_get(
        f"approved_strategies?created_at=gt.{cutoff}"
        f"&select=id,candidate_id,score_total,title,strategy_type&limit=200"
    )
    for row in approved:
        sid = row.get('id')
        if not sid or _already_recorded(sid, 'strategy_approved'):
            continue
        record_outcome(
            event_type='strategy_approved',
            outcome='win',
            source_id=sid,
            source_type='strategy',
            score_at_time=row.get('score_total'),
            meta={
                'title':         row.get('title'),
                'strategy_type': row.get('strategy_type'),
            },
        )
        recorded += 1

    rejected = _sb_get(
        f"strategy_reviews?created_at=gt.{cutoff}"
        f"&review_action=eq.reject"
        f"&select=id,candidate_id,score_total,notes&limit=200"
    )
    for row in rejected:
        rid = row.get('id')
        if not rid or _already_recorded(rid, 'strategy_rejected'):
            continue
        record_outcome(
            event_type='strategy_rejected',
            outcome='loss',
            source_id=rid,
            source_type='strategy',
            score_at_time=row.get('score_total'),
            notes=row.get('notes'),
        )
        recorded += 1

    return recorded


# ─── Telegram alert ───────────────────────────────────────────────────────────

def _send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}).encode()
    req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            pass
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


def _build_alert(report: dict, sig_updated: int, strat_updated: int) -> str:
    sig   = report.get('signal',   {})
    strat = report.get('strategy', {})
    drift = report.get('weight_drift', {})
    lines = [
        '<b>Nexus Auto-Optimization Report</b>',
        f"Period: last {report.get('period_hours', '?')}h",
        '',
        '<b>Signals</b>',
        f"  Approval rate: {sig.get('approval_rate', 'N/A')}",
        f"  Avg score (approved): {sig.get('avg_score', 'N/A')}",
        f"  Weights adjusted: {sig_updated} dimension(s)",
        f"  Weight drift: {drift.get('signal', 'N/A')}",
        '',
        '<b>Strategies</b>',
        f"  Approval rate: {strat.get('approval_rate', 'N/A')}",
        f"  Avg score (approved): {strat.get('avg_score', 'N/A')}",
        f"  Weights adjusted: {strat_updated} dimension(s)",
        f"  Weight drift: {drift.get('strategy', 'N/A')}",
    ]
    return '\n'.join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info(
        f"Optimization worker starting "
        f"(lookback={LOOKBACK_HOURS}h, report={REPORT_PERIOD_HOURS}h)"
    )

    # 1. Record new outcome events
    sig_recorded   = ingest_signal_outcomes(LOOKBACK_HOURS)
    strat_recorded = ingest_strategy_outcomes(LOOKBACK_HOURS)
    logger.info(f"Outcome events recorded: signals={sig_recorded} strategies={strat_recorded}")

    # 2. Compute and apply weight adjustments
    sig_outcomes   = get_recent_outcomes(source_type='signal',   days=7)
    strat_outcomes = get_recent_outcomes(source_type='strategy', days=7)

    sig_deltas   = compute_signal_adjustments(sig_outcomes)
    strat_deltas = compute_strategy_adjustments(strat_outcomes)

    sig_updated   = apply_adjustments('signal',   sig_deltas)
    strat_updated = apply_adjustments('strategy', strat_deltas)
    logger.info(
        f"Weight updates applied: signal={sig_updated} strategy={strat_updated}"
    )

    # 3. Performance metrics report
    report = run_report(period_hours=REPORT_PERIOD_HOURS)
    logger.info(
        f"Metrics report: "
        f"signal approval={report['signal'].get('approval_rate')} "
        f"strategy approval={report['strategy'].get('approval_rate')} "
        f"drift signal={report['weight_drift']['signal']} "
        f"drift strategy={report['weight_drift']['strategy']}"
    )

    # 4. Telegram alert if notable changes
    if sig_updated + strat_updated >= ALERT_THRESHOLD:
        msg = _build_alert(report, sig_updated, strat_updated)
        _send_telegram(msg)
        logger.info("Telegram alert sent")

    # 5. Agent effectiveness summary (recommendation + task outcomes)
    try:
        summary = run_agent_summary()
        logger.info(
            f"Agent summary: {summary['agents_evaluated']} agents, "
            f"{summary['metrics_written']} metrics, "
            f"{len(summary['alerts'])} alert(s)"
        )
    except Exception as e:
        logger.warning(f"Agent summary job failed: {e}")

    logger.info("Optimization worker done.")


if __name__ == '__main__':
    main()
