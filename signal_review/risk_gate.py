"""
Risk Gate — runs an AI-approved signal through NexusRiskManager,
then sends a Telegram alert and updates Supabase status.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'trading-engine'))
from risk.risk_manager import NexusRiskManager

logger = logging.getLogger('RiskGate')

TELEGRAM_TOKEN   = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
SUPABASE_URL     = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY     = os.getenv('SUPABASE_KEY', '')

# Singleton risk manager (persists daily P&L across signals in the same process)
_risk_manager = None

def get_risk_manager() -> NexusRiskManager:
    global _risk_manager
    if _risk_manager is None:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'trading-engine', 'risk_config.json')
        _risk_manager = NexusRiskManager(config_file=config_path)
    return _risk_manager


def _supabase_patch(table: str, row_id: str, data: dict):
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
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def _html(text: str) -> str:
    """Escape special HTML characters in dynamic content."""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _send_telegram(message: str):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured — skipping alert")
        return
    url  = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    body = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}).encode()
    req  = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            pass
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def run_risk_gate(signal: dict, ai_review: dict) -> dict:
    """
    Apply risk rules to an AI-approved signal.
    Updates Supabase status and sends Telegram alert.

    Returns:
      { 'approved': bool, 'reason': str }
    """
    symbol    = signal.get('symbol', 'UNKNOWN')
    side      = signal.get('side', '').upper()
    timeframe = signal.get('timeframe', '?')
    entry     = signal.get('entry_price', 0)
    sl        = signal.get('stop_loss', 0)
    tp        = signal.get('take_profit', 0)
    conf      = ai_review.get('confidence', 0)
    strategy  = ai_review.get('strategy_match') or signal.get('strategy_id', 'unknown')
    reasoning = ai_review.get('reasoning', '')

    # Calculate R:R
    risk   = abs(entry - sl) if entry and sl else 0
    reward = abs(tp - entry) if tp and entry else 0
    rr     = reward / risk if risk > 0 else 0

    # Run risk manager
    rm = get_risk_manager()
    risk_result = rm.validate_signal({
        'symbol':        symbol,
        'entry_price':   entry,
        'stop_loss':     sl,
        'take_profit':   tp,
        'position_size': 0.01,
    })

    approved  = risk_result.get('approved', False)
    risk_issues = risk_result.get('issues', [])
    daily_pnl   = rm.daily_pnl

    if approved:
        _update_status(signal['id'], 'approved')
        msg = (
            f"🟢 <b>SIGNAL APPROVED</b>\n"
            f"{_html(symbol)} | {_html(side)} | {_html(timeframe)}m\n"
            f"Entry: {_html(entry)} | SL: {_html(sl)} | TP: {_html(tp)}\n"
            f"R:R: 1:{rr:.1f} | Confidence: {conf:.0%}\n"
            f"Strategy: {_html(strategy)}\n"
            f"AI review: {_html(reasoning)}\n"
            f"Risk check: PASSED (daily P&L: ${daily_pnl:+.0f} / limit: -$100)"
        )
        logger.info(f"APPROVED — {symbol} {side} | R:R={rr:.1f} | confidence={conf:.0%}")
    else:
        reason = '; '.join(risk_issues) if risk_issues else 'Risk rule violation'
        _update_status(signal['id'], 'rejected')
        msg = (
            f"🔴 <b>SIGNAL REJECTED</b>\n"
            f"{_html(symbol)} | {_html(side)} | {_html(timeframe)}m\n"
            f"Reason: {_html(reason)}"
        )
        logger.info(f"REJECTED — {symbol} {side} | reason={reason}")

    _send_telegram(msg)
    return {'approved': approved, 'reason': '; '.join(risk_issues) if not approved else 'passed'}


def reject_signal(signal: dict, reason: str):
    """Reject a signal at the AI review stage (before risk check)."""
    symbol    = signal.get('symbol', 'UNKNOWN')
    side      = signal.get('side', '').upper()
    timeframe = signal.get('timeframe', '?')

    _update_status(signal['id'], 'rejected')

    msg = (
        f"🔴 <b>SIGNAL REJECTED</b>\n"
        f"{_html(symbol)} | {_html(side)} | {_html(timeframe)}m\n"
        f"Reason: {_html(reason)}"
    )
    _send_telegram(msg)
    logger.info(f"REJECTED (AI stage) — {symbol} {side} | reason={reason}")


def _update_status(signal_id: str, status: str):
    try:
        _supabase_patch('tv_normalized_signals', signal_id, {'status': status})
    except Exception as e:
        logger.error(f"Failed to update signal status in Supabase: {e}")
