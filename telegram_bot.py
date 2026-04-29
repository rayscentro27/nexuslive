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
from typing import Optional, Dict, Any, Callable
from html import escape
import subprocess
import time
import threading
import concurrent.futures
from collections import deque

try:
    import fcntl
except ImportError:  # pragma: no cover - non-posix fallback
    fcntl = None

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
SINGLE_INSTANCE_LOCK = os.path.join(os.path.dirname(__file__), ".telegram_bot.lock")
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
        self.bot_token = (
            os.getenv('TELEGRAM_INBOUND_BOT_TOKEN')
            or os.getenv('NEXUS_ONE_BOT_TOKEN')
            or os.getenv('HERMES_BOT_TOKEN')
            or self.config.get('bot_token', 'YOUR_TELEGRAM_BOT_TOKEN')
        )
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', self.config.get('chat_id', 'YOUR_CHAT_ID'))
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.connected = False
        self.last_update_id = self.load_update_offset()
        self.max_response_chars = int(os.getenv("TELEGRAM_MAX_RESPONSE_CHARS", "1800"))
        self.max_inbound_chars = int(os.getenv("TELEGRAM_MAX_INBOUND_CHARS", "280"))
        self.command_timeout_seconds = float(os.getenv("TELEGRAM_COMMAND_TIMEOUT_SECONDS", "12"))
        self.cooldown_seconds = float(os.getenv("TELEGRAM_COMMAND_COOLDOWN_SECONDS", "3"))
        self.circuit_breaker_window_seconds = float(os.getenv("TELEGRAM_CIRCUIT_BREAKER_WINDOW_SECONDS", "60"))
        self.circuit_breaker_error_threshold = int(os.getenv("TELEGRAM_CIRCUIT_BREAKER_ERROR_THRESHOLD", "5"))
        self.circuit_breaker_open_seconds = float(os.getenv("TELEGRAM_CIRCUIT_BREAKER_OPEN_SECONDS", "60"))
        self.allow_mutating_commands = os.getenv("TELEGRAM_ALLOW_MUTATING_COMMANDS", "false").lower() == "true"
        self.allow_webhook_takeover = os.getenv("TELEGRAM_DELETE_WEBHOOK_ON_START", "false").lower() == "true"
        self.recent_update_ids: deque[int] = deque(maxlen=200)
        self.chat_cooldowns: dict[str, float] = {}
        self.error_timestamps: deque[float] = deque(maxlen=50)
        self.circuit_open_until = 0.0
        self._lock_handle = None

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

    def acquire_single_instance_lock(self) -> bool:
        if fcntl is None:
            return True
        try:
            self._lock_handle = open(SINGLE_INSTANCE_LOCK, "w", encoding="utf-8")
            fcntl.flock(self._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._lock_handle.write(str(os.getpid()))
            self._lock_handle.flush()
            return True
        except OSError:
            logger.error("Telegram monitor already running; refusing duplicate polling instance")
            return False

    def get_webhook_info(self) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.api_url}/getWebhookInfo", timeout=5)
            if response.status_code != 200:
                return {"ok": False, "status_code": response.status_code}
            payload = response.json()
            return payload.get("result") or {}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def ensure_polling_ready(self) -> bool:
        info = self.get_webhook_info()
        webhook_url = str(info.get("url") or "").strip()
        if not webhook_url:
            return True
        if self.allow_webhook_takeover:
            try:
                response = requests.post(
                    f"{self.api_url}/deleteWebhook",
                    json={"drop_pending_updates": False},
                    timeout=10,
                )
                if response.status_code == 200:
                    logger.warning("Deleted Telegram webhook so polling can own inbound commands")
                    return True
            except Exception as e:
                logger.error(f"Failed to delete Telegram webhook: {e}")
            return False
        logger.warning(
            "Webhook is active for this bot token; polling disabled to avoid 409 conflicts. "
            "Set TELEGRAM_DELETE_WEBHOOK_ON_START=true to let telegram_bot.py take over inbound polling."
        )
        return False

    def _truncate_response(self, text: str) -> str:
        text = text or ""
        if len(text) <= self.max_response_chars:
            return text
        return text[: self.max_response_chars - 16].rstrip() + "\n\n(truncated)"

    def _structured_log(
        self,
        *,
        update_id: int | None,
        chat_id: str | None,
        command: str,
        duration_ms: int,
        status: str,
        error_message: str | None = None,
    ) -> None:
        payload = {
            "update_id": update_id,
            "chat_id": chat_id,
            "command": command,
            "duration_ms": duration_ms,
            "status": status,
        }
        if error_message:
            payload["error_message"] = error_message[:240]
        logger.info("telegram_command %s", json.dumps(payload, sort_keys=True))

    def _record_error(self) -> None:
        now = time.time()
        self.error_timestamps.append(now)
        cutoff = now - self.circuit_breaker_window_seconds
        while self.error_timestamps and self.error_timestamps[0] < cutoff:
            self.error_timestamps.popleft()
        if len(self.error_timestamps) >= self.circuit_breaker_error_threshold:
            self.circuit_open_until = now + self.circuit_breaker_open_seconds
            logger.error(
                "Telegram circuit breaker opened for %.0fs after %s recent errors",
                self.circuit_breaker_open_seconds,
                len(self.error_timestamps),
            )

    def _circuit_open(self) -> bool:
        return time.time() < self.circuit_open_until

    def execute_with_timeout(self, func: Callable[[], str]) -> tuple[bool, str]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(func)
            try:
                result = future.result(timeout=self.command_timeout_seconds)
                return True, str(result or "")
            except concurrent.futures.TimeoutError:
                return False, "Command timed out. Try again in a moment."
            except Exception as e:
                return False, f"Command failed: {e}"

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        if not self.connected:
            logger.warning("Telegram not connected")
            return False

        try:
            payload = {
                "chat_id": self.chat_id,
                "text": self._truncate_response(message),
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
                if response.status_code == 409:
                    self._record_error()
                logger.warning(f"Telegram getUpdates failed: {response.status_code} {response.text[:200]}")
                return []
            payload = response.json()
            return payload.get("result", [])
        except Exception as e:
            self._record_error()
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

    def latest_stored_brief(self) -> str:
        try:
            from scripts.prelaunch_utils import rest_select

            rows = rest_select(
                "executive_briefings?select=briefing_type,content,urgency,generated_by,created_at"
                "&order=created_at.desc&limit=1",
                timeout=8,
            ) or []
        except Exception as e:
            return f"Latest stored brief unavailable: {e}"

        if not rows:
            return "No stored Hermes brief found yet."

        row = rows[0]
        content = str(row.get("content") or "").strip()
        header = (
            f"Latest stored brief\n"
            f"type={row.get('briefing_type') or 'unknown'} | "
            f"urgency={row.get('urgency') or 'unknown'} | "
            f"by={row.get('generated_by') or 'unknown'} | "
            f"at={row.get('created_at') or 'unknown'}\n\n"
        )
        return header + (content or "Brief content is empty.")

    def safe_status_summary(self) -> str:
        try:
            from scripts.prelaunch_utils import list_launchd, pgrep_lines, probe_port
        except Exception as e:
            return f"Status unavailable: {e}"

        telegram_processes = pgrep_lines("telegram_bot.py|hermes_status_bot.py|hermes_claude_bot.py")
        scheduler_running = bool(pgrep_lines("operations_center/scheduler.py"))
        lines = [
            "Nexus status",
            f"control_center={'up' if probe_port('127.0.0.1', 4000) else 'down'}",
            f"hermes_gateway={'up' if probe_port('127.0.0.1', 8642) else 'down'}",
            f"scheduler={'up' if scheduler_running else 'down'}",
            f"telegram_processes={len(telegram_processes)}",
            f"launchd_matches={len(list_launchd())}",
        ]
        return "\n".join(lines)

    def safe_health_summary(self) -> str:
        output = self.run_local_command("python3", os.path.join(os.path.dirname(__file__), "scripts", "backend_health_report.py"), timeout=15)
        try:
            payload = json.loads(output)
            services = payload.get("services") or {}
            supabase = payload.get("supabase") or {}
            lines = [
                "Nexus health",
                f"control_center={services.get('control_center')}",
                f"netcup_ollama_tunnel={services.get('netcup_ollama_tunnel')}",
                f"scheduler_processes={len(services.get('scheduler_processes') or [])}",
                f"telegram_processes={len(services.get('telegram_processes') or [])}",
                f"job_queue_total={supabase.get('job_queue_total', 0)}",
                f"worker_heartbeats_total={supabase.get('worker_heartbeats_total', 0)}",
            ]
            return "\n".join(lines)
        except Exception:
            return output

    def safe_jobs_summary(self) -> str:
        try:
            from scripts.prelaunch_utils import count_by, count_rows
            by_status = count_by("job_queue", "status")
            lines = [
                "Queue summary",
                f"job_queue_total={count_rows('job_queue')}",
                f"workflow_outputs_total={count_rows('workflow_outputs')}",
            ]
            for status, count in list(by_status.items())[:6]:
                lines.append(f"{status}={count}")
            return "\n".join(lines)
        except Exception as e:
            return f"Queue summary unavailable: {e}"

    def safe_workers_summary(self) -> str:
        try:
            from scripts.prelaunch_utils import count_rows, rest_select
            rows = rest_select(
                "worker_heartbeats?select=worker_id,worker_type,status,last_seen_at"
                "&order=last_seen_at.desc&limit=8",
                timeout=8,
            ) or []
        except Exception as e:
            return f"Worker summary unavailable: {e}"

        lines = [
            "Worker summary",
            f"worker_heartbeats_total={count_rows('worker_heartbeats')}",
        ]
        for row in rows[:5]:
            lines.append(
                f"{row.get('worker_id') or row.get('worker_type')}: "
                f"{row.get('status') or 'unknown'} | {row.get('last_seen_at') or 'unknown'}"
            )
        return "\n".join(lines)

    def safe_help_text(self) -> str:
        return (
            "Safe commands\n"
            "status\n"
            "health\n"
            "jobs\n"
            "workers\n"
            "brief\n"
            "help\n\n"
            "Notes\n"
            "- basic commands do not call an LLM\n"
            "- unknown or long messages are rejected safely\n"
            "- expensive workflows are disabled by default"
        )

    def parse_command(self, text: str) -> tuple[str, str]:
        raw = text.strip()
        normalized = raw.lower().strip()
        mapping = {
            "status": "status",
            "/status": "status",
            "health": "health",
            "/health": "health",
            "jobs": "jobs",
            "/jobs": "jobs",
            "workers": "workers",
            "/workers": "workers",
            "help": "help",
            "/help": "help",
            "brief": "brief",
            "/brief": "brief",
        }
        return mapping.get(normalized, "unknown"), raw

    def handle_basic_command(self, command: str) -> str:
        handlers: dict[str, Callable[[], str]] = {
            "status": self.safe_status_summary,
            "health": self.safe_health_summary,
            "jobs": self.safe_jobs_summary,
            "workers": self.safe_workers_summary,
            "help": self.safe_help_text,
            "brief": self.latest_stored_brief,
        }
        handler = handlers.get(command)
        if not handler:
            return self.safe_help_text()
        return handler()

    def handle_coordination_command(self, text: str) -> Optional[str]:
        raw = text.strip()
        normalized = raw.lower().strip()

        basic_command, _ = self.parse_command(text)
        if basic_command != "unknown":
            return self.format_pre(self.handle_basic_command(basic_command))

        if len(raw) > self.max_inbound_chars:
            return "Message too long for Telegram command mode. Send `help` for safe commands."

        if normalized in {"what needs attention", "needs attention", "attention"}:
            return self.format_pre(self.run_local_command(OPS_ATTENTION, timeout=15))

        if normalized in {"show pending tasks", "show tasks", "pending tasks"}:
            return self.format_pre(self.run_coord_cli("tasks", "hermes"))

        if normalized in {"show activity", "activity"}:
            return self.format_pre(self.run_coord_cli("activity", "--limit", "8"))

        if normalized in {"/coord", "/coord-help", "coord help", "coordination help"}:
            return self.format_pre(self.safe_help_text())

        if not self.allow_mutating_commands:
            return self.safe_help_text()

        if normalized in {"run lead check", "lead check"}:
            return self.format_pre(self.run_local_command("python3", SCHEDULER_SCRIPT, "--run-now", "leads", timeout=20))

        if normalized in {"run reputation check", "reputation check"}:
            return self.format_pre(self.run_local_command("python3", SCHEDULER_SCRIPT, "--run-now", "reputation", timeout=20))

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

        return self.safe_help_text()

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
        started = time.time()
        update_id = update.get("update_id")
        if update_id is not None:
            if update_id in self.recent_update_ids:
                self._structured_log(
                    update_id=update_id,
                    chat_id=None,
                    command="duplicate",
                    duration_ms=int((time.time() - started) * 1000),
                    status="duplicate_ignored",
                )
                return
            self.recent_update_ids.append(update_id)
            if update_id > self.last_update_id:
                self.last_update_id = update_id

        message = update.get("message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        sender = message.get("from") or {}
        if sender.get("is_bot"):
            self._structured_log(
                update_id=update_id,
                chat_id=chat_id,
                command="bot_message",
                duration_ms=int((time.time() - started) * 1000),
                status="self_ignored",
            )
            return
        if str(self.chat_id) != chat_id:
            return

        text = (message.get("text") or "").strip()
        if not text:
            return
        command, _ = self.parse_command(text)

        if self._circuit_open():
            self._structured_log(
                update_id=update_id,
                chat_id=chat_id,
                command=command,
                duration_ms=int((time.time() - started) * 1000),
                status="circuit_open",
            )
            return

        cooldown_until = self.chat_cooldowns.get(chat_id, 0.0)
        if time.time() < cooldown_until:
            self._structured_log(
                update_id=update_id,
                chat_id=chat_id,
                command=command,
                duration_ms=int((time.time() - started) * 1000),
                status="cooldown_ignored",
            )
            return
        self.chat_cooldowns[chat_id] = time.time() + self.cooldown_seconds

        ok, response = self.execute_with_timeout(lambda: self.handle_coordination_command(text) or self.safe_help_text())
        if ok and response:
            self.send_message(response)
            self._structured_log(
                update_id=update_id,
                chat_id=chat_id,
                command=command,
                duration_ms=int((time.time() - started) * 1000),
                status="ok",
            )
            return
        self._record_error()
        self.send_message(response or "Command failed.")
        self._structured_log(
            update_id=update_id,
            chat_id=chat_id,
            command=command,
            duration_ms=int((time.time() - started) * 1000),
            status="error",
            error_message=response,
        )

    def poll_commands_once(self) -> None:
        if self._circuit_open():
            return
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

    if not bot.acquire_single_instance_lock():
        return

    if not bot.ensure_polling_ready():
        logger.warning("Telegram command polling not started because polling is not the active delivery mode")
        return

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
