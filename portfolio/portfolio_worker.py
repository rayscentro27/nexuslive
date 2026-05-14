"""
Portfolio Worker.

Cron job that snapshots the portfolio and sends a Telegram briefing.
Also triggers kill/scale analysis when thresholds are hit.

Cron: 0 9 * * *  (daily at 9am, after revenue_worker at 8am)

Run: python3 -m portfolio.portfolio_worker
"""

import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger('PortfolioWorker')


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
    from lib.hermes_gate import send as gate_send

    allowed, _ = should_send_telegram_notification("worker_summary")
    if not allowed:
        return
    gate_send(message, event_type="worker_summary", severity="summary")


def run_portfolio_cycle() -> dict:
    from portfolio.portfolio_service import (
        take_snapshot, get_top_performers, get_underperformers,
        get_portfolio_summary_text,
    )
    from instance_engine.kill_scale_engine import run_kill_scale_analysis

    # 1. Take snapshot
    snapshot = take_snapshot()
    if not snapshot:
        logger.error("Portfolio snapshot failed")
        return {}

    monthly   = snapshot.get('monthly_revenue', 0)
    all_time  = snapshot.get('total_revenue', 0)
    active    = snapshot.get('active_instances', 0)
    testing   = snapshot.get('testing_instances', 0)
    scaled    = snapshot.get('scaled_instances', 0)
    killed    = snapshot.get('killed_instances', 0)
    top       = snapshot.get('top_performers') or []
    under     = snapshot.get('underperformers') or []

    # 2. Format top performers
    top_lines = '\n'.join(
        f"  #{i+1}  {p.get('display_name') or p.get('niche','?')}: <b>${p.get('monthly_rev',0):,.0f}/mo</b>"
        for i, p in enumerate(top[:3])
    ) or '  (no revenue yet)'

    # 3. Format underperformers
    under_lines = '\n'.join(
        f"  ⚠️  {u.get('display_name') or u.get('niche','?')}: ${u.get('monthly_rev',0):,.0f}/mo"
        for u in under[:3]
    ) or '  (all instances performing)'

    message = (
        f"<b>📊 Nexus Portfolio Briefing</b>\n"
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
        f"Monthly Revenue:  <b>${monthly:,.2f}</b>\n"
        f"All-Time Revenue: ${all_time:,.2f}\n\n"
        f"Instances: active={active}  testing={testing}  scaled={scaled}  killed={killed}\n\n"
        f"<b>🏆 Top Performers:</b>\n{top_lines}\n\n"
        f"<b>📉 Underperformers:</b>\n{under_lines}"
    )
    _send_telegram(message)

    # 4. Run kill/scale analysis — generates instance_decisions
    decisions = run_kill_scale_analysis()
    if decisions:
        pending_lines = '\n'.join(
            f"  • [{d.get('decision','?').upper()}] "
            f"{d.get('instance_id','')[:8]}... — {d.get('reason','')}"
            for d in decisions[:5]
        )
        decision_msg = (
            f"<b>⚡ Kill/Scale Decisions Queued: {len(decisions)}</b>\n\n"
            f"{pending_lines}\n\n"
            f"Review and approve in your admin panel."
        )
        _send_telegram(decision_msg)
        logger.info(f"Kill/scale analysis complete: {len(decisions)} decisions queued")

    logger.info(f"Portfolio cycle done: monthly=${monthly} active={active}")
    return snapshot


if __name__ == '__main__':
    _load_env()
    logging.basicConfig(level=logging.INFO)
    result = run_portfolio_cycle()
    print(f"Monthly: ${result.get('monthly_revenue', 0):,.2f}")
    print(f"Active instances: {result.get('active_instances', 0)}")
