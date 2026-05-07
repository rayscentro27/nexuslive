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

from lib.telegram_role_config import (
    allow_shared_token,
    get_chat_config,
    get_ops_config,
    get_reports_config,
    telegram_auto_reports_enabled,
    telegram_conversational_mode,
    telegram_manual_only,
    validate_ops_polling,
)
from lib import hermes_gate


def email_summaries_enabled() -> bool:
    return os.getenv("TELEGRAM_EMAIL_SUMMARIES_ENABLED", "false").lower() == "true"

class NexusTelegramBot:
    """Telegram bot for Nexus AI trading alerts and system monitoring"""

    def __init__(self, config_file: str = "telegram_config.json"):
        self.config = self.load_config(config_file)
        self.role_config = get_ops_config()
        self.bot_token = self.role_config.token or self.config.get('bot_token', 'YOUR_TELEGRAM_BOT_TOKEN')
        self.chat_id = self.role_config.chat_id or self.config.get('chat_id', 'YOUR_CHAT_ID')
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

        for warning in self.role_config.warnings:
            logger.warning("Telegram ops config: %s", warning)

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
        ok, errors = validate_ops_polling()
        if not ok:
            for error in errors:
                logger.error(error)
            return False

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

    def _conversational_reply(self, raw: str) -> str:
        """Natural-language Telegram reply path for conversational mode."""
        try:
            from hermes_claude_bot import ask_via_router
            return str(ask_via_router(raw) or "")
        except Exception:
            try:
                from hermes_command_router.router import run_command
                return self.format_pre(run_command(raw, source="telegram"))
            except Exception:
                return self.safe_help_text()

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
            if response.status_code == 400 and "can't parse entities" in response.text.lower():
                fallback_payload = {
                    "chat_id": self.chat_id,
                    "text": self._truncate_response(message),
                }
                retry = requests.post(f"{self.api_url}/sendMessage", json=fallback_payload, timeout=10)
                if retry.status_code == 200:
                    logger.warning("Telegram HTML parse failed; resent message without parse_mode")
                    return True
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
            "status    — system + worker status\n"
            "health    — monitoring checks\n"
            "jobs      — recent job activity\n"
            "workers   — worker heartbeats\n"
            "brief     — latest CEO briefing\n"
            "models    — routing/model diagnostics\n"
            "queue     — signal proposal queue\n"
            "help      — this message\n\n"
            "CEO Mode\n"
            "/ceo      — daily CEO summary\n"
            "/summarize — CEO daily executive summary\n"
            "show trading digest\n"
            "what strategies should we improve?\n"
            "what business should we build next?\n"
            "show best online opportunities\n"
            "generate website brief for the top opportunity\n"
            "show critical alerts\n"
            "what needs my approval?\n"
            "show recommendations\n"
            "show pending recommendations\n"
            "approve recommendation <id>\n"
            "reject recommendation <id>\n"
            "generate build plan for recommendation <id>\n"
            "what should we focus on this week?\n"
            "highest ROI opportunity\n"
            "best business to launch\n"
            "best performing strategy\n"
            "what should we stop doing?\n"
            "what should we automate next?\n"
            "show recommendation rankings\n"
            "what credit actions work best?\n"
            "what is blocking funding approvals?\n"
            "which lenders approve most often?\n"
            "what profile patterns succeed?\n"
            "what should improve before applying?\n"
            "which clients are closest to Tier 1 readiness?\n"
            "what credit strategies improve scores fastest?\n"
            "which clients are closest to funding?\n"
            "which clients are stuck?\n"
            "who is likely to churn?\n"
            "who needs intervention?\n"
            "highest momentum clients\n"
            "highest value clients\n"
            "who should we prioritize this week?\n"
            "which clients need outreach?\n"
            "why did Hermes recommend this?\n"
            "show recommendation reasoning\n"
            "what signals influenced this score?\n"
            "what data is missing?\n"
            "why is this client high priority?\n"
            "why is this strategy ranked highly?\n"
            "show executive review snapshot\n"
            "/leads    — lead pipeline report\n"
            "/revenue  — revenue & MRR report\n"
            "/launch   — launch KPIs today\n"
            "/alerts   — run all 12 alert checks\n"
            "/approvals — pending owner approvals\n"
            "/checklist — daily launch checklist\n"
            "/content  — content topics for today\n"
            "/outreach — outreach targets for today\n"
            "/comms    — comms delivery health\n"
            "/autofix  — run safe auto-fixes\n\n"
            "Mutating commands (require TELEGRAM_ALLOW_MUTATING_COMMANDS=true)\n"
            "/approve &lt;id&gt;\n"
            "/reject &lt;id&gt;\n"
            "/needs_edits &lt;id&gt; &lt;notes&gt;\n\n"
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
            "models": "models",
            "/models": "models",
            "/research": "research",
            "queue": "queue",
            "/queue": "queue",
            # CEO Mode commands
            "/ceo": "ceo_report",
            "ceo": "ceo_report",
            "/leads": "leads",
            "leads": "leads",
            "/revenue": "revenue",
            "revenue": "revenue",
            "/launch": "launch",
            "launch": "launch",
            "/alerts": "alerts",
            "alerts": "alerts",
            "/approvals": "approvals",
            "approvals": "approvals",
            "/checklist": "checklist",
            "checklist": "checklist",
            "/content": "content",
            "content topics": "content",
            "/outreach": "outreach",
            "outreach targets": "outreach",
            "/comms": "comms",
            "comms": "comms",
            "/autofix": "autofix",
            "autofix": "autofix",
            "/summarize": "daily_summary",
            "summarize today": "daily_summary",
            "show trading digest": "trading_digest",
            "what strategies should we improve?": "strategy_improve",
            "what business should we build next?": "business_next",
            "show best online opportunities": "online_opportunities",
            "generate website brief for the top opportunity": "website_brief",
            "show critical alerts": "critical_alerts",
            "what needs my approval?": "approvals",
            "show recommendations": "show_recommendations",
            "show pending recommendations": "show_pending_recommendations",
            "what should we focus on this week?": "weekly_focus",
            "highest roi opportunity": "highest_roi",
            "best business to launch": "best_business_launch",
            "best performing strategy": "best_strategy",
            "what should we stop doing?": "stop_doing",
            "what should we automate next?": "automate_next",
            "show recommendation rankings": "recommendation_rankings",
            "what credit actions work best?": "credit_actions_best",
            "what is blocking funding approvals?": "funding_blockers",
            "which lenders approve most often?": "lender_approvals",
            "what profile patterns succeed?": "profile_patterns",
            "what should improve before applying?": "pre_apply_improvements",
            "which clients are closest to tier 1 readiness?": "tier1_closest",
            "what credit strategies improve scores fastest?": "credit_strategies_fastest",
            "which clients are closest to funding?": "clients_closest_funding",
            "which clients are stuck?": "clients_stuck",
            "who is likely to churn?": "clients_churn",
            "who needs intervention?": "clients_intervention",
            "highest momentum clients": "clients_momentum",
            "highest value clients": "clients_value",
            "who should we prioritize this week?": "clients_weekly_priority",
            "which clients need outreach?": "clients_outreach",
            "why did hermes recommend this?": "why_recommended",
            "show recommendation reasoning": "recommendation_reasoning",
            "what signals influenced this score?": "score_signals",
            "what data is missing?": "missing_data",
            "why is this client high priority?": "client_priority_reason",
            "why is this strategy ranked highly?": "strategy_priority_reason",
            "show executive review snapshot": "executive_review_snapshot",
        }
        return mapping.get(normalized, "unknown"), raw

    def _routed_health(self) -> str:
        try:
            from hermes_command_router.router import run_command
            return run_command("check backend health", source="telegram")
        except Exception as e:
            return self.safe_health_summary()

    def _routed_workers(self) -> str:
        try:
            from hermes_command_router.router import run_command
            return run_command("worker status", source="telegram")
        except Exception as e:
            return self.safe_workers_summary()

    def _routed_queue(self) -> str:
        try:
            from hermes_command_router.router import run_command
            return run_command("queue status", source="telegram")
        except Exception as e:
            return self.safe_jobs_summary()

    def handle_basic_command(self, command: str) -> str:
        handlers: dict[str, Callable[[], str]] = {
            "status": self.safe_status_summary,
            "health": self._routed_health,
            "jobs": self._routed_queue,
            "workers": self._routed_workers,
            "help": self.safe_help_text,
            "brief": self.latest_stored_brief,
            "models": self._cmd_models,
            "queue": self._routed_queue,
            # CEO Mode
            "ceo_report": self._cmd_ceo_report,
            "leads": self._cmd_leads,
            "revenue": self._cmd_revenue,
            "launch": self._cmd_launch,
            "alerts": self._cmd_alerts,
            "approvals": self._cmd_approvals,
            "checklist": self._cmd_checklist,
            "content": self._cmd_content,
            "outreach": self._cmd_outreach,
            "comms": self._cmd_comms,
            "autofix": self._cmd_autofix,
            "daily_summary": self._cmd_daily_summary,
            "trading_digest": self._cmd_trading_digest,
            "strategy_improve": self._cmd_strategy_improve,
            "business_next": self._cmd_business_next,
            "online_opportunities": self._cmd_online_opportunities,
            "website_brief": self._cmd_website_brief,
            "critical_alerts": self._cmd_critical_alerts,
            "show_recommendations": self._cmd_show_recommendations,
            "show_pending_recommendations": self._cmd_show_pending_recommendations,
            "weekly_focus": self._cmd_weekly_focus,
            "highest_roi": self._cmd_highest_roi,
            "best_business_launch": self._cmd_best_business_launch,
            "best_strategy": self._cmd_best_strategy,
            "stop_doing": self._cmd_stop_doing,
            "automate_next": self._cmd_automate_next,
            "recommendation_rankings": self._cmd_recommendation_rankings,
            "credit_actions_best": self._cmd_credit_actions_best,
            "funding_blockers": self._cmd_funding_blockers,
            "lender_approvals": self._cmd_lender_approvals,
            "profile_patterns": self._cmd_profile_patterns,
            "pre_apply_improvements": self._cmd_pre_apply_improvements,
            "tier1_closest": self._cmd_tier1_closest,
            "credit_strategies_fastest": self._cmd_credit_strategies_fastest,
            "clients_closest_funding": self._cmd_clients_closest_funding,
            "clients_stuck": self._cmd_clients_stuck,
            "clients_churn": self._cmd_clients_churn,
            "clients_intervention": self._cmd_clients_intervention,
            "clients_momentum": self._cmd_clients_momentum,
            "clients_value": self._cmd_clients_value,
            "clients_weekly_priority": self._cmd_clients_weekly_priority,
            "clients_outreach": self._cmd_clients_outreach,
            "why_recommended": self._cmd_why_recommended,
            "recommendation_reasoning": self._cmd_recommendation_reasoning,
            "score_signals": self._cmd_score_signals,
            "missing_data": self._cmd_missing_data,
            "client_priority_reason": self._cmd_client_priority_reason,
            "strategy_priority_reason": self._cmd_strategy_priority_reason,
            "executive_review_snapshot": self._cmd_executive_review_snapshot,
        }
        handler = handlers.get(command)
        if not handler:
            return self.safe_help_text()
        return handler()

    # ── CEO Mode Command Handlers ─────────────────────────────────────────────

    def _cmd_ceo_report(self) -> str:
        try:
            from ceo_agent.revenue_tracker import build_revenue_summary_text
            from ceo_agent.lead_tracker import build_lead_summary_text
            from ceo_agent.alert_engine import run_all_checks
            lines = [
                '<b>CEO Report</b>',
                f"💰 {build_revenue_summary_text()}",
                f"🎯 {build_lead_summary_text()}",
            ]
            alerts = run_all_checks()
            lines.append(f"🚨 Active alerts: {len(alerts)}")
            if alerts:
                for a in alerts[:3]:
                    lines.append(f"  • [{a['type']}] {a['summary'][:80]}")
            return '\n'.join(lines)
        except Exception as e:
            return f"CEO report error: {e}"

    def _cmd_models(self) -> str:
        try:
            from lib.model_router import routing_preview

            previews: list[str] = []
            task_classes = [
                "funding_strategy",
                "credit_analysis",
                "telegram_reply",
                "cheap_summary",
                "research_worker",
                "coding_assistant",
            ]
            for task in task_classes:
                try:
                    p = routing_preview(task_type=task)
                    previews.append(
                        f"- {task}: {p.get('provider','?')} / {p.get('model','?')} / ctx={p.get('max_context','?')}"
                    )
                except Exception as e:
                    previews.append(f"- {task}: unavailable ({type(e).__name__})")

            default_provider = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            default_model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
            ctx = os.getenv("OPENROUTER_CTX", os.getenv("MODEL_CONTEXT_LENGTH", "128000"))

            lines = [
                "<b>Model Diagnostics</b>",
                f"default provider: {default_provider}",
                f"default model: {default_model}",
                f"configured context length: {ctx}",
                f"telegram manual-only: {telegram_manual_only()}",
                f"telegram auto reports enabled: {telegram_auto_reports_enabled()}",
                "",
                "<b>Routing Preview</b>",
                *previews,
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Models diagnostic error: {e}"

    def _cmd_leads(self) -> str:
        try:
            from ceo_agent.lead_tracker import build_lead_report
            return build_lead_report()
        except Exception as e:
            return f"Leads error: {e}"

    def _cmd_revenue(self) -> str:
        try:
            from ceo_agent.revenue_tracker import build_revenue_report
            return build_revenue_report()
        except Exception as e:
            return f"Revenue error: {e}"

    def _cmd_launch(self) -> str:
        try:
            from ceo_agent.launch_tracker import build_launch_report
            return build_launch_report(period='daily')
        except Exception as e:
            return f"Launch error: {e}"

    def _cmd_alerts(self) -> str:
        try:
            from ceo_agent.alert_engine import run_all_checks, format_alerts_telegram
            alerts = run_all_checks()
            if not alerts:
                return "✅ No active alerts — all systems green."
            return format_alerts_telegram(alerts)
        except Exception as e:
            return f"Alerts error: {e}"

    def _cmd_approvals(self) -> str:
        try:
            from ceo_agent.owner_approval import format_pending_list
            return format_pending_list()
        except Exception as e:
            return f"Approvals error: {e}"

    def _cmd_checklist(self) -> str:
        try:
            from ceo_agent.launch_tracker import build_daily_checklist
            return build_daily_checklist()
        except Exception as e:
            return f"Checklist error: {e}"

    def _cmd_content(self) -> str:
        try:
            from ceo_agent.launch_tracker import get_content_topics
            return get_content_topics(5)
        except Exception as e:
            return f"Content error: {e}"

    def _cmd_outreach(self) -> str:
        try:
            from ceo_agent.launch_tracker import get_outreach_targets
            return get_outreach_targets(3)
        except Exception as e:
            return f"Outreach error: {e}"

    def _cmd_comms(self) -> str:
        try:
            from ceo_agent.comms_reliability import get_comms_health
            return get_comms_health()
        except Exception as e:
            return f"Comms error: {e}"

    def _cmd_autofix(self) -> str:
        try:
            from ceo_agent.autofix_service import run_safe_fixes
            results = run_safe_fixes()
            if not any(v for v in results.values() if isinstance(v, dict) and any(v.values())):
                return "✅ No issues found — no auto-fixes needed."
            lines = ['<b>Auto-Fix Results</b>']
            for k, v in results.items():
                if isinstance(v, dict):
                    parts = ', '.join(f"{kk}={vv}" for kk, vv in v.items())
                    lines.append(f"  {k}: {parts}")
            return '\n'.join(lines)
        except Exception as e:
            return f"Auto-fix error: {e}"

    def _cmd_daily_summary(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_daily_executive_summary
            return build_daily_executive_summary()
        except Exception as e:
            return f"Daily summary error: {e}"

    def _cmd_trading_digest(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_trading_digest
            return build_trading_digest().get("text", "Trading digest unavailable")
        except Exception as e:
            return f"Trading digest error: {e}"

    def _cmd_strategy_improve(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_trading_digest
            d = build_trading_digest()
            recs = d.get("recommendations") or []
            if not recs:
                return "No strategy improvements detected right now."
            lines = ["<b>Strategy Improvement Recommendations</b>"]
            lines.extend([f"- {r}" for r in recs[:6]])
            return "\n".join(lines)
        except Exception as e:
            return f"Strategy recommendation error: {e}"

    def _cmd_business_next(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_business_digest
            d = build_business_digest()
            return d.get("text", "Business digest unavailable")
        except Exception as e:
            return f"Business recommendation error: {e}"

    def _cmd_online_opportunities(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_business_digest
            d = build_business_digest()
            ranked = d.get("ranked") or []
            if not ranked:
                return "No ranked online opportunities available."
            lines = ["<b>Best Online Opportunities</b>"]
            for row in ranked[:5]:
                lines.append(f"- {row.get('title','Untitled')} | score {row.get('composite','?')}")
            return "\n".join(lines)
        except Exception as e:
            return f"Online opportunities error: {e}"

    def _cmd_website_brief(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_business_digest, build_website_brief
            d = build_business_digest()
            top = d.get("top")
            if not top:
                return "No top opportunity available to generate a website brief."
            return build_website_brief(top)
        except Exception as e:
            return f"Website brief error: {e}"

    def _cmd_critical_alerts(self) -> str:
        try:
            from ceo_agent.alert_engine import run_all_checks, format_alerts_telegram
            alerts = run_all_checks()
            critical = [a for a in alerts if str(a.get("severity", "")).lower() in {"critical", "high"}]
            if not critical:
                return "✅ No critical alerts right now."
            return format_alerts_telegram(critical)
        except Exception as e:
            return f"Critical alerts error: {e}"

    def _cmd_show_recommendations(self) -> str:
        try:
            from ceo_agent.recommendation_queue import format_recommendations
            return format_recommendations(pending_only=False)
        except Exception as e:
            return f"Recommendations error: {e}"

    def _cmd_show_pending_recommendations(self) -> str:
        try:
            from ceo_agent.recommendation_queue import format_recommendations
            return format_recommendations(pending_only=True)
        except Exception as e:
            return f"Pending recommendations error: {e}"

    def _cmd_weekly_focus(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_weekly_focus
            return build_weekly_focus()
        except Exception as e:
            return f"Weekly focus error: {e}"

    def _cmd_highest_roi(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_business_digest
            top = (build_business_digest(hours=24 * 7).get("top") or {})
            if not top:
                return "No ROI-ranked business opportunity available."
            return f"Highest ROI opportunity: {top.get('title','Untitled')} (score {top.get('composite','?')})"
        except Exception as e:
            return f"Highest ROI error: {e}"

    def _cmd_best_business_launch(self) -> str:
        try:
            from ceo_agent.chief_of_staff import build_business_digest
            top = (build_business_digest(hours=24 * 7).get("top") or {})
            if not top:
                return "No launch candidate available."
            return f"Best business to launch now: {top.get('title','Untitled')} ({top.get('niche') or top.get('opportunity_type') or 'general'})"
        except Exception as e:
            return f"Best business error: {e}"

    def _cmd_best_strategy(self) -> str:
        try:
            from ceo_agent.chief_of_staff import best_performing_strategy
            return best_performing_strategy()
        except Exception as e:
            return f"Best strategy error: {e}"

    def _cmd_stop_doing(self) -> str:
        try:
            from ceo_agent.chief_of_staff import stop_doing_recommendation
            return stop_doing_recommendation()
        except Exception as e:
            return f"Stop-doing analysis error: {e}"

    def _cmd_automate_next(self) -> str:
        try:
            from ceo_agent.chief_of_staff import automate_next_recommendation
            return automate_next_recommendation()
        except Exception as e:
            return f"Automate-next error: {e}"

    def _cmd_recommendation_rankings(self) -> str:
        try:
            from ceo_agent.recommendation_queue import format_rankings, category_outcomes
            return f"{format_rankings(limit=10)}\n\n{category_outcomes()}"
        except Exception as e:
            return f"Recommendation ranking error: {e}"

    def _cmd_credit_actions_best(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import credit_actions_work_best
            return credit_actions_work_best()
        except Exception as e:
            return f"Credit intelligence error: {e}"

    def _cmd_funding_blockers(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import funding_blockers
            return funding_blockers()
        except Exception as e:
            return f"Funding blocker analysis error: {e}"

    def _cmd_lender_approvals(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import lenders_approve_most_often
            return lenders_approve_most_often()
        except Exception as e:
            return f"Lender approval analysis error: {e}"

    def _cmd_profile_patterns(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import profile_patterns_succeed
            return profile_patterns_succeed()
        except Exception as e:
            return f"Profile pattern analysis error: {e}"

    def _cmd_pre_apply_improvements(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import improve_before_applying
            return improve_before_applying()
        except Exception as e:
            return f"Pre-application guidance error: {e}"

    def _cmd_tier1_closest(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import closest_to_tier1
            return closest_to_tier1()
        except Exception as e:
            return f"Tier 1 readiness analysis error: {e}"

    def _cmd_credit_strategies_fastest(self) -> str:
        try:
            from ceo_agent.credit_funding_intelligence import credit_strategies_improve_scores_fastest
            return credit_strategies_improve_scores_fastest()
        except Exception as e:
            return f"Credit strategy velocity analysis error: {e}"

    def _cmd_clients_closest_funding(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import clients_closest_to_funding
            return clients_closest_to_funding()
        except Exception as e:
            return f"Client funding proximity error: {e}"

    def _cmd_clients_stuck(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import clients_stuck
            return clients_stuck()
        except Exception as e:
            return f"Client stalled analysis error: {e}"

    def _cmd_clients_churn(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import clients_likely_to_churn
            return clients_likely_to_churn()
        except Exception as e:
            return f"Client churn analysis error: {e}"

    def _cmd_clients_intervention(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import clients_need_intervention
            return clients_need_intervention()
        except Exception as e:
            return f"Client intervention analysis error: {e}"

    def _cmd_clients_momentum(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import highest_momentum_clients
            return highest_momentum_clients()
        except Exception as e:
            return f"Client momentum analysis error: {e}"

    def _cmd_clients_value(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import highest_value_clients
            return highest_value_clients()
        except Exception as e:
            return f"Client value analysis error: {e}"

    def _cmd_clients_weekly_priority(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import prioritize_this_week
            return prioritize_this_week()
        except Exception as e:
            return f"Client weekly priority error: {e}"

    def _cmd_clients_outreach(self) -> str:
        try:
            from ceo_agent.client_success_intelligence import clients_need_outreach
            return clients_need_outreach()
        except Exception as e:
            return f"Client outreach analysis error: {e}"

    def _cmd_why_recommended(self) -> str:
        try:
            from ceo_agent.executive_review_console import why_did_hermes_recommend_this
            return why_did_hermes_recommend_this()
        except Exception as e:
            return f"Recommendation explainability error: {e}"

    def _cmd_recommendation_reasoning(self) -> str:
        try:
            from ceo_agent.executive_review_console import show_recommendation_reasoning
            return show_recommendation_reasoning()
        except Exception as e:
            return f"Recommendation reasoning error: {e}"

    def _cmd_score_signals(self) -> str:
        try:
            from ceo_agent.executive_review_console import signals_influencing_score
            return signals_influencing_score()
        except Exception as e:
            return f"Score signal explainability error: {e}"

    def _cmd_missing_data(self) -> str:
        try:
            from ceo_agent.executive_review_console import sparse_data_diagnostics
            return sparse_data_diagnostics()
        except Exception as e:
            return f"Missing data diagnostics error: {e}"

    def _cmd_client_priority_reason(self) -> str:
        try:
            from ceo_agent.executive_review_console import why_client_high_priority
            return why_client_high_priority()
        except Exception as e:
            return f"Client priority reasoning error: {e}"

    def _cmd_strategy_priority_reason(self) -> str:
        try:
            from ceo_agent.executive_review_console import why_strategy_ranked_highly
            return why_strategy_ranked_highly()
        except Exception as e:
            return f"Strategy reasoning error: {e}"

    def _cmd_executive_review_snapshot(self) -> str:
        try:
            from ceo_agent.executive_review_console import executive_review_snapshot
            return executive_review_snapshot()
        except Exception as e:
            return f"Executive review snapshot error: {e}"

    def safe_queue_summary(self) -> str:
        try:
            from scripts.prelaunch_utils import rest_select
            rows = rest_select(
                "reviewed_signal_proposals"
                "?select=id,symbol,side,timeframe,strategy_id,entry_price,stop_loss,take_profit,ai_confidence,status,created_at"
                "&status=not.in.(executed,blocked,rejected)"
                "&order=created_at.desc&limit=10",
                timeout=8,
            ) or []
        except Exception as e:
            return f"Signal queue unavailable: {e}"

        if not rows:
            return "No pending proposals in signal queue."

        lines = [f"Signal queue — pending ({len(rows)})"]
        for r in rows:
            sym  = (r.get("symbol") or "?").replace("_", "")
            side = (r.get("side") or "?").upper()
            tf   = r.get("timeframe") or "?"
            conf = r.get("ai_confidence")
            conf_str = f"{conf*100:.0f}%" if conf is not None else "?"
            created = (r.get("created_at") or "")[:16].replace("T", " ")
            lines.append(f"ID:{r.get('id','?')[:8]} | {sym} {side} {tf} | conf={conf_str} | {created}")

        lines.append("\nTo block: /reject <id>  |  auto-executor runs all unblocked")
        return "\n".join(lines)

    def _queue_action(self, raw_text: str, action: str) -> str:
        """Block or allow a reviewed_signal_proposals entry by short or full ID."""
        parts = raw_text.strip().split(None, 1)
        if len(parts) < 2:
            return f"Usage: /{action} &lt;proposal-id&gt;"
        item_id = parts[1].strip()
        if not item_id:
            return f"Usage: /{action} &lt;proposal-id&gt;"

        new_status = "pending" if action == "approve" else "blocked"
        try:
            from scripts.prelaunch_utils import rest_select, supabase_request
            rows = rest_select(
                "reviewed_signal_proposals"
                "?select=id,symbol,side,status"
                "&status=not.in.(executed,blocked,rejected)&limit=20",
                timeout=8,
            ) or []
            match = next((r for r in rows if r.get("id", "").startswith(item_id) or r.get("id") == item_id), None)
            if not match:
                return f"No pending proposal matching ID '{item_id}'."

            full_id = match["id"]
            supabase_request(
                f"reviewed_signal_proposals?id=eq.{full_id}",
                method="PATCH",
                body={"status": new_status},
                prefer="return=minimal",
                timeout=8,
            )
            sym  = (match.get("symbol") or "?").replace("_", "")
            side = (match.get("side") or "?").upper()
            if new_status == "blocked":
                return f"BLOCKED: {sym} {side} (ID: {full_id[:8]}) — auto-executor will skip it"
            return f"ALLOWED: {sym} {side} (ID: {full_id[:8]}) — auto-executor will run it"
        except Exception as e:
            return f"Queue action failed: {e}"

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

        if normalized.startswith("/approve ") or normalized.startswith("/reject "):
            action = "approve" if normalized.startswith("/approve ") else "reject"
            if not self.allow_mutating_commands:
                return (
                    f"⛔ Mutating commands are disabled.\n"
                    f"Set TELEGRAM_ALLOW_MUTATING_COMMANDS=true to use /{action}."
                )
            # Try owner_approval_queue first, fall back to signal queue action
            parts = raw.strip().split(None, 1)
            short_id = parts[1].strip() if len(parts) > 1 else ''
            if short_id:
                try:
                    from ceo_agent.owner_approval import find_item, approve, reject
                    item = find_item(short_id)
                    if item:
                        ok = approve(item['id']) if action == 'approve' else reject(item['id'])
                        status = action + 'd' if ok else 'not found'
                        return f"Approval [{short_id}]: {status}"
                except Exception:
                    pass
            return self.format_pre(self._queue_action(raw, action))

        if normalized.startswith("/needs_edits "):
            if not self.allow_mutating_commands:
                return "⛔ Mutating commands disabled. Set TELEGRAM_ALLOW_MUTATING_COMMANDS=true."
            parts = raw.strip().split(None, 2)
            if len(parts) < 2:
                return "Usage: /needs_edits &lt;id&gt; &lt;notes&gt;"
            short_id = parts[1].strip()
            notes = parts[2].strip() if len(parts) > 2 else ''
            try:
                from ceo_agent.owner_approval import find_item, needs_edits
                item = find_item(short_id)
                if item:
                    ok = needs_edits(item['id'], notes)
                    return f"Needs-edits [{short_id}]: {'saved' if ok else 'not found'}"
                return f"No pending approval matching '{short_id}'."
            except Exception as e:
                return f"needs_edits error: {e}"

        if normalized.startswith("approve recommendation "):
            if not self.allow_mutating_commands:
                return "⛔ Mutating commands disabled. Set TELEGRAM_ALLOW_MUTATING_COMMANDS=true."
            rid = raw[len("approve recommendation "):].strip()
            try:
                from ceo_agent.recommendation_queue import set_recommendation_status
                return set_recommendation_status(rid, "approved")
            except Exception as e:
                return f"Approve recommendation error: {e}"

        if normalized.startswith("reject recommendation "):
            if not self.allow_mutating_commands:
                return "⛔ Mutating commands disabled. Set TELEGRAM_ALLOW_MUTATING_COMMANDS=true."
            rid = raw[len("reject recommendation "):].strip()
            try:
                from ceo_agent.recommendation_queue import set_recommendation_status
                return set_recommendation_status(rid, "rejected")
            except Exception as e:
                return f"Reject recommendation error: {e}"

        if normalized.startswith("generate build plan for recommendation "):
            rid = raw[len("generate build plan for recommendation "):].strip()
            try:
                from ceo_agent.recommendation_queue import generate_plan_for
                return generate_plan_for(rid)
            except Exception as e:
                return f"Generate plan error: {e}"

        if not self.allow_mutating_commands:
            if telegram_conversational_mode():
                return self._conversational_reply(raw)
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

        # ── Research Ingestion ───────────────────────────────────────────────
        if normalized.startswith("/research") or normalized.startswith("research "):
            url = raw.split(None, 1)[1].strip() if " " in raw else ""
            if not url:
                return (
                    "<b>Research Ingestion</b>\n\n"
                    "Usage: <code>/research [YouTube URL or web link]</code>\n\n"
                    "Examples:\n"
                    "<code>/research https://youtube.com/watch?v=XXXXX</code>\n"
                    "<code>/research https://youtube.com/@ChannelName</code>\n\n"
                    "The researcher will extract trade setups and queue them for AI scoring and demo trading."
                )
            return self._enqueue_research(url)

        if telegram_conversational_mode():
            return self._conversational_reply(raw)
        return self.safe_help_text()

    def _enqueue_research(self, url: str) -> str:
        """Queue a URL for research ingestion and signal extraction."""
        import json
        import tempfile
        import subprocess as sp

        NODE = "/Users/raymonddavis/.nvm/versions/node/v22.22.1/bin/node"
        RUNNER = "/Users/raymonddavis/nexus-ai/workflows/research_ingestion/research_ingestion_runner.js"
        CWD = "/Users/raymonddavis/nexus-ai/workflows/research_ingestion"

        sources_payload = {
            "sources": [{
                "url":        url,
                "name":       "user_submitted",
                "topic":      "trading",
                "max_videos": 3,
            }]
        }

        try:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, dir="/tmp", prefix="nexus_research_"
            )
            json.dump(sources_payload, tmp)
            tmp.close()

            sp.Popen(
                [NODE, RUNNER, "--once", "--sources", tmp.name, "--topic", "trading"],
                cwd=CWD,
                stdout=open(f"/Users/raymonddavis/nexus-ai/logs/research_ingestion.log", "a"),
                stderr=sp.STDOUT,
                start_new_session=True,
            )
            logger.info(f"[research] Queued URL for ingestion: {url}")
            return (
                f"🔬 <b>Research queued</b>\n\n"
                f"URL: <code>{url}</code>\n"
                f"Topic: trading\n\n"
                f"The researcher is extracting trade setups. "
                f"Signals will appear in Supabase and be scored automatically in ~3 minutes.\n\n"
                f"Watch for Telegram alerts when proposals are ready."
            )
        except Exception as e:
            logger.error(f"[research] Failed to queue {url}: {e}")
            return f"⚠️ Research queue error: {e}"

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
        """Record trading signal for digest (no immediate Telegram spam)."""
        message = (
            f"<b>📈 TRADING SIGNAL</b>\n\n"
            f"<b>Symbol:</b> {signal.get('symbol', 'N/A')}\n"
            f"<b>Action:</b> {signal.get('action', 'N/A')}\n"
            f"<b>Entry:</b> {signal.get('entry_price', 'Market')}\n"
            f"<b>Confidence:</b> {signal.get('confidence', 'N/A')}%\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            f"Nexus Trading Signal — {signal.get('symbol', 'N/A')}",
            json.dumps(signal, indent=2, default=str),
        )
        hermes_gate.record_digest_item('trading_digest', message)
        return True

    def alert_trade_execution(self, trade: Dict[str, Any]) -> bool:
        """Record trade execution for digest (no immediate Telegram spam)."""
        message = (
            f"<b>✅ TRADE EXECUTED</b>\n\n"
            f"<b>Symbol:</b> {trade.get('symbol', 'N/A')}\n"
            f"<b>Action:</b> {trade.get('action', 'N/A')}\n"
            f"<b>Entry Price:</b> {trade.get('entry_price', 'N/A')}\n"
            f"<b>Position Size:</b> {trade.get('position_size', 'N/A')}\n"
            f"<b>Order ID:</b> <code>{trade.get('order_id', 'N/A')}</code>\n"
            f"<b>Broker:</b> {trade.get('broker', 'N/A')}\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            f"Nexus Trade Executed — {trade.get('symbol', 'N/A')}",
            json.dumps(trade, indent=2, default=str),
        )
        hermes_gate.record_digest_item('trading_digest', message)
        return True

    def alert_position_closed(self, position: Dict[str, Any]) -> bool:
        """Record position closure for digest (no immediate Telegram spam)."""
        pnl = position.get('pnl', 0)
        pnl_emoji = "💰" if pnl > 0 else "📉"
        message = (
            f"<b>{pnl_emoji} POSITION CLOSED</b>\n\n"
            f"<b>Symbol:</b> {position.get('symbol', 'N/A')}\n"
            f"<b>Exit Price:</b> {position.get('exit_price', 'N/A')}\n"
            f"<b>P&L:</b> <b>${pnl:.2f}</b>\n"
            f"<b>Reason:</b> {position.get('reason', 'N/A')}\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            f"Nexus Position Closed — {position.get('symbol', 'N/A')}",
            json.dumps(position, indent=2, default=str),
        )
        hermes_gate.record_digest_item('trading_digest', message)
        return True

    def alert_risk_warning(self, warning: Dict[str, Any]) -> bool:
        """Send only true trading risk violations immediately; otherwise digest."""
        message = (
            f"<b>⚠️ RISK WARNING</b>\n\n"
            f"<b>Type:</b> {warning.get('type', 'N/A')}\n"
            f"<b>Message:</b> {warning.get('message', 'N/A')}\n"
            f"<b>Current Status:</b>\n"
            f"  • Daily P&L: ${warning.get('daily_pnl', 0):.2f}\n"
            f"  • Open Positions: {warning.get('open_positions', 0)}\n"
            f"  • Max Allowed: {warning.get('max_allowed', 'N/A')}\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            f"Nexus Risk Warning — {warning.get('type', 'N/A')}",
            json.dumps(warning, indent=2, default=str),
        )
        warn_type = str(warning.get('type', '')).lower()
        is_violation = any(k in warn_type for k in ('violation', 'breach', 'max_loss', 'risk_limit'))
        if is_violation:
            return hermes_gate.send_critical(message, event_type='trading_risk_violation')
        hermes_gate.record_digest_item('operations_digest', message)
        return True

    def alert_system_status(self, status: Dict[str, Any]) -> bool:
        """Record system status for operations digest; alert only on outages."""
        message = (
            f"<b>🤖 SYSTEM STATUS</b>\n\n"
            f"<b>Status:</b> {status.get('status', 'Unknown')}\n"
            f"<b>Hermes:</b> {'✅ Connected' if status.get('hermes_connected') else '❌ Disconnected'}\n"
            f"<b>Broker:</b> {'✅ Connected' if status.get('broker_connected') else '❌ Disconnected'}\n"
            f"<b>Signals Processed:</b> {status.get('signals_processed', 0)}\n"
            f"<b>Active Positions:</b> {status.get('active_positions', 0)}\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            "Nexus System Status",
            json.dumps(status, indent=2, default=str),
        )
        system_state = str(status.get('status', '')).lower()
        outage = any(k in system_state for k in ('offline', 'down', 'crash', 'failed'))
        if outage or (status.get('hermes_connected') is False):
            return hermes_gate.send_critical(message, event_type='backend_api_offline')
        hermes_gate.record_digest_item('operations_digest', message)
        return True

    def alert_research_complete(self, research: Dict[str, Any]) -> bool:
        """Record research completion for operations digest (no immediate Telegram spam)."""
        message = (
            f"<b>📊 RESEARCH COMPLETE</b>\n\n"
            f"<b>Strategies Found:</b> {research.get('strategies_found', 0)}\n"
            f"<b>Videos Analyzed:</b> {research.get('videos_analyzed', 0)}\n\n"
            f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        )
        self.send_email_summary(
            "Nexus Research Complete",
            json.dumps(research, indent=2, default=str),
        )
        hermes_gate.record_digest_item('operations_digest', message)
        return True

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


class TelegramReportSender:
    """Send-only Telegram client for outbound reports."""

    def __init__(self):
        self.role_config = get_reports_config()
        self.bot_token = self.role_config.token
        self.chat_id = self.role_config.chat_id
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        self.connected = bool(self.bot_token and self.chat_id)
        for warning in self.role_config.warnings:
            logger.warning("Telegram reports config: %s", warning)
        ops = get_ops_config()
        if (
            self.bot_token
            and ops.token
            and self.bot_token == ops.token
            and not allow_shared_token()
        ):
            logger.warning("Reports token matches ops token; outbound sending allowed, but shared-token polling remains blocked")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        if not self.connected:
            logger.warning("Telegram reports bot not configured")
            return False
        return hermes_gate.send(
            message,
            event_type='reports_sender',
            severity='summary',
            bot_token=self.bot_token,
            chat_id=self.chat_id,
        )

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

    if bot.connected and telegram_auto_reports_enabled():
        bot.send_message(
            "<b>🟢 Nexus Telegram Monitor Started</b>\n"
            "<i>Nexus stack is online. Signal alerts are active.</i>"
        )
        logger.info("Telegram monitor running — heartbeat every 300s")
    elif bot.connected:
        logger.info(
            "Telegram auto-report suppressed; conversational mode still enabled (conversational_mode=%s)",
            telegram_conversational_mode(),
        )
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
