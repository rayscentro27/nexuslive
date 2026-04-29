#!/usr/bin/env python3
"""
Nexus Telegram Integration
Real-time trading alerts and system monitoring via Telegram
"""

import os
import json
import requests
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from html import escape
import subprocess
import time

# optionally load .env file for credentials
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, environment variables still work
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram-integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TelegramIntegration')
UPDATE_OFFSET_FILE = os.path.join(os.path.dirname(__file__), ".telegram_update_offset")
COORD_CLI = os.path.join(os.path.dirname(__file__), "nexus_coord.py")
OPS_SNAPSHOT = os.path.join(os.path.dirname(__file__), "scripts", "hermes_ops_snapshot.sh")
OPS_ATTENTION = os.path.join(os.path.dirname(__file__), "scripts", "hermes_ops_attention.sh")
SCHEDULER_SCRIPT = os.path.join(os.path.dirname(__file__), "operations_center", "scheduler.py")


def email_summaries_enabled() -> bool:
    return os.getenv("TELEGRAM_EMAIL_SUMMARIES_ENABLED", "false").lower() == "true"

class NexusTelegramBot:
    """Telegram bot for Nexus AI trading alerts and system monitoring"""

    def __init__(self, config_file: str = "telegram_config.json"):
        self.config = self.load_config(config_file)
        # environment variables take precedence (after .env loading)
        self.bot_token = os.getenv('NEXUS_ONE_BOT_TOKEN', self.config.get('bot_token', 'YOUR_TELEGRAM_BOT_TOKEN'))
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', self.config.get('chat_id', 'YOUR_CHAT_ID'))
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.connected = False
        self.last_update_id = self.load_update_offset()

        if self.bot_token != 'YOUR_TELEGRAM_BOT_TOKEN':
            self.test_connection()
        else:
            logger.warning("⚠️ Telegram credentials not configured")

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load Telegram configuration"""
        default_config = {
            'bot_token': 'YOUR_TELEGRAM_BOT_TOKEN',
            'chat_id': 'YOUR_CHAT_ID',
            'enabled': False,
            'alert_level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
            'include_charts': True,
            'include_metrics': True
        }

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.error(f"Error loading config: {e}")

        return default_config

    def load_update_offset(self) -> int:
        try:
            with open(UPDATE_OFFSET_FILE, 'r', encoding='utf-8') as f:
                return int(f.read().strip() or "0")
        except Exception:
            return 0

    def save_update_offset(self) -> None:
        try:
            with open(UPDATE_OFFSET_FILE, 'w', encoding='utf-8') as f:
                f.write(str(self.last_update_id))
        except Exception as e:
            logger.warning(f"Could not save Telegram update offset: {e}")

    def test_connection(self) -> bool:
        """Test Telegram bot connection"""
        try:
            response = requests.get(f"{self.api_url}/getMe", timeout=5)
            if response.status_code == 200:
                self.connected = True
                bot_info = response.json()['result']
                logger.info(f"✅ Telegram connected: @{bot_info['username']}")
                return True
            else:
                logger.error(f"❌ Telegram connection failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Telegram connection error: {e}")
            return False

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        if not self.connected:
            logger.warning("Telegram not connected")
            return False

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode
            }

            response = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)

            if response.status_code == 200:
                logger.debug(f"📤 Message sent to Telegram")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_email_summary(self, subject: str, body: str) -> None:
        if not email_summaries_enabled():
            return
        try:
            from notifications.operator_notifications import send_operator_email
            sent, detail = send_operator_email(subject, body)
            if not sent:
                logger.warning(f"Email summary skipped/failed: {detail}")
        except Exception as e:
            logger.warning(f"Email summary error: {e}")

    def get_updates(self, timeout: int = 20) -> list[dict]:
        if not self.connected:
            return []

        params = {
            "timeout": timeout,
            "allowed_updates": ["message"],
        }
        if self.last_update_id:
            params["offset"] = self.last_update_id + 1

        try:
            response = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=timeout + 5)
            if response.status_code != 200:
                logger.warning(f"Telegram getUpdates failed: {response.status_code} {response.text[:200]}")
                return []
            payload = response.json()
            return payload.get("result", [])
        except Exception as e:
            logger.warning(f"Telegram polling error: {e}")
            return []

    def run_coord_cli(self, *args: str) -> str:
        try:
            proc = subprocess.run(
                ["python3", COORD_CLI, *args],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=os.path.dirname(__file__),
            )
            output = (proc.stdout or "").strip()
            error = (proc.stderr or "").strip()
            if proc.returncode != 0:
                return error or output or f"coordination command failed ({proc.returncode})"
            return output or "OK"
        except Exception as e:
            return f"coordination command failed: {e}"

    def format_pre(self, text: str) -> str:
        return f"<pre>{escape(text[:3500])}</pre>"

    def run_local_command(self, *args: str, timeout: int = 30) -> str:
        try:
            proc = subprocess.run(
                list(args),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(__file__),
            )
            output = (proc.stdout or "").strip()
            error = (proc.stderr or "").strip()
            if proc.returncode != 0:
                return error or output or f"command failed ({proc.returncode})"
            return output or "OK"
        except Exception as e:
            return f"command failed: {e}"

    def handle_coordination_command(self, text: str) -> Optional[str]:
        raw = text.strip()
        normalized = raw.lower().strip()

        if normalized in {"status", "ops snapshot", "give me an ops snapshot", "summarize system health"}:
            return self.format_pre(self.run_local_command(OPS_SNAPSHOT, timeout=60))

        if normalized in {"what needs attention", "needs attention", "attention"}:
            return self.format_pre(self.run_local_command(OPS_ATTENTION, timeout=60))

        if normalized in {"show activity", "activity"}:
            return self.format_pre(self.run_coord_cli("activity", "--limit", "8"))

        if normalized in {"coordination summary", "show coordination summary", "summary"}:
            return self.format_pre(self.run_coord_cli("summary"))

        if normalized.startswith("show tasks for "):
            agent = raw.split("for ", 1)[1].strip()
            return self.format_pre(self.run_coord_cli("tasks", agent))

        if normalized in {"show pending tasks", "show tasks", "pending tasks"}:
            return self.format_pre(self.run_coord_cli("tasks", "hermes"))

        if normalized in {"run lead check", "lead check"}:
            return self.format_pre(self.run_local_command("python3", SCHEDULER_SCRIPT, "--run-now", "leads", timeout=60))

        if normalized in {"run reputation check", "reputation check"}:
            return self.format_pre(self.run_local_command("python3", SCHEDULER_SCRIPT, "--run-now", "reputation", timeout=60))

        if normalized.startswith("assign task to "):
            target_part = raw[len("assign task to "):]
            if ":" not in target_part:
                return "Use: <code>assign task to codex: description</code>"
            agent, description = target_part.split(":", 1)
            agent = agent.strip()
            description = description.strip()
            if not description:
                return "Task description cannot be empty."
            return self.format_pre(self.run_coord_cli("add-task", agent, description, "--posted-by", "hermes"))

        if normalized in {"/coord", "/coord-help", "coord help", "coordination help"}:
            return (
                "<b>Coordination Commands</b>\n\n"
                "<code>status</code>\n"
                "<code>what needs attention</code>\n"
                "<code>show pending tasks</code>\n"
                "<code>run lead check</code>\n"
                "<code>run reputation check</code>\n"
                "<code>show activity</code>\n"
                "<code>coordination summary</code>\n"
                "<code>show tasks for codex</code>\n"
                "<code>assign task to codex: review launchd runtime</code>\n"
                "<code>assign task to claude: update docs</code>\n\n"
                "<b>CEO Auto-Routing</b>\n"
                "<code>/route &lt;task&gt;</code> — Route a task to the right AI employee\n"
                "Example: <code>/route create a TikTok script about business credit</code>"
            )

        # ── CEO Auto-Routing ─────────────────────────────────────────────────
        if normalized.startswith("/route "):
            task = raw[len("/route "):].strip()
            if not task:
                return "Usage: <code>/route &lt;your task description&gt;</code>"
            return self._submit_ceo_route(task)

        # ── Browser Worker commands ──────────────────────────────────────────
        if normalized in {"browser help", "/browser", "/browser help"}:
            return (
                "<b>Browser Worker Commands</b>\n\n"
                "<code>browser oracle</code> — OCI ARM instance status\n"
                "<code>browser stripe</code> — Stripe webhook + events\n"
                "<code>browser nexuslive</code> — Nexuslive site health\n"
                "<code>browser supabase</code> — Supabase table health\n"
                "<code>browser tasks</code> — Recent task history\n"
                "<code>browser do: &lt;task&gt;</code> — Free-form browser task\n\n"
                "Tasks run async — results arrive in ~30s."
            )

        if normalized in {"browser oracle", "/browser oracle"}:
            return self._enqueue_browser_task("oracle_check")

        if normalized in {"browser stripe", "/browser stripe"}:
            return self._enqueue_browser_task("stripe_check")

        if normalized in {"browser nexuslive", "/browser nexuslive"}:
            return self._enqueue_browser_task("nexuslive_check")

        if normalized in {"browser supabase", "/browser supabase"}:
            return self._enqueue_browser_task("supabase_check")

        if normalized in {"browser tasks", "browser status"}:
            return self._browser_task_status()

        if normalized.startswith("browser do:"):
            task_desc = raw[len("browser do:"):].strip()
            if not task_desc:
                return "Usage: <code>browser do: describe what to do</code>"
            return self._enqueue_browser_task("open", payload={"task": task_desc})

        return None

    def _enqueue_browser_task(self, task_type: str, payload: dict = None) -> str:
        """Insert a browser task into the queue and confirm."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from browser_worker.task_queue import enqueue_task
            task = enqueue_task(task_type, payload or {}, requested_by="telegram")
            if task:
                return f"🌐 Browser task queued: <b>{task_type}</b> (id={task['id']})\nResult will arrive shortly."
            return f"⚠️ Failed to queue browser task — check Supabase connection"
        except Exception as e:
            return f"⚠️ Browser task error: {e}"

    def _browser_task_status(self) -> str:
        try:
            from browser_worker.task_queue import get_recent_tasks
            tasks = get_recent_tasks(limit=8)
            if not tasks:
                return "No browser tasks found."
            lines = ["<b>Recent Browser Tasks:</b>"]
            for t in tasks:
                ts = (t.get("created_at") or "")[:16].replace("T", " ")
                icon = {"done": "✅", "error": "❌", "running": "⏳", "pending": "🕐"}.get(t.get("status"), "?")
                lines.append(f"{icon} [{ts}] {t['task_type']:<18} {t.get('status','?')}")
            return "\n".join(lines)
        except Exception as e:
            return f"⚠️ Status fetch failed: {e}"

    def _submit_ceo_route(self, task: str) -> str:
        """Submit a task to the CEO auto-routing pipeline."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from lib.event_intake import submit_ceo_route_request
            result = submit_ceo_route_request(
                message=task,
                source="telegram",
                channel="bot",
            )
            if "error" in result:
                return f"⚠️ CEO routing failed: {result['error']}"
            return (
                f"✅ <b>Task submitted for CEO routing</b>\n"
                f"Event ID: <code>{result.get('event_id', '—')}</code>\n"
                f"Status: <b>pending</b>\n\n"
                f"The CEO will classify this and assign it to the right AI employee. "
                f"Draft will appear in workflow_outputs for review."
            )
        except Exception as e:
            return f"⚠️ CEO routing error: {e}"

    def handle_update(self, update: dict) -> None:
        update_id = update.get("update_id")
        if update_id is not None and update_id > self.last_update_id:
            self.last_update_id = update_id

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        if str(self.chat_id) != chat_id:
            return

        text = (message.get("text") or "").strip()
        if not text:
            return

        response = self.handle_coordination_command(text)
        if response:
            self.send_message(response)

    def poll_commands_once(self) -> None:
        updates = self.get_updates()
        if not updates:
            return
        for update in updates:
            self.handle_update(update)
        self.save_update_offset()

    def alert_signal(self, signal: Dict[str, Any]) -> bool:
        """Alert on new trading signal"""
        message = f"""
<b>📈 TRADING SIGNAL</b>

<b>Symbol:</b> {signal.get('symbol', 'N/A')}
<b>Action:</b> {signal.get('action', 'N/A')}
<b>Entry:</b> {signal.get('entry_price', 'Market')}
<b>Confidence:</b> {signal.get('confidence', 'N/A')}%

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            f"Nexus Trading Signal — {signal.get('symbol', 'N/A')}",
            json.dumps(signal, indent=2, default=str),
        )
        return self.send_message(message)

    def alert_trade_execution(self, trade: Dict[str, Any]) -> bool:
        """Alert on trade execution"""
        message = f"""
<b>✅ TRADE EXECUTED</b>

<b>Symbol:</b> {trade.get('symbol', 'N/A')}
<b>Action:</b> {trade.get('action', 'N/A')}
<b>Entry Price:</b> {trade.get('entry_price', 'N/A')}
<b>Position Size:</b> {trade.get('position_size', 'N/A')}
<b>Order ID:</b> <code>{trade.get('order_id', 'N/A')}</code>
<b>Broker:</b> {trade.get('broker', 'N/A')}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            f"Nexus Trade Executed — {trade.get('symbol', 'N/A')}",
            json.dumps(trade, indent=2, default=str),
        )
        return self.send_message(message)

    def alert_position_closed(self, position: Dict[str, Any]) -> bool:
        """Alert on position closure"""
        pnl = position.get('pnl', 0)
        pnl_emoji = "💰" if pnl > 0 else "📉"

        message = f"""
<b>{pnl_emoji} POSITION CLOSED</b>

<b>Symbol:</b> {position.get('symbol', 'N/A')}
<b>Exit Price:</b> {position.get('exit_price', 'N/A')}
<b>P&L:</b> <b>${pnl:.2f}</b>
<b>Reason:</b> {position.get('reason', 'N/A')}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            f"Nexus Position Closed — {position.get('symbol', 'N/A')}",
            json.dumps(position, indent=2, default=str),
        )
        return self.send_message(message)

    def alert_risk_warning(self, warning: Dict[str, Any]) -> bool:
        """Alert on risk warnings"""
        message = f"""
<b>⚠️ RISK WARNING</b>

<b>Type:</b> {warning.get('type', 'N/A')}
<b>Message:</b> {warning.get('message', 'N/A')}
<b>Current Status:</b>
  • Daily P&L: ${warning.get('daily_pnl', 0):.2f}
  • Open Positions: {warning.get('open_positions', 0)}
  • Max Allowed: {warning.get('max_allowed', 'N/A')}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            f"Nexus Risk Warning — {warning.get('type', 'N/A')}",
            json.dumps(warning, indent=2, default=str),
        )
        return self.send_message(message)

    def alert_system_status(self, status: Dict[str, Any]) -> bool:
        """Alert on system status"""
        message = f"""
<b>🤖 SYSTEM STATUS</b>

<b>Status:</b> {status.get('status', 'Unknown')}
<b>Hermes:</b> {'✅ Connected' if status.get('hermes_connected') else '❌ Disconnected'}
<b>Broker:</b> {'✅ Connected' if status.get('broker_connected') else '❌ Disconnected'}
<b>Signals Processed:</b> {status.get('signals_processed', 0)}
<b>Active Positions:</b> {status.get('active_positions', 0)}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            "Nexus System Status",
            json.dumps(status, indent=2, default=str),
        )
        return self.send_message(message)

    def alert_research_complete(self, research: Dict[str, Any]) -> bool:
        """Alert on research pipeline completion"""
        message = f"""
<b>📊 RESEARCH COMPLETE</b>

<b>Strategies Found:</b> {research.get('strategies_found', 0)}
<b>Videos Analyzed:</b> {research.get('videos_analyzed', 0)}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        self.send_email_summary(
            "Nexus Research Complete",
            json.dumps(research, indent=2, default=str),
        )
        return self.send_message(message)

    def send_dashboard_link(self) -> bool:
        """Send dashboard access link"""
        dashboard_url = os.getenv('NEXUS_DASHBOARD_URL', 'http://localhost:3000')
        message = f"""
<b>📈 NEXUS DASHBOARD</b>

Access your real-time trading dashboard:
<a href="{dashboard_url}">🔗 Open Dashboard</a>

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
        return self.send_message(message)

def monitor():
    """
    Long-running monitor mode — used by launchd to keep the Telegram
    integration alive. Sends a startup notification, then pings every
    5 minutes so launchd has a persistent process to watch.
    """
    import signal as _signal

    bot = NexusTelegramBot()
    running = True

    def _shutdown(sig, frame):
        nonlocal running
        logger.info("Telegram monitor received shutdown signal")
        running = False

    _signal.signal(_signal.SIGTERM, _shutdown)
    _signal.signal(_signal.SIGINT, _shutdown)

    if bot.connected:
        bot.send_message(
            "<b>🟢 Nexus Telegram Monitor Started</b>\n"
            "<i>Nexus stack is online. Signal alerts are active.</i>"
        )
        logger.info("Telegram monitor running — heartbeat every 300s")
    else:
        logger.error("Telegram not connected — monitor will retry on each heartbeat")

    HEARTBEAT_INTERVAL = 300  # 5 minutes
    last_heartbeat = 0.0
    while running:
        try:
            bot.poll_commands_once()
        except Exception as e:
            logger.warning(f"Telegram command poll error: {e}")

        now = time.time()
        if now - last_heartbeat >= HEARTBEAT_INTERVAL:
            last_heartbeat = now
            try:
                bot.test_connection()
                logger.info(f"Telegram heartbeat OK — connected={bot.connected}")
            except Exception as e:
                logger.warning(f"Telegram heartbeat error: {e}")

    logger.info("Telegram monitor stopped")


def main():
    """Entry point — run test mode by default, --monitor for daemon mode."""
    import argparse
    parser = argparse.ArgumentParser(description='Nexus Telegram Bot')
    parser.add_argument(
        '--monitor', action='store_true',
        help='Run as long-lived monitor daemon (used by launchd)'
    )
    args = parser.parse_args()

    if args.monitor:
        monitor()
        return

    # Default: one-shot test (original behaviour)
    bot = NexusTelegramBot()

    if bot.connected:
        logger.info("🧪 Testing Telegram alerts...")

        test_signal = {
            'symbol': 'EURUSD',
            'action': 'BUY',
            'entry_price': 1.0500,
            'stop_loss': 1.0450,
            'take_profit': 1.0600,
            'confidence': 85
        }
        bot.alert_signal(test_signal)

        test_status = {
            'status': '🟢 Operational',
            'hermes_connected': True,
            'broker_connected': True,
            'signals_processed': 1,
            'active_positions': 0
        }
        bot.alert_system_status(test_status)
    else:
        logger.error("Cannot test - Telegram not connected")


if __name__ == "__main__":
    main()
