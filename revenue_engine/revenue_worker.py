"""
Revenue Worker.

Cron job that aggregates revenue signals from system events and
sends a daily revenue summary via Telegram.

Cron: 0 8 * * *  (daily at 8am)

Run: python3 -m revenue_engine.revenue_worker
"""

import os
import json
import logging
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger('RevenueWorker')


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
        body = json.dumps({'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}).encode()
        req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning(f"Telegram send failed: {e}")


def _collect_funding_fees() -> None:
    """
    Pull funded amounts from conversion_events and record success fees.
    10% fee on funded amounts.
    """
    from revenue_engine.revenue_service import record_revenue

    key = os.getenv('SUPABASE_KEY', '')
    url = (
        f"{os.getenv('SUPABASE_URL', '')}/rest/v1/conversion_events"
        f"?event_type=eq.funded&select=lead_id,amount,created_at"
        f"&order=created_at.desc&limit=200"
    )
    req = urllib.request.Request(
        url, headers={'apikey': key, 'Authorization': f'Bearer {key}'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            events = json.loads(r.read())
        for ev in events:
            amount = float(ev.get('amount') or 0)
            if amount > 0:
                fee = round(amount * 0.10, 2)
                record_revenue(stream_type='funding_fee', amount=fee, transactions=1)
    except Exception as e:
        logger.warning(f"Funding fee collection error: {e}")


def _collect_subscription_revenue() -> None:
    """Placeholder — hook into subscription billing events when live."""
    pass


def run_revenue_summary() -> dict:
    """Compute and broadcast daily revenue summary."""
    from revenue_engine.revenue_service import (
        get_monthly_total, get_all_time_total,
        get_revenue_by_stream, get_top_revenue_instances,
    )

    period          = datetime.now(timezone.utc).strftime('%Y-%m')
    monthly_total   = get_monthly_total(period=period)
    all_time_total  = get_all_time_total()
    by_stream       = get_revenue_by_stream(period=period)
    top_instances   = get_top_revenue_instances(period=period, limit=3)

    stream_lines = '\n'.join(
        f"  • {st}: ${rev:,.2f}"
        for st, rev in sorted(by_stream.items(), key=lambda x: x[1], reverse=True)
    ) or '  (no streams recorded)'

    top_lines = '\n'.join(
        f"  #{i+1}  {row['instance_id'][:8]}...  ${row['revenue']:,.2f}"
        for i, row in enumerate(top_instances)
    ) or '  (no instances)'

    message = (
        f"<b>💰 Nexus Revenue — {period}</b>\n\n"
        f"Monthly:   <b>${monthly_total:,.2f}</b>\n"
        f"All-time:  ${all_time_total:,.2f}\n\n"
        f"<b>By stream:</b>\n{stream_lines}\n\n"
        f"<b>Top instances:</b>\n{top_lines}"
    )
    _send_telegram(message)
    logger.info(f"Revenue summary sent: monthly=${monthly_total}")

    return {
        'period':         period,
        'monthly_total':  monthly_total,
        'all_time_total': all_time_total,
        'by_stream':      by_stream,
    }


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(level=logging.INFO)
    _collect_funding_fees()
    _collect_subscription_revenue()
    summary = run_revenue_summary()
    print(f"Monthly revenue: ${summary['monthly_total']:,.2f}")
    print(f"All-time revenue: ${summary['all_time_total']:,.2f}")
