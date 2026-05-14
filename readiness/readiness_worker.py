"""
Readiness Worker.

Runs all integration checks, stores results to Supabase,
sends Telegram report, and feeds Nexus One readiness state.

Cron: */30 * * * *  (every 30 min — fast feedback during setup/pilot)
      0 * * * *     (hourly once stable)

Run:
  python3 -m readiness.readiness_worker
  python3 -m readiness.readiness_worker --required-only
  python3 -m readiness.readiness_worker --silent   (store only, no Telegram)
"""

import os
import sys
import json
import logging
import urllib.request
from datetime import datetime, timezone
import lib.ssl_fix  # noqa — fixes HTTPS on macOS Python 3.14

logger = logging.getLogger('ReadinessWorker')


def _load_env() -> None:
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, _, v = line.partition('=')
                    os.environ.setdefault(k.strip(), v.strip())


def _send_telegram(message: str) -> None:
    from lib.telegram_notification_policy import should_send_telegram_notification

    allowed, _ = should_send_telegram_notification("worker_summary")
    if not allowed:
        return
    token   = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id:
        return
    try:
        url  = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({
            'chat_id':    chat_id,
            'text':       message,
            'parse_mode': 'HTML',
        }).encode()
        req = urllib.request.Request(
            url, data=body, headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def run(required_only: bool = False, silent: bool = False) -> dict:
    from readiness.integration_checks import run_all_checks, run_required_checks
    from readiness.readiness_reporter import (
        build_report, store_results, format_telegram_report, get_nexus_one_summary,
    )

    # Run checks
    results = run_required_checks() if required_only else run_all_checks()
    report  = build_report(results)
    summary = get_nexus_one_summary(report)

    # Store to Supabase (best-effort — table may not exist yet during setup)
    store_results(results)

    # Telegram output
    if not silent:
        text = format_telegram_report(report)
        _send_telegram(text)

    # Also store a Nexus One briefing snapshot
    _store_readiness_briefing(report, summary)

    logger.info(
        f"Readiness check: overall={report['overall']} "
        f"ok={report['ok_count']} degraded={report['degraded_count']} "
        f"blocked={report['blocked_count']} pilot_ready={report['pilot_ready']}"
    )
    return report


def _store_readiness_briefing(report: dict, summary: dict) -> None:
    """Store a structured readiness briefing to executive_briefings."""
    from readiness.readiness_reporter import format_telegram_report
    content  = format_telegram_report(report)
    url_val  = os.getenv('SUPABASE_URL', '')
    key_val  = os.getenv('SUPABASE_KEY', '')
    if not url_val or not key_val:
        return
    try:
        url  = f"{url_val}/rest/v1/executive_briefings"
        row  = {
            'briefing_type': 'readiness',
            'content':       content,
            'urgency':       'critical' if not report.get('pilot_ready') else 'low',
            'generated_by':  'readiness_worker',
        }
        data = json.dumps(row).encode()
        h    = {
            'apikey': key_val, 'Authorization': f'Bearer {key_val}',
            'Content-Type': 'application/json', 'Prefer': 'return=minimal',
        }
        req = urllib.request.Request(url, data=data, headers=h, method='POST')
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass  # Table may not exist yet — not a failure condition during bootstrap


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )

    required_only = '--required-only' in sys.argv
    silent        = '--silent' in sys.argv

    report = run(required_only=required_only, silent=silent)

    # Print compact summary to stdout for manual runs
    print(f"\nReadiness: {report['overall'].upper()}  |  "
          f"Pilot ready: {report['pilot_ready']}")
    print(f"OK: {report['ok_count']}  Degraded: {report['degraded_count']}  "
          f"Blocked: {report['blocked_count']}\n")

    for r in report.get('results', []):
        icon = {'ok': '✅', 'degraded': '🟡', 'blocked': '🔴', 'missing': '🔴'}.get(
            r.get('status', ''), '❓'
        )
        print(f"  {icon}  [{r['integration_key']:20s}] {r['check_key']:20s}  "
              f"{r['status']:10s}  {r['message']}")
