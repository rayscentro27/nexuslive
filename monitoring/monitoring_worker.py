"""
Monitoring Worker.

Runs every N minutes. Checks:
  1. Stale worker heartbeats (no ping in > STALE_MINUTES)
  2. Queue depth (tv_normalized_signals status='new')
  3. Recent job failure rate (last hour)
  4. Recent error spikes (last 15 minutes)
  5. AI cost accumulation today

Sends Telegram alert for any threshold breach.

Run:
  cd /Users/raymonddavis/nexus-ai
  source .env && python3 -m monitoring.monitoring_worker

Or via cron (every 5 minutes):
  */5 * * * * cd /Users/raymonddavis/nexus-ai && source .env && \\
      python3 -m monitoring.monitoring_worker >> logs/monitoring.log 2>&1
"""

import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone, timedelta

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
logger = logging.getLogger('MonitoringWorker')

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID   = os.getenv('TELEGRAM_CHAT_ID', '')

STALE_MINUTES      = int(os.getenv('MONITOR_STALE_MINUTES',      '10'))
QUEUE_ALERT_DEPTH  = int(os.getenv('MONITOR_QUEUE_ALERT_DEPTH',  '50'))
FAIL_RATE_ALERT    = float(os.getenv('MONITOR_FAIL_RATE_ALERT',  '0.3'))
ERROR_SPIKE_COUNT  = int(os.getenv('MONITOR_ERROR_SPIKE_COUNT',  '5'))
COST_ALERT_USD     = float(os.getenv('MONITOR_COST_ALERT_USD',   '5.0'))

# Workers that should be running — alert if any go stale.
# Only include workers that actually call send_heartbeat(); others will spam.
EXPECTED_WORKERS = [
    'autonomy_worker',
]


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


def _send_telegram(text: str) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    body = json.dumps({
        'chat_id':    TELEGRAM_CHAT_ID,
        'text':       text,
        'parse_mode': 'HTML',
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as _:
            pass
    except Exception as e:
        logger.warning(f"Telegram alert failed: {e}")


# ─── Checks ───────────────────────────────────────────────────────────────────

def check_worker_heartbeats() -> list:
    """Return list of stale worker names (EXPECTED_WORKERS only)."""
    if not EXPECTED_WORKERS:
        return []
    now    = datetime.now(timezone.utc)
    cutoff = (now - timedelta(minutes=STALE_MINUTES)).isoformat()
    # Only query the workers we explicitly monitor — ignore everything else in the table
    id_filter = ','.join(EXPECTED_WORKERS)
    rows   = _sb_get(
        f"worker_heartbeats?select=worker_id,status,last_seen_at"
        f"&worker_id=in.({id_filter})&limit=50"
    )
    seen  = {r.get('worker_id') for r in rows}
    alive = {r['worker_id'] for r in rows if r.get('last_seen_at', '') > cutoff}
    stale = []
    for row in rows:
        wid = row.get('worker_id', '')
        if wid and wid not in alive:
            stale.append(wid)
    for w in EXPECTED_WORKERS:
        if w not in seen:
            stale.append(f"{w} (never registered)")
    return stale


def check_queue_depth() -> dict:
    """Return pending signal and strategy queue depths."""
    sig_rows   = _sb_get(
        "tv_normalized_signals?status=eq.new&select=id&limit=1000"
    )
    strat_rows = _sb_get(
        "research?select=id&limit=1000"
    )
    # Strategy queue: research rows not yet in strategy_candidates
    ingested = _sb_get(
        "strategy_candidates?select=source_research_id&limit=10000"
    )
    ingested_ids = {str(r.get('source_research_id')) for r in ingested if r.get('source_research_id')}
    pending_strat = sum(1 for r in strat_rows if str(r.get('id', '')) not in ingested_ids)

    return {
        'signals_pending':    len(sig_rows),
        'strategies_pending': pending_strat,
    }


def check_job_failures(hours: int = 1) -> dict:
    """Return job failure rate in the last N hours."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    rows   = _sb_get(
        f"job_events?created_at=gt.{cutoff}&select=status&limit=500"
    )
    if not rows:
        return {'total': 0, 'failed': 0, 'fail_rate': 0.0}
    total  = len(rows)
    failed = sum(1 for r in rows if r.get('status') == 'failed')
    return {
        'total':     total,
        'failed':    failed,
        'fail_rate': round(failed / total, 3) if total else 0.0,
    }


def check_error_spike(minutes: int = 15) -> int:
    """Return error count in the last N minutes."""
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    rows   = _sb_get(
        f"error_log?created_at=gt.{cutoff}&level=eq.error&select=id&limit=200"
    )
    return len(rows)


def check_ai_cost_today() -> float:
    """Return total estimated AI cost for today (UTC)."""
    today  = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    rows   = _sb_get(
        f"ai_usage_log?created_at=gt.{today.isoformat()}"
        f"&select=cost_usd&limit=10000"
    )
    return round(sum(float(r.get('cost_usd') or 0) for r in rows), 4)


# ─── Alert assembly ───────────────────────────────────────────────────────────

def run_checks() -> dict:
    stale_workers = check_worker_heartbeats()
    queue         = check_queue_depth()
    jobs          = check_job_failures(hours=1)
    error_count   = check_error_spike(minutes=15)
    ai_cost       = check_ai_cost_today()

    alerts = []
    if stale_workers:
        alerts.append(f"STALE WORKERS: {', '.join(stale_workers)}")
    if queue['signals_pending'] >= QUEUE_ALERT_DEPTH:
        alerts.append(f"SIGNAL QUEUE BACKLOG: {queue['signals_pending']} pending")
    if jobs['fail_rate'] >= FAIL_RATE_ALERT and jobs['total'] >= 3:
        alerts.append(
            f"HIGH FAILURE RATE: {jobs['fail_rate']:.0%} "
            f"({jobs['failed']}/{jobs['total']} jobs last hour)"
        )
    if error_count >= ERROR_SPIKE_COUNT:
        alerts.append(f"ERROR SPIKE: {error_count} errors in last 15 min")
    if ai_cost >= COST_ALERT_USD:
        alerts.append(f"AI COST: ${ai_cost:.4f} today (threshold ${COST_ALERT_USD})")

    return {
        'stale_workers': stale_workers,
        'queue':         queue,
        'jobs':          jobs,
        'errors_15m':    error_count,
        'ai_cost_today': ai_cost,
        'alerts':        alerts,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    logger.info("Monitoring check starting")
    result = run_checks()

    logger.info(
        f"Queue: signals={result['queue']['signals_pending']} "
        f"strategies={result['queue']['strategies_pending']} | "
        f"Jobs: fail_rate={result['jobs']['fail_rate']:.0%} | "
        f"Errors(15m): {result['errors_15m']} | "
        f"AI cost today: ${result['ai_cost_today']}"
    )

    if result['stale_workers']:
        logger.warning(f"Stale workers: {result['stale_workers']}")

    if result['alerts']:
        msg = '<b>Nexus System Alert</b>\n\n' + '\n'.join(
            f'⚠ {a}' for a in result['alerts']
        )
        _send_telegram(msg)
        logger.warning(f"Alerts sent: {result['alerts']}")
    else:
        logger.info("All checks passed — no alerts")

    logger.info("Monitoring check done.")


if __name__ == '__main__':
    main()
