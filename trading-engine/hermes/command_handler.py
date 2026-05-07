"""
hermes/command_handler.py — Telegram command interface via @NexusHermbot.

Polls @NexusHermbot for messages from Ray and dispatches commands
to the live trading engine. Runs as a daemon thread inside the engine.

Commands:
  /status    — engine state, open positions, daily P&L
  /positions — list all open positions with entry prices
  /halt      — pause all signal processing immediately
  /resume    — resume signal processing
  /approve   — approve the last pending signal (override Hermes review)
  /help      — list all commands
"""

import os
import time
import logging
import threading
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

HERMES_TOKEN = os.getenv('HERMES_BOT_TOKEN', '')
CHAT_ID      = os.getenv('TELEGRAM_CHAT_ID', '')
POLL_INTERVAL = int(os.getenv('HERMES_POLL_INTERVAL', '3'))  # seconds

COMMANDS = {
    '/status':    'Engine state, positions, daily P&L',
    '/positions': 'List all open positions',
    '/halt':      'Halt all signal processing',
    '/resume':    'Resume signal processing',
    '/approve':   'Approve the last pending signal',
    '/help':      'Show this help',
}


class HermesCommandHandler:
    """
    Polls @NexusHermbot for commands and dispatches to the trading engine.

    The engine must expose:
        engine.halted          (bool) — set True to pause processing
        engine.active_positions (list)
        engine.pending_signal  (dict | None) — last signal awaiting override
        engine.hermes_override (str | None)  — 'approve' triggers execution
        engine.get_status()    → dict
    """

    def __init__(self, engine):
        self.engine   = engine
        self.token    = HERMES_TOKEN
        self.chat_id  = str(CHAT_ID)
        _explicit = os.getenv('HERMES_COMMANDS_ENABLED', '').lower()
        self.enabled  = bool(self.token and self.chat_id) and _explicit != 'false'
        self.offset   = 0
        self._running = False
        self._thread  = None

        if not self.enabled:
            logger.warning("HermesCommandHandler disabled — HERMES_BOT_TOKEN not set or HERMES_COMMANDS_ENABLED=false")

    # ── Telegram helpers ──────────────────────────────────────────────────────

    def _send(self, text: str):
        if not self.enabled:
            return
        try:
            from lib import hermes_gate
            hermes_gate.send_direct_response(
                text,
                event_type='trading_engine_command_reply',
                bot_token=self.token,
                chat_id=self.chat_id,
                parse_mode='Markdown',
            )
        except Exception:
            pass

    def _get_updates(self) -> list:
        try:
            r = requests.get(
                f'https://api.telegram.org/bot{self.token}/getUpdates',
                params={'offset': self.offset, 'timeout': 10, 'limit': 20},
                timeout=15,
            )
            updates = r.json().get('result', [])
            if updates:
                self.offset = updates[-1]['update_id'] + 1
            return updates
        except Exception:
            return []

    # ── Command handlers ──────────────────────────────────────────────────────

    def _cmd_status(self):
        status = self.engine.get_status()
        risk   = status.get('risk_status', {})
        acct   = status.get('account_info') or {}
        halted = getattr(self.engine, 'halted', False)
        state  = 'HALTED' if halted else 'RUNNING'

        self._send(
            f"*Trading Engine Status*\n"
            f"State: `{state}`\n"
            f"Open positions: `{status['active_positions']}`\n"
            f"Signals processed: `{status['total_signals_processed']}`\n"
            f"Broker: `{'connected' if status['broker_connected'] else 'disconnected'}`\n"
            f"Balance: `${acct.get('balance', 0):,.2f}`\n"
            f"Daily P&L: `${risk.get('daily_pnl', 0):+.2f}`\n"
            f"Risk limit hit: `{risk.get('risk_limit_hit', False)}`"
        )

    def _cmd_positions(self):
        positions = self.engine.active_positions
        if not positions:
            self._send("*No open positions.*")
            return
        lines = [f"*Open Positions ({len(positions)})*"]
        for p in positions:
            lines.append(
                f"- `{p['symbol']}` "
                f"entry: `{p.get('entry_price', '?')}` "
                f"size: `{p.get('position_size', '?')}`"
            )
        self._send('\n'.join(lines))

    def _cmd_halt(self):
        self.engine.halted = True
        self._send("*Trading HALTED.*\nNo new signals will be processed.\nSend /resume to restart.")
        logger.warning("Trading halted via Hermes Telegram command")

    def _cmd_resume(self):
        self.engine.halted = False
        self._send("*Trading RESUMED.*\nEngine is now processing signals.")
        logger.info("Trading resumed via Hermes Telegram command")

    def _cmd_approve(self):
        pending = getattr(self.engine, 'pending_signal', None)
        if not pending:
            self._send("No pending signal to approve.")
            return
        sym    = pending.get('symbol', '?')
        action = pending.get('action', '?').upper()
        self.engine.hermes_override = 'approve'
        self._send(
            f"*Manual Approve* — `{sym} {action}`\n"
            f"Hermes review overridden. Executing trade..."
        )
        logger.info(f"Manual approve via Telegram: {sym} {action}")

    def _cmd_help(self):
        lines = ["*Hermes Trading Commands*"]
        for cmd, desc in COMMANDS.items():
            lines.append(f"`{cmd}` — {desc}")
        self._send('\n'.join(lines))

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, text: str):
        cmd = text.strip().split()[0].lower()
        dispatch = {
            '/status':    self._cmd_status,
            '/positions': self._cmd_positions,
            '/halt':      self._cmd_halt,
            '/resume':    self._cmd_resume,
            '/approve':   self._cmd_approve,
            '/help':      self._cmd_help,
        }
        handler = dispatch.get(cmd)
        if handler:
            handler()
        else:
            self._send(
                f"Unknown command: `{cmd}`\n"
                f"Send /help for available commands."
            )

    # ── Poll loop ─────────────────────────────────────────────────────────────

    def _poll_loop(self):
        logger.info("Hermes command handler polling @NexusHermbot")
        while self._running:
            # Re-read env var each cycle so disabling via .env takes effect immediately
            if os.getenv('HERMES_COMMANDS_ENABLED', '').lower() == 'false':
                logger.info("HERMES_COMMANDS_ENABLED=false detected — stopping command handler")
                self._running = False
                break
            try:
                updates = self._get_updates()
                for update in updates:
                    msg = update.get('message') or update.get('edited_message')
                    if not msg:
                        continue
                    # Only accept from the configured chat
                    if str(msg.get('chat', {}).get('id')) != self.chat_id:
                        continue
                    text = msg.get('text', '')
                    if text.startswith('/'):
                        logger.info(f"Hermes command: {text.strip()}")
                        self._dispatch(text)
            except Exception as e:
                logger.error(f"Command handler poll error: {e}")
            time.sleep(POLL_INTERVAL)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        """Start command polling in a daemon thread."""
        if not self.enabled:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop, daemon=True, name='HermesCommands'
        )
        self._thread.start()

    def stop(self):
        self._running = False
