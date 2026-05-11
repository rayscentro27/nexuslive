"""
Optimization Summary Job.

Aggregates recommendation and task outcomes per agent, stores summary
metrics in performance_metrics, and sends a Telegram alert when
agent effectiveness drops below thresholds.

Run standalone:
    cd /Users/raymonddavis/nexus-ai
    source .env && python3 -m optimization_engine.optimization_summary_job

Called by optimization_worker every 6 hours.
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger('OptimizationSummaryJob')

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

# Alert thresholds
MIN_ACCEPTANCE_RATE = float(os.getenv('OPT_MIN_ACCEPTANCE_RATE', '0.3'))
MIN_COMPLETION_RATE = float(os.getenv('OPT_MIN_COMPLETION_RATE', '0.3'))
MIN_SAMPLES         = int(os.getenv('OPT_MIN_SAMPLES', '5'))
LOOKBACK_DAYS       = int(os.getenv('OPT_LOOKBACK_DAYS', '7'))


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
        logger.warning(f"Telegram: {e}")


def _store_metric(metric_type: str, value: float, meta: Optional[dict] = None) -> None:
    """Write a row to performance_metrics (fire-and-forget)."""
    try:
        from optimization_engine.performance_reporter import store_metric
        store_metric(metric_type=metric_type, value=value, meta=meta or {})
    except Exception as e:
        logger.warning(f"store_metric failed: {e}")


from typing import Optional


# ─── Aggregators ──────────────────────────────────────────────────────────────

def _rec_stats_by_agent() -> dict:
    """Return {agent_name: {total, accepted, rejected, pending, rate}} for last N days."""
    try:
        from optimization_engine.recommendation_tracker import get_recent_recommendations
        rows = get_recent_recommendations(days=LOOKBACK_DAYS, limit=2000)
    except Exception as e:
        logger.warning(f"rec_stats_by_agent: {e}")
        return {}

    by_agent: dict = {}
    for row in rows:
        a = row.get('agent_name', 'unknown')
        if a not in by_agent:
            by_agent[a] = {'total': 0, 'accepted': 0, 'rejected': 0, 'pending': 0}
        by_agent[a]['total'] += 1
        o = row.get('outcome', 'pending')
        if o in by_agent[a]:
            by_agent[a][o] += 1

    for a, s in by_agent.items():
        total = s['total']
        s['acceptance_rate'] = round(s['accepted'] / total, 3) if total else 0.0

    return by_agent


def _task_stats_by_agent() -> dict:
    """Return {agent_name: {total, completed, cancelled, pending, rate}} for last N days."""
    try:
        from optimization_engine.task_outcome_tracker import get_all_agent_stats
        rows = get_all_agent_stats(days=LOOKBACK_DAYS)
    except Exception as e:
        logger.warning(f"task_stats_by_agent: {e}")
        return {}
    return {r['agent_name']: r for r in rows}


# ─── Main ─────────────────────────────────────────────────────────────────────

def run() -> dict:
    """
    Run the optimization summary job.
    Returns a summary dict for logging/testing.
    """
    logger.info("Optimization summary job starting")
    now  = datetime.now(timezone.utc).isoformat()
    alerts = []
    metrics_written = 0

    rec_stats  = _rec_stats_by_agent()
    task_stats = _task_stats_by_agent()

    all_agents = set(list(rec_stats.keys()) + list(task_stats.keys()))

    for agent in sorted(all_agents):
        rs = rec_stats.get(agent, {})
        ts = task_stats.get(agent, {})

        rec_total = rs.get('total', 0)
        task_total = ts.get('total', 0)

        # Store recommendation acceptance rate
        if rec_total >= MIN_SAMPLES:
            rate = rs.get('acceptance_rate', 0.0)
            _store_metric(
                f'{agent}.recommendation_acceptance_rate',
                rate,
                meta={'agent': agent, 'samples': rec_total, 'days': LOOKBACK_DAYS},
            )
            metrics_written += 1
            if rate < MIN_ACCEPTANCE_RATE:
                alerts.append(
                    f'{agent}: low recommendation acceptance {rate:.0%} ({rec_total} samples)'
                )

        # Store task completion rate
        if task_total >= MIN_SAMPLES:
            crate = ts.get('completion_rate', 0.0)
            _store_metric(
                f'{agent}.task_completion_rate',
                crate,
                meta={'agent': agent, 'samples': task_total, 'days': LOOKBACK_DAYS},
            )
            metrics_written += 1
            if crate < MIN_COMPLETION_RATE:
                alerts.append(
                    f'{agent}: low task completion {crate:.0%} ({task_total} tasks)'
                )

        logger.info(
            f"Agent {agent}: rec={rec_total} accepted={rs.get('accepted',0)} "
            f"tasks={task_total} completed={ts.get('completed',0)}"
        )

    # Send Telegram alert on issues
    if alerts:
        lines = '\n'.join(f'⚠ {a}' for a in alerts)
        _send_telegram(
            f'<b>Nexus Agent Effectiveness Alert</b>\n\n{lines}'
            f'\n\n<i>Last {LOOKBACK_DAYS}d window</i>'
        )
        logger.warning(f"Effectiveness alerts: {alerts}")
    else:
        logger.info(f"Agent effectiveness OK — {metrics_written} metrics written")

    return {
        'agents_evaluated': len(all_agents),
        'metrics_written':  metrics_written,
        'alerts':           alerts,
        'run_at':           now,
    }


if __name__ == '__main__':
    import sys
    _env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _, _v = _line.partition('=')
                    os.environ.setdefault(_k.strip(), _v.strip())

    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s %(message)s')
    result = run()
    print(json.dumps(result, indent=2))
