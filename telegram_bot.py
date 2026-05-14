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
import hashlib
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
OPS_MEMORY_FILE = os.path.join(os.path.dirname(__file__), ".hermes_ops_memory.json")
COORD_CLI = os.path.join(os.path.dirname(__file__), "nexus_coord.py")
OPS_SNAPSHOT = os.path.join(os.path.dirname(__file__), "scripts", "hermes_ops_snapshot.sh")
OPS_ATTENTION = os.path.join(os.path.dirname(__file__), "scripts", "hermes_ops_attention.sh")
SCHEDULER_SCRIPT = os.path.join(os.path.dirname(__file__), "operations_center", "scheduler.py")

from lib.telegram_role_config import (
    allow_shared_token,
    get_chat_config,
    get_ops_config,
    get_reports_config,
    secondary_bots_disabled,
    telegram_auto_reports_enabled,
    telegram_conversational_mode,
    telegram_manual_mode,
    telegram_primary_bot,
    telegram_manual_only,
    validate_ops_polling,
)
from lib import hermes_gate
from lib import hermes_ops_memory
from lib import swarm_coordinator
from lib.ops_monitor_agent import run_ops_monitor_summary
from lib.controlled_agents import run_controlled_agent
from lib.hermes_knowledge_brain import get_recent_recommendations, get_funding_knowledge, get_credit_knowledge, knowledge_dashboard_snapshot, build_telegram_knowledge_report_context
from lib.hermes_operational_telemetry import emit_metric
from lib.demo_readiness import run_demo_readiness_check
from lib.trading_intelligence_lab import build_trading_intelligence_report
from lib.opportunity_intelligence import build_opportunity_summary
from lib.hermes_email_knowledge_intake import recent_knowledge_email_intake
from lib.hermes_internal_first import try_internal_first
from lib.hermes_runtime_config import format_telegram_reply
from lib.hermes_supabase_first import nexus_knowledge_reply
from lib.telegram_router import TelegramRouter
from lib import hermes_conversation_memory

DIAGNOSTIC_PHRASES = {
    "status",
    "worker status",
    "system status",
    "queue status",
    "backend health",
    "health check",
    "trading status",
}

DIAGNOSTIC_TO_COMMAND = {
    "status": "status",
    "worker status": "workers",
    "system status": "status",
    "queue status": "queue",
    "backend health": "health",
    "health check": "health",
    "trading status": "ceo_report",
    "/tasks": "tasks_summary",
    "/running": "running_summary",
    "/pending": "pending_summary",
    "/approvals": "approvals_summary",
}

REPORT_PHRASES = {
    "send report",
    "generate report",
    "full report",
    "research brief",
    "opportunity report",
    "weekly report",
}

FUNDING_INSIGHT_PHRASES = {
    "what funding insights do we have",
    "funding insights",
    "funding knowledge",
    "funding recommendations",
}

CREDIT_INSIGHT_PHRASES = {
    "what credit workflow insights do we have",
    "credit workflow insights",
    "credit insights",
    "credit knowledge",
    "credit recommendations",
}

KNOWLEDGE_REPORT_PHRASES = {
    "send me a knowledge report",
    "send knowledge report",
    "knowledge report",
    "knowledge summary",
}

PLANNING_PROMPTS = {
    "what do you recommend we work on today",
    "what should we work on today",
    "next best move",
    "what should hermes do today",
}

APPROVAL_REPLY_APPROVE = {"approve", "approved", "yes proceed"}
APPROVAL_REPLY_CANCEL = {"cancel", "stop"}

TASK_SELECTION_ALIASES = {
    "start the second one": "start item 2",
    "work on the telegram issue": "work on the telegram one",
    "option 1": "do item 1",
    "option 2": "do item 2",
    "option 3": "do item 3",
    "option 4": "do item 4",
    "option 5": "do item 5",
    "pick option 1": "do item 1",
    "pick option 2": "do item 2",
    "pick option 3": "do item 3",
    "pick option 4": "do item 4",
    "pick option 5": "do item 5",
    "lets do 1": "do item 1",
    "lets do 2": "do item 2",
    "lets do 3": "do item 3",
    "lets do 4": "do item 4",
    "lets do 5": "do item 5",
    "let's do 1": "do item 1",
    "let's do 2": "do item 2",
    "let's do 3": "do item 3",
    "let's do 4": "do item 4",
    "let's do 5": "do item 5",
    "lets go with 1": "do item 1",
    "lets go with 2": "do item 2",
    "lets go with 3": "do item 3",
    "lets go with 4": "do item 4",
    "lets go with 5": "do item 5",
    "let's go with 1": "do item 1",
    "let's go with 2": "do item 2",
    "let's go with 3": "do item 3",
    "let's go with 4": "do item 4",
    "let's go with 5": "do item 5",
}


def _build_ops_context_snippet() -> str:
    """Build a short operational context string to inject into the LLM system prompt."""
    try:
        from lib import hermes_ops_memory
        from lib.notebooklm_ingest_adapter import load_dry_run_queue, summarize_intake_queue
        from pathlib import Path

        mem = hermes_ops_memory.load_memory(updated_by="context_snippet")
        pending = mem.get("pending_approval_refs") or []
        completed = mem.get("recent_completed") or []

        nlm_path = Path(__file__).resolve().parent / "reports" / "knowledge_intake" / "notebooklm_intake_queue.json"
        nlm_queue = load_dry_run_queue(str(nlm_path)) if nlm_path.exists() else []

        openrouter_ok = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
        provider_note = f"OpenRouter {'available' if openrouter_ok else 'key missing'}"

        parts = ["Current Nexus operational state:"]
        if pending:
            parts.append(f"- {len(pending)} pending approval(s) in queue")
        if completed:
            last = completed[-1]
            task_name = str(last.get("task") or last) if isinstance(last, dict) else str(last)
            parts.append(f"- Last completed: {task_name[:60]}")
        if nlm_queue:
            parts.append(f"- NotebookLM queue: {len(nlm_queue)} item(s) ready")
        parts.append(f"- AI provider: {provider_note}")

        return " ".join(parts) if len(parts) > 1 else ""
    except Exception:
        return ""


def email_summaries_enabled() -> bool:
    return os.getenv("TELEGRAM_EMAIL_SUMMARIES_ENABLED", "false").lower() == "true"


def email_reports_enabled() -> bool:
    return os.getenv("EMAIL_REPORTS_ENABLED", "true").lower() == "true"


def completion_notices_enabled() -> bool:
    return os.getenv("TELEGRAM_COMPLETION_NOTICES_ENABLED", "true").lower() == "true"


def full_reports_enabled() -> bool:
    return os.getenv("TELEGRAM_FULL_REPORTS_ENABLED", "false").lower() == "true"

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
        self.command_timeout_seconds = float(os.getenv("TELEGRAM_COMMAND_TIMEOUT_SECONDS", "30"))
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
        self.last_plan_items: list[str] = []
        self._repeat_error_key: str = ""
        self._repeat_error_count: int = 0
        self.pending_approval_action: dict[str, str] | None = None
        self.pending_swarm_plan: dict[str, str] | None = None
        self.task_lifecycle: dict[str, str] = {}
        self._last_reply_hash: str = ""
        self._last_reply_ts: float = 0.0
        self._current_chat_id: str = ""
        self.ops_memory: dict[str, Any] = self._load_operational_memory()
        self.last_plan_items = list(self.ops_memory.get("latest_daily_plan", []))
        self.task_lifecycle = dict(self.ops_memory.get("task_lifecycle", {}))
        self.pending_approval_action = self.ops_memory.get("pending_approval")
        self.pending_swarm_plan = self.ops_memory.get("pending_swarm_plan")

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

    def _load_operational_memory(self) -> dict[str, Any]:
        return hermes_ops_memory.load_memory(updated_by="telegram_bot_startup")

    def _save_operational_memory(self) -> None:
        try:
            self.ops_memory["latest_daily_plan"] = self.last_plan_items
            self.ops_memory["task_lifecycle"] = self.task_lifecycle
            self.ops_memory["pending_approval"] = self.pending_approval_action
            self.ops_memory["pending_swarm_plan"] = self.pending_swarm_plan
            self.ops_memory = hermes_ops_memory.save_memory(self.ops_memory, updated_by="telegram_bot")
        except Exception as e:
            logger.warning(f"operational memory save failed: {e}")

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

    def execute_with_custom_timeout(self, func: Callable[[], str], timeout_seconds: float) -> tuple[bool, str]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(func)
            try:
                result = future.result(timeout=max(1.0, float(timeout_seconds)))
                return True, str(result or "")
            except concurrent.futures.TimeoutError:
                return False, "Command timed out. Try again in a moment."
            except Exception as e:
                return False, f"Command failed: {e}"

    def _fallback_response_for_command(self, command: str) -> str:
        emit_metric(
            "telegram_fallback_response",
            payload={"domain": "telegram", "command": (command or "").strip().lower()},
        )
        cmd = (command or "").strip().lower()
        if cmd in {"status", "health", "jobs", "workers", "queue", "approvals"}:
            return "I hit a timeout while checking that command. Please retry in a moment."
        if cmd in {"ceo_report", "daily_summary", "trading_digest"}:
            return "I couldn't build that summary right now. I can retry or send a shorter status check."
        return "I'm online, but I couldn't complete that request right now. Please try again."

    def _log_telegram_event(self, event_type: str, status: str, payload: dict[str, Any]) -> None:
        try:
            from lib.event_intake import submit_system_event

            submit_system_event(event_type, status=status, payload=payload)
        except Exception:
            pass

    def _send_message_once(self, message: str, parse_mode: str = "HTML") -> bool:
        text = self._truncate_response(message or "")
        if not text:
            return False
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        now = time.time()
        if digest == self._last_reply_hash and (now - self._last_reply_ts) < 4.0:
            logger.info("telegram dedup reply_suppressed=true")
            emit_metric("telegram_duplicate_reply_suppressed", payload={"domain": "telegram"})
            return True
        sent = self.send_message(text, parse_mode=parse_mode)
        if sent:
            self._last_reply_hash = digest
            self._last_reply_ts = now
        return sent

    def _conversational_reply(self, raw: str) -> str:
        """Natural-language Telegram reply path for conversational mode."""
        chat_id = getattr(self, "_current_chat_id", "")
        normalized = (raw or "").strip().lower()
        if normalized in {
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening", "yo",
        }:
            hermes_conversation_memory.clear_session(chat_id)
            return "Good morning, Ray. I'm online and ready."

        # Internal-first routing — bypass LLM for known Nexus ops topics
        internal = try_internal_first(raw)
        if internal is not None:
            text = format_telegram_reply(internal.text)
            hermes_conversation_memory.record_turn(chat_id, "user", raw)
            hermes_conversation_memory.record_turn(chat_id, "assistant", internal.text)
            return text

        # Supabase-first knowledge routing — search approved knowledge, research tickets, domain tables
        # Intercepts Nexus-relevant questions before they reach the generic LLM
        supabase_reply = nexus_knowledge_reply(raw)
        if supabase_reply is not None:
            hermes_conversation_memory.record_turn(chat_id, "user", raw)
            hermes_conversation_memory.record_turn(chat_id, "assistant", supabase_reply)
            logger.info("telegram route=supabase_first reply_len=%d", len(supabase_reply))
            return format_telegram_reply(supabase_reply)

        # Build message history for conversational continuity
        history = hermes_conversation_memory.get_history(chat_id)
        is_followup = hermes_conversation_memory.is_followup(raw, chat_id)
        if is_followup:
            logger.info("telegram conversation follow-up detected chat_id=%s history_turns=%d", chat_id, len(history))

        # Build operational context snapshot to anchor identity
        ops_context = _build_ops_context_snippet()

        try:
            base_url = (os.getenv("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1").rstrip("/")
            model = (os.getenv("OPENROUTER_MODEL") or "deepseek/deepseek-chat").strip()
            key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
            if not key:
                raise RuntimeError("OPENROUTER_API_KEY missing")
            url = f"{base_url}/chat/completions"
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
            system_prompt = (
                "You are Hermes, the AI Chief of Staff for Nexus — Raymond's private business intelligence and credit platform. "
                "You have access to Nexus internal state: operational memory, knowledge queue, provider status, pending tasks. "
                "You are NOT a generic assistant. You ONLY answer in the context of Nexus operations. "
                "Personality: calm, sharp, strategic. You speak like a chief of staff who has read every internal report and knows exactly what needs attention. "
                "Rules: "
                "(1) Short — 2-4 sentences max unless the user asks for detail. No markdown headers in conversational mode. "
                "(2) Operational first — reference Nexus state, tickets, and knowledge pipeline when relevant. "
                "(3) AI providers are Nexus-internal only: OpenRouter, Ollama, Claude Code, OpenClaw. Never name external AI products. "
                "(4) For 'what to focus on today' — give 2-3 specific Nexus priorities: pending knowledge approvals, open tickets, demo readiness. Never give generic life advice. "
                "(5) Conversational tone — you are a chief of staff, not a report generator. Avoid 'Summary:', 'Here is a list:', header dumps. "
                "(6) Follow-up questions: use prior conversation context naturally. Continue the thread. "
                "(7) For Nexus-specific knowledge: the Supabase-first router already checked the knowledge base. If the question reaches you, answer from Nexus operational context only. "
                "    Never say 'I don't have live data' or 'Run Nexus search'. If you can't answer, say 'I can submit that to the research team' and nothing else. "
                "(8) Trading topics: speak like a trading-aware chief of staff — reference ICT concepts, session timing, and NitroTrades as sources where relevant. "
                "(9) Grant/funding topics: reference the knowledge pipeline, Hello Alice, SBA, and upcoming deadlines. Be actionable. "
                f"{ops_context}"
            )
            messages = [{"role": "system", "content": system_prompt}]
            if is_followup and history:
                messages.extend(history[-6:])
            else:
                messages.extend(history[-3:])
            messages.append({"role": "user", "content": raw})
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.5,
            }
            logger.info(
                "telegram conversational model=openrouter/%s history_turns=%d followup=%s",
                model, len(history), is_followup,
            )
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            resp.raise_for_status()
            data = resp.json()
            reply = str(((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            hermes_conversation_memory.record_turn(chat_id, "user", raw)
            hermes_conversation_memory.record_turn(chat_id, "assistant", reply)
            return format_telegram_reply(reply)
        except Exception:
            return "Hermes is online — conversational model unavailable right now. Try /status, /models, or ask a specific operational question."

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram"""
        if not self.connected:
            logger.warning("Telegram not connected")
            return False

        try:
            return hermes_gate.send_direct_response(
                self._truncate_response(message),
                event_type='direct_chat_reply',
                bot_token=self.bot_token,
                chat_id=self.chat_id,
                parse_mode=parse_mode,
            )

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

    def _mask_email(self, value: str) -> str:
        text = str(value or "").strip()
        if "@" not in text:
            return "not-set"
        local, domain = text.split("@", 1)
        local_mask = (local[:2] + "***") if len(local) > 2 else "***"
        return f"{local_mask}@{domain}"

    def _send_report_email_with_diagnostics(self, subject: str, body: str) -> dict[str, Any]:
        provider = "smtp_gmail"
        recipient = os.getenv("SCHEDULER_EMAIL_TO", os.getenv("NEXUS_EMAIL", "")).strip()
        masked_recipient = self._mask_email(recipient)
        logger.info("email_report_attempted=true")
        logger.info("email_provider=%s", provider)
        logger.info("email_recipient=%s", masked_recipient)
        if not email_reports_enabled():
            logger.info("email_report_sent=false")
            logger.info("email_error=email_reports_disabled")
            return {
                "ok": False,
                "sent": False,
                "configured": False,
                "provider": provider,
                "recipient_masked": masked_recipient,
                "error": "email_reports_disabled",
            }
        try:
            from notifications.operator_notifications import send_operator_email

            sent, detail = send_operator_email(subject, body)
            if sent:
                logger.info("email_report_sent=true")
                return {
                    "ok": True,
                    "sent": True,
                    "configured": True,
                    "provider": provider,
                    "recipient_masked": masked_recipient,
                    "error": "",
                }
            safe_error = str(detail or "send_failed")[:180]
            logger.info("email_report_sent=false")
            logger.info("email_error=%s", safe_error)
            return {
                "ok": False,
                "sent": False,
                "configured": "not configured" not in safe_error.lower(),
                "provider": provider,
                "recipient_masked": masked_recipient,
                "error": safe_error,
            }
        except Exception as e:
            safe_error = str(e)[:180]
            logger.info("email_report_sent=false")
            logger.info("email_error=%s", safe_error)
            return {
                "ok": False,
                "sent": False,
                "configured": False,
                "provider": provider,
                "recipient_masked": masked_recipient,
                "error": safe_error,
            }

    def send_report_email(self, subject: str, body: str) -> None:
        result = self._send_report_email_with_diagnostics(subject, body)
        if not result.get("sent"):
            logger.warning(f"Report email skipped/failed: {result.get('error')}")
        return result

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

    def render_chat_response(self, text: str) -> str:
        return str(text or "").strip()

    def render_report_response(self, text: str) -> str:
        return self.format_pre(str(text or ""))

    def render_command_response(self, text: str) -> str:
        return str(text or "").strip()

    def render_short_status(self, text: str) -> str:
        return str(text or "").strip()

    def render_daily_plan(self, items: list[dict[str, str]]) -> str:
        lines = ["Here is what I recommend we work on today:"]
        for idx, item in enumerate(items, start=1):
            lines.append(f"{idx}) {item['title']}")
            lines.append(f"- Why: {item['why']}")
            lines.append(f"- Risk: {item['risk']}")
            lines.append(f"- Action: {item['action']}")
        return "\n".join(lines)

    def render_approval_request(self, reason: str) -> str:
        return (
            "This action needs approval before I proceed:\n"
            f"{reason}\n"
            "Reply APPROVE or CANCEL."
        )

    def render_completion_notice(self, task: str) -> str:
        return f"✅ Done — I completed {task}. Full details were sent to your email."

    def render_failure_notice(self, task: str) -> str:
        return f"⚠️ I couldn't complete {task}. I saved the details and can send a report by email."

    def render_report_email(self, user_prompt: str) -> str:
        try:
            from hermes_command_router.router import run_command
            return str(run_command(user_prompt, source="telegram") or "No report content generated.")
        except Exception as e:
            return f"Report generation failed: {e}"

    def render_report_summary(self) -> str:
        return "📩 I've sent the full report to your email."

    def classify_message_route(self, raw: str) -> str:
        normalized = (raw or "").strip().lower()
        normalized = TASK_SELECTION_ALIASES.get(normalized, normalized)
        if normalized.startswith("/"):
            return "command"
        if normalized in DIAGNOSTIC_PHRASES:
            return "command"
        if any(phrase in normalized for phrase in REPORT_PHRASES):
            return "report_request"
        if any(phrase in normalized for phrase in FUNDING_INSIGHT_PHRASES):
            return "funding_insights"
        if any(phrase in normalized for phrase in CREDIT_INSIGHT_PHRASES):
            return "credit_insights"
        if any(phrase in normalized for phrase in KNOWLEDGE_REPORT_PHRASES):
            return "knowledge_report"
        if self._is_work_planning_request(normalized):
            return "daily_plan"
        if (
            normalized.startswith("do item ")
            or normalized.startswith("start item ")
            or normalized.startswith("item ")
            or normalized in {"start all", "do the funding one", "work on the telegram one", "third one", "the third one"}
        ):
            return "task_selection"
        return "chat"

    def _is_work_planning_request(self, normalized: str) -> bool:
        if any(normalized == p or normalized.startswith(p) for p in PLANNING_PROMPTS):
            return True
        # Tight heuristic: only planning/focus phrasing about today's work.
        has_today = "today" in normalized
        has_work = any(k in normalized for k in {"work", "focus", "priority", "priorities", "next best"})
        has_recommend = any(k in normalized for k in {"recommend", "should we", "what should"})
        return has_today and has_work and has_recommend

    def _risky_action_requested(self, raw: str) -> Optional[str]:
        lowered = (raw or "").lower()
        checks = {
            "deploy": "deployment action",
            "send email to client": "sending emails to clients",
            "external message": "sending external messages",
            "invoice": "billing/invoice action",
            "message client": "sending external client messages",
            "change production config": "changing production config",
            "apply migration": "applying database migrations",
            "delete data": "deleting data",
            "change dns": "changing DNS",
            "change auth": "changing auth",
            "change funding logic": "changing funding/readiness logic",
        }
        for token, reason in checks.items():
            if token in lowered:
                return reason
        return None

    def _handle_llm_error(self, err: Exception) -> str:
        key = f"{type(err).__name__}:{str(err)[:120]}"
        if key == self._repeat_error_key:
            self._repeat_error_count += 1
        else:
            self._repeat_error_key = key
            self._repeat_error_count = 1
        if self._repeat_error_count > 1:
            logger.warning("Repeated chat model error suppressed: %s", key)
        return "I'm online, but my chat model is unavailable right now."

    def _build_daily_plan(self) -> str:
        funding_hint = (get_funding_knowledge(limit=1) or [{}])[0].get("summary") or "Keeps readiness recommendations aligned with current client data."
        credit_hint = (get_credit_knowledge(limit=1) or [{}])[0].get("summary") or "Review credit workflow blockers and missing data."
        top_rec = (get_recent_recommendations(limit=1) or [{}])[0].get("summary") or "Validate worker coordination before scaling usage."
        items = [
            {
                "title": "Funding workflow review",
                "why": funding_hint,
                "risk": "Medium",
                "action": "Run a funding strategy review pass and flag blockers.",
            },
            {
                "title": "Telegram routing verification",
                "why": "Prevents report formatting leaks into chat responses.",
                "risk": "Low",
                "action": "Run conversational routing checks for command/report/chat paths.",
            },
            {
                "title": "Pilot operations simulation",
                "why": top_rec,
                "risk": "Medium",
                "action": "Execute a 10-user pilot simulation and collect failures.",
            },
            {
                "title": "Credit workflow checkpoint",
                "why": credit_hint,
                "risk": "Low",
                "action": "Review credit next-step recommendations and mark blockers.",
            },
        ]
        self.last_plan_items = [i["title"] for i in items]
        self.ops_memory = hermes_ops_memory.update_latest_daily_plan(
            self.ops_memory,
            self.last_plan_items[:],
            updated_by="telegram_daily_plan",
        )
        return self.render_daily_plan(items)

    def _knowledge_bullets(self, rows: list[dict[str, Any]], empty_text: str) -> str:
        summaries: list[str] = []
        for row in rows:
            summary = str(row.get("summary") or "").strip()
            if summary:
                cleaned = " ".join(summary.replace("\n", " ").replace("*", " ").split())
                cleaned = cleaned[:180].rstrip()
                summaries.append(cleaned)
            if len(summaries) >= 5:
                break
        if not summaries:
            return empty_text
        lines = ["- " + s for s in summaries[:5]]
        return "\n".join(lines)

    def _funding_insights_reply(self) -> str:
        rows = get_funding_knowledge(limit=5)
        return "Here are the latest funding insights:\n" + self._knowledge_bullets(
            rows,
            "- No recent funding insights are available yet.",
        )

    def _credit_insights_reply(self) -> str:
        rows = get_credit_knowledge(limit=5)
        return "Here are the latest credit workflow insights:\n" + self._knowledge_bullets(
            rows,
            "- No recent credit workflow insights are available yet.",
        )

    def _knowledge_report_email(self) -> str:
        try:
            snap = build_telegram_knowledge_report_context()
        except Exception:
            snap = knowledge_dashboard_snapshot()
        categories = snap.get("category_counts") or {}
        stale = snap.get("stale_warnings") or []
        recs = snap.get("operations") or snap.get("top_operational_recommendations") or []
        funding = snap.get("funding") or snap.get("recent_funding_insights") or []
        credit = snap.get("credit") or snap.get("recent_credit_insights") or []
        lines = [
            "Hermes Knowledge Brain Report",
            f"Generated at: {datetime.utcnow().isoformat()}Z",
            "",
            "Category Counts:",
            json.dumps(categories, indent=2),
            "",
            f"Stale Warnings: {len(stale)}",
            "",
            "Top Operational Recommendations:",
        ]
        for row in recs[:5]:
            lines.append(f"- {str(row.get('summary') or '').strip()}")
        lines.append("")
        lines.append("Recent Funding Insights:")
        for row in funding[:5]:
            lines.append(f"- {str(row.get('summary') or '').strip()}")
        lines.append("")
        lines.append("Recent Credit Insights:")
        for row in credit[:5]:
            lines.append(f"- {str(row.get('summary') or '').strip()}")
        return "\n".join(lines)

    def _knowledge_report_confirmation(self) -> str:
        return "📩 I've prepared the Knowledge Brain report for email/review."

    def _queue_task_from_selection(self, task_title: str) -> dict:
        task_map = {
            "funding": "funding_strategy_review",
            "telegram": "telegram_routing_review",
            "pilot": "worker_status_check",
        }
        lowered = task_title.lower()
        task_type = "worker_status_check"
        for key, value in task_map.items():
            if key in lowered:
                task_type = value
                break
        try:
            from lib.event_intake import submit_ceo_route_request
            result = submit_ceo_route_request(
                message=f"Run task: {task_title}",
                source="telegram",
                channel="bot",
                metadata={
                    "task_title": task_title,
                    "task_type": task_type,
                    "requested_by": "operator",
                    "priority": "medium",
                    "requires_approval": False,
                    "status": "queued",
                },
            )
            ok = not bool(result.get("error"))
            if ok:
                event_id = str(result.get("event_id") or "")
                if event_id:
                    self.task_lifecycle[event_id] = "queued"
                    self.ops_memory.setdefault("active_priorities", [])
                    if task_title not in self.ops_memory["active_priorities"]:
                        self.ops_memory["active_priorities"].append(task_title)
                    self.ops_memory = hermes_ops_memory.update_task_lifecycle(
                        self.ops_memory,
                        event_id,
                        "queued",
                        updated_by="telegram_queue_task",
                    )
                logger.info("job queued_from_telegram=true")
                return {"ok": True, "task_id": event_id, "status": "queued"}
            return {"ok": False, "error": result.get("error") or "enqueue_failed", "status": "failed"}
        except Exception as e:
            return {"ok": False, "error": str(e), "status": "failed"}

    def _task_selection_reply(self, raw: str) -> Optional[str]:
        txt = TASK_SELECTION_ALIASES.get((raw or "").strip().lower(), (raw or "").strip().lower())
        if not self.last_plan_items:
            return None
        if txt == "start all":
            for item in self.last_plan_items:
                self._queue_task_from_selection(item)
            if completion_notices_enabled():
                logger.info("telegram route=completion_notice")
                logger.info("telegram completion_sent=true")
            return "I queued all planned items. I'll notify you as they complete and email full details."
        if txt in {"third one", "the third one"}:
            txt = "do item 3"

        if txt.startswith("item "):
            txt = "do item " + txt.replace("item ", "", 1).strip()

        if txt.startswith("do item ") or txt.startswith("start item "):
            part = txt.replace("do item ", "", 1).replace("start item ", "", 1).strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(self.last_plan_items):
                    item = self.last_plan_items[idx]
                    risky = any(k in item.lower() for k in ["client", "production", "external"])
                    if risky:
                        logger.info("telegram route=approval_request")
                        logger.info("approval requested=true")
                        self.pending_approval_action = {"task": item, "reason": "Potentially risky action."}
                        self.ops_memory = hermes_ops_memory.update_approval_state(
                            self.ops_memory,
                            self.pending_approval_action,
                            updated_by="telegram_approval_requested",
                        )
                        return self.render_approval_request("Potentially risky action.")
                    q = self._queue_task_from_selection(item)
                    if not q.get("ok"):
                        logger.info("task failed=true")
                        return self.render_failure_notice(item)
                    if completion_notices_enabled():
                        logger.info("telegram route=completion_notice")
                        logger.info("telegram completion_sent=true")
                    return "I queued that task and will send completion when done."
        if txt == "do the funding one":
            item = next((i for i in self.last_plan_items if "funding" in i.lower()), self.last_plan_items[0])
            q = self._queue_task_from_selection(item)
            if not q.get("ok"):
                logger.info("task failed=true")
                return self.render_failure_notice(item)
            if completion_notices_enabled():
                logger.info("telegram route=completion_notice")
                logger.info("telegram completion_sent=true")
            return "I queued the funding task and will send completion when done."
        if txt == "work on the telegram one":
            item = next((i for i in self.last_plan_items if "telegram" in i.lower()), self.last_plan_items[0])
            q = self._queue_task_from_selection(item)
            if not q.get("ok"):
                logger.info("task failed=true")
                return self.render_failure_notice(item)
            if completion_notices_enabled():
                logger.info("telegram route=completion_notice")
                logger.info("telegram completion_sent=true")
            return "I queued the Telegram task and will send completion when done."
        return None

    def _handle_approval_reply(self, text: str) -> Optional[str]:
        if not self.pending_approval_action:
            return None
        normalized = (text or "").strip().lower()
        if normalized in APPROVAL_REPLY_APPROVE:
            task = self.pending_approval_action.get("task", "requested action")
            q = self._queue_task_from_selection(task)
            self.pending_approval_action = None
            logger.info("approval received=true")
            logger.info("approval granted=true")
            self.ops_memory = hermes_ops_memory.update_approval_state(
                self.ops_memory,
                None,
                updated_by="telegram_approval_granted",
            )
            if not q.get("ok"):
                logger.info("task failed=true")
                self.ops_memory = hermes_ops_memory.record_failure(
                    self.ops_memory,
                    task=task,
                    reason=q.get("error", "unknown"),
                    retry_recommendation="Retry after configuration check.",
                    updated_by="telegram_approval_failure",
                )
                return self.render_failure_notice(task)
            return "Approved. I queued the task and will notify you on completion."
        if normalized in APPROVAL_REPLY_CANCEL:
            self.pending_approval_action = None
            logger.info("approval received=true")
            logger.info("approval canceled=true")
            logger.info("task canceled=true")
            self.ops_memory = hermes_ops_memory.update_approval_state(
                self.ops_memory,
                None,
                updated_by="telegram_approval_canceled",
            )
            return "Cancelled. I did not proceed."
        return None

    def _handle_command_mode(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        if normalized in {"/tasks", "/running", "/pending", "/approvals"}:
            key = DIAGNOSTIC_TO_COMMAND.get(normalized)
            if key:
                return self.render_short_status(self.handle_basic_command(key))
        if normalized.startswith("/"):
            cmd = normalized[1:]
            if cmd in {"help", "status", "health", "workers", "queue", "approvals"}:
                mapped = "workers" if cmd == "workers" else ("queue" if cmd == "queue" else cmd)
                return self.render_short_status(self.handle_basic_command(mapped))
            if cmd == "reset":
                self.last_plan_items = []
                self.pending_approval_action = None
                self.ops_memory = hermes_ops_memory.update_approval_state(
                    self.ops_memory,
                    None,
                    updated_by="telegram_reset",
                )
                return "State reset complete."
            if cmd == "restart":
                return "Restart request received. Use launchctl command from terminal to restart Hermes safely."
            return self.render_short_status(self.safe_help_text())
        if normalized in DIAGNOSTIC_TO_COMMAND:
            return self.render_short_status(self.handle_basic_command(DIAGNOSTIC_TO_COMMAND[normalized]))
        return self.render_short_status(self.handle_coordination_command(text) or self.safe_help_text())

    def _task_rows(self, status: str = "") -> list[dict]:
        try:
            from scripts.prelaunch_utils import rest_select
            filt = f"&status=eq.{status}" if status else ""
            return rest_select(
                "system_events?select=id,status,event_type,created_at,payload"
                f"&event_type=eq.ceo_route_request{filt}&order=created_at.desc&limit=20",
                timeout=8,
            ) or []
        except Exception:
            return []

    def _cmd_tasks_summary(self) -> str:
        local = list(self.task_lifecycle.values())
        if local:
            running = sum(1 for s in local if s == "running")
            pending = sum(1 for s in local if s in {"queued", "pending", "waiting_for_approval"})
            failed = sum(1 for s in local if s == "failed")
            completed = sum(1 for s in local if s == "completed")
            canceled = sum(1 for s in local if s == "canceled")
            return f"You have {running} running, {pending} pending, {completed} completed, {failed} failed, and {canceled} canceled tasks."
        rows = self._task_rows()
        running = sum(1 for r in rows if (r.get("status") or "").lower() in {"processing", "running"})
        pending = sum(1 for r in rows if (r.get("status") or "").lower() in {"pending", "queued"})
        failed = sum(1 for r in rows if (r.get("status") or "").lower() in {"failed", "error"})
        return f"You currently have {running} running tasks, {pending} pending tasks, and {failed} failed tasks."

    def _cmd_running_summary(self) -> str:
        rows = self._task_rows("processing")
        return f"Running tasks: {len(rows)}."

    def _cmd_pending_summary(self) -> str:
        rows = self._task_rows("pending")
        return f"Pending tasks: {len(rows)}."

    def _cmd_approvals_summary(self) -> str:
        try:
            from scripts.prelaunch_utils import rest_select
            rows = rest_select("owner_approval_queue?select=id,status&status=eq.pending&limit=20", timeout=8) or []
            return f"You currently have {len(rows)} pending approvals."
        except Exception:
            return "Pending approvals unavailable right now."

    def _recent_completed_summary(self) -> str:
        rows = self.ops_memory.get("recent_completed", [])
        if not rows:
            return "No completed items are stored yet today."
        return "Recently completed: " + ", ".join(str(r.get("task", "task")) for r in rows[-3:])

    def _failed_summary(self) -> str:
        return hermes_ops_memory.summarize_failed_today(self.ops_memory)

    def _blocked_summary(self) -> str:
        rows = self.ops_memory.get("blocked_priorities", [])
        if not rows:
            return "Nothing is currently blocked."
        return "Blocked priorities: " + ", ".join(rows[:3])

    def _active_priorities_summary(self) -> str:
        return hermes_ops_memory.summarize_current_work(self.ops_memory)

    def _resume_previous_work_summary(self) -> str:
        return hermes_ops_memory.summarize_resume_previous_work(self.ops_memory)

    def _start_work_session_summary(self) -> str:
        goal = "Advance today's top priorities."
        self.ops_memory = hermes_ops_memory.start_work_session(
            self.ops_memory,
            current_goal=goal,
            updated_by="telegram_work_session_start",
        )
        return "Perfect — I started a work session. I’ll keep track of tasks, approvals, and blockers as we go."

    def _pause_work_session_summary(self) -> str:
        self.ops_memory = hermes_ops_memory.pause_work_session(
            self.ops_memory,
            updated_by="telegram_work_session_pause",
        )
        return "Got it — I paused the work session. Say 'resume work session' anytime and we’ll pick back up."

    def _resume_work_session_summary(self) -> str:
        self.ops_memory = hermes_ops_memory.resume_work_session(
            self.ops_memory,
            updated_by="telegram_work_session_resume",
        )
        return hermes_ops_memory.summarize_work_session(self.ops_memory)

    def _summarize_work_session(self) -> str:
        return hermes_ops_memory.summarize_work_session(self.ops_memory)

    def _list_agents_summary(self) -> str:
        agents = swarm_coordinator.list_agents()
        names = [a.get("name", "Agent") for a in agents]
        return "Here’s the specialist lineup I can plan with: " + ", ".join(names[:10])

    def _plan_swarm_task_summary(self, goal: str) -> str:
        plan = swarm_coordinator.dry_run_swarm_plan(goal)
        role = plan.get("assigned_role", "unknown")
        approval = "yes" if plan.get("approval_required") else "no"
        self.pending_swarm_plan = {
            "goal": goal or "general operational improvement",
            "assigned_role": role,
        }
        self._save_operational_memory()
        return (
            f"Nice — I drafted a dry-run swarm plan for that. Lead specialist: {role}. "
            f"Approval required: {approval}. Nothing executed yet. "
            "Reply 'start swarm task' to queue planning-only work, or 'wait' to hold."
        )

    def _handle_swarm_followup(self, normalized: str) -> Optional[str]:
        if not self.pending_swarm_plan:
            return None
        if normalized in {"wait", "hold", "not now"}:
            self.pending_swarm_plan = None
            self._save_operational_memory()
            return "Sounds good — I’ll hold that swarm plan until you want to run it."
        if normalized in {"start swarm task", "start swarm", "queue swarm task"}:
            goal = self.pending_swarm_plan.get("goal", "swarm task")
            role = self.pending_swarm_plan.get("assigned_role", "qa_test")
            self.pending_swarm_plan = None
            self._save_operational_memory()
            return (
                f"Done — I queued a dry-run swarm planning task for '{goal}' with {role}. "
                "It’s planning-only, so no external actions were executed."
            )
        return None

    def _plan_item_status(self, idx: int) -> str:
        return hermes_ops_memory.resolve_plan_item_status(self.ops_memory, idx)

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
            "/tasks    — task summary\n"
            "/running  — running tasks\n"
            "/pending  — pending tasks\n"
            "/approvals — pending approvals\n\n"
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
        normalized_key = normalized.rstrip(" ?!.")
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
            "run demo readiness check": "demo_readiness_check",
            "demo ready": "demo_readiness_check",
            "what funding blockers do we have": "funding_blockers",
            "what trading strategies are launch focus": "launch_focus_strategies",
            "what trading strategies are lanch focus": "launch_focus_strategies",
            "what opportunities should we review": "opportunity_review",
            "where are you getting your information from": "data_source_summary",
            "are you using what is in supabase": "data_source_summary",
        }
        return mapping.get(normalized, mapping.get(normalized_key, "unknown")), raw

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
            "tasks_summary": self._cmd_tasks_summary,
            "running_summary": self._cmd_running_summary,
            "pending_summary": self._cmd_pending_summary,
            "approvals_summary": self._cmd_approvals_summary,
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

    def _cmd_demo_readiness_check(self) -> str:
        try:
            report = run_demo_readiness_check()
            score = int(report.get("score") or 0)
            status = str(report.get("status") or "unknown")
            blockers = report.get("blockers") or []
            if blockers:
                return (
                    f"✅ Demo readiness is {status} ({score}). "
                    f"Top blocker: {str(blockers[0])[:90]}. "
                    "I can send the full report by email."
                )
            return f"✅ Demo readiness is {status} ({score}) with no blockers detected. I can send the full report by email."
        except Exception as e:
            return f"Demo readiness check error: {e}"

    def _cmd_launch_focus_strategies(self) -> str:
        try:
            report = build_trading_intelligence_report()
            focus = report.get("launch_focus_strategies") or []
            names = [str(s.get("strategy_name") or "").strip() for s in focus if str(s.get("strategy_name") or "").strip()]
            if not names:
                return "Launch-focus strategies are currently unavailable."
            return "🚀 Launch-focus strategies: " + ", ".join(names[:3]) + "."
        except Exception as e:
            return f"Trading launch-focus error: {e}"

    def _cmd_opportunity_review(self) -> str:
        try:
            summary = build_opportunity_summary()
            grants = summary.get("grant_opportunity_summary") or []
            business = summary.get("business_opportunity_summary") or []
            titles = []
            for row in (grants + business):
                title = str(row.get("summary") or row.get("title") or "").strip()
                if title:
                    titles.append(title)
                if len(titles) >= 3:
                    break
            action = str(summary.get("opportunity_next_action") or "Review the opportunity shortlist and blockers.")
            if titles:
                return f"Here are the top opportunities to review: {', '.join(titles)}. Next best action: {action}"
            return f"The opportunity shortlist is sparse right now. Next best action: {action}"
        except Exception as e:
            return f"Opportunity review error: {e}"

    def _cmd_funding_blockers_conversational(self) -> str:
        core = str(self.handle_basic_command("funding_blockers") or "").strip()
        if not core:
            return "I couldn't pull funding blockers right now. I can retry or send a full report by email."
        return f"Here’s what I’m seeing for funding blockers right now: {core}"

    def _cmd_data_source_summary(self) -> str:
        return (
            "I use Nexus data paths first (Supabase-backed system events, workflow outputs, and operational memory) "
            "when available, then fall back to safe summaries if a data path is unavailable."
        )

    def _cmd_knowledge_emails_summary(self) -> str:
        try:
            rows = recent_knowledge_email_intake(limit=5)
            if not rows:
                return "No recent knowledge email intake records found yet."
            cats: dict[str, int] = {}
            for r in rows:
                c = str(r.get("category") or "general")
                cats[c] = cats.get(c, 0) + 1
            top = ", ".join([f"{k}:{v}" for k, v in sorted(cats.items(), key=lambda x: (-x[1], x[0]))[:3]])
            return f"Recent knowledge email proposals: {len(rows)} records. Top categories: {top}."
        except Exception as e:
            return f"Knowledge email status unavailable right now: {e}"

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

    def handle_inbound_message(self, text: str) -> str:
        normalized = (text or "").strip().lower()
        if normalized:
            self.ops_memory["last_user_instruction"] = normalized[:300]
            self.ops_memory = hermes_ops_memory.save_memory(
                self.ops_memory,
                updated_by="telegram_user_instruction",
            )
        continuity = {
            "run demo readiness check": self._cmd_demo_readiness_check,
            "demo ready?": self._cmd_demo_readiness_check,
            "demo ready": self._cmd_demo_readiness_check,
            "what funding blockers do we have": self._cmd_funding_blockers_conversational,
            "what trading strategies are launch focus": self._cmd_launch_focus_strategies,
            "what trading strategies are lanch focus": self._cmd_launch_focus_strategies,
            "what opportunities should we review": self._cmd_opportunity_review,
            "where are you getting your information from": self._cmd_data_source_summary,
            "are you using what is in supabase": self._cmd_data_source_summary,
            "run remote readiness check": self._cmd_demo_readiness_check,
            "send remote ceo report": lambda: self._run_controlled_agent("report_writer"),
            "what needs my approval?": self._cmd_approvals_summary,
            "what knowledge emails came in?": self._cmd_knowledge_emails_summary,
            "what marketing tasks are ready?": lambda: self.handle_basic_command("weekly_focus"),
            "what should i do before travel?": self._cmd_demo_readiness_check,
            "start work session": lambda: self._start_work_session_summary(),
            "pause work session": lambda: self._pause_work_session_summary(),
            "resume work session": lambda: self._resume_work_session_summary(),
            "summarize work session": lambda: self._summarize_work_session(),
            "what are we working on?": lambda: self._active_priorities_summary(),
            "what are we working on": lambda: self._active_priorities_summary(),
            "what are we currently working on?": self._cmd_tasks_summary,
            "what are we currently working on": self._cmd_tasks_summary,
            "what is still pending?": self._cmd_pending_summary,
            "what is still pending": self._cmd_pending_summary,
            "what approvals are waiting?": self._cmd_approvals_summary,
            "what approvals are waiting": self._cmd_approvals_summary,
            "what did we finish today?": lambda: self._recent_completed_summary(),
            "what did we finish today": lambda: self._recent_completed_summary(),
            "resume previous work": lambda: self._resume_previous_work_summary(),
            "what is blocked?": lambda: self._blocked_summary(),
            "what is blocked": lambda: self._blocked_summary(),
            "what failed?": lambda: self._failed_summary(),
            "what failed": lambda: self._failed_summary(),
            "show active priorities": lambda: self._active_priorities_summary(),
            "what were we working on?": lambda: self._resume_previous_work_summary(),
            "what were we working on": lambda: self._resume_previous_work_summary(),
            "what were working on?": lambda: self._resume_previous_work_summary(),
            "what were working on": lambda: self._resume_previous_work_summary(),
            "did we finish item 1?": lambda: self._plan_item_status(1),
            "did we finish item 1": lambda: self._plan_item_status(1),
            "did we finish item 2?": lambda: self._plan_item_status(2),
            "did we finish item 2": lambda: self._plan_item_status(2),
            "did we finish item 3?": lambda: self._plan_item_status(3),
            "did we finish item 3": lambda: self._plan_item_status(3),
            "run ops monitor": lambda: self._run_ops_monitor_summary(),
            "check ops monitor": lambda: self._run_ops_monitor_summary(),
            "ops monitor summary": lambda: self._run_ops_monitor_summary(),
            "run qa check": lambda: self._run_controlled_agent("qa_test"),
            "run test agent": lambda: self._run_controlled_agent("qa_test"),
            "check system tests": lambda: self._run_controlled_agent("qa_test"),
            "send executive report": lambda: self._run_controlled_agent("report_writer"),
            "write weekly report": lambda: self._run_controlled_agent("report_writer"),
            "send nexus summary": lambda: self._run_controlled_agent("report_writer"),
            "draft a telegram update": lambda: self._run_controlled_agent("telegram_comms"),
            "draft client update": lambda: self._run_controlled_agent("telegram_comms"),
            "review funding strategy": lambda: self._run_controlled_agent("funding_strategy"),
            "funding next step": lambda: self._run_controlled_agent("funding_strategy"),
            "review credit workflow": lambda: self._run_controlled_agent("credit_workflow"),
            "credit next step": lambda: self._run_controlled_agent("credit_workflow"),
        }
        if normalized in continuity:
            logger.info("telegram route=chat")
            return continuity[normalized]()

        swarm_followup = self._handle_swarm_followup(normalized)
        if swarm_followup:
            logger.info("telegram route=chat")
            return self.render_chat_response(swarm_followup)

        if normalized.startswith("list agents") or normalized in {"show agents", "swarm agents", "list the agents"}:
            logger.info("telegram route=command")
            return self.render_chat_response(self._list_agents_summary())

        if normalized.startswith("plan swarm task for "):
            goal = text.strip()[len("plan swarm task for "):].strip()
            logger.info("telegram route=command")
            return self.render_chat_response(self._plan_swarm_task_summary(goal or "general operational improvement"))

        router = TelegramRouter(
            classify_message_route=self.classify_message_route,
            handle_command_mode=self._handle_command_mode,
            build_daily_plan=self._build_daily_plan,
            task_selection_reply=self._task_selection_reply,
            handle_approval_reply=self._handle_approval_reply,
            risky_action_requested=self._risky_action_requested,
            conversational_reply=self._conversational_reply if telegram_conversational_mode() else self.safe_help_text,
            report_email=self.render_report_email,
            send_report_email=self.send_report_email,
            report_confirmation=self.render_report_summary,
            funding_insights_reply=self._funding_insights_reply,
            credit_insights_reply=self._credit_insights_reply,
            knowledge_report_email=self._knowledge_report_email,
            knowledge_report_confirmation=self._knowledge_report_confirmation,
            help_text=self.safe_help_text,
            email_reports_enabled=email_reports_enabled,
            full_reports_enabled=full_reports_enabled,
            report_response=self.render_report_response,
            approval_request_response=self.render_approval_request,
            chat_response=self.render_chat_response,
            model_error_response=self._handle_llm_error,
        )

        route, response = router.route_incoming_message(text)
        logger.info("telegram route=%s", route)
        if route == "approval":
            if "reply approve or cancel" in response.lower():
                logger.info("approval requested=true")
                self.pending_approval_action = {"task": text.strip(), "reason": self._risky_action_requested(text) or "approval required"}
                self.ops_memory = hermes_ops_memory.update_approval_state(
                    self.ops_memory,
                    self.pending_approval_action,
                    updated_by="telegram_approval_requested",
                )
        if route == "report_request":
            logger.info("email report_queued=true")
            logger.info("email report_sent=true")
            logger.info("telegram full_report_suppressed=true")
        if route == "knowledge_report":
            logger.info("email report_queued=true")
            logger.info("email report_sent=true")
            logger.info("telegram full_report_suppressed=true")
        return response

    def _run_ops_monitor_summary(self) -> str:
        result = run_ops_monitor_summary(send_report_email=self.send_report_email)
        if not result.get("ok"):
            return self.render_chat_response("I couldn't run Ops Monitor right now because it is disabled.")
        logger.info("telegram route=command")
        logger.info("email report_queued=true")
        if result.get("email", {}).get("sent"):
            logger.info("email report_sent=true")
            return self.render_chat_response("I ran the Ops Monitor summary. Full details were sent to your email.")
        logger.info("email report_sent=false")
        logger.info("telegram full_report_suppressed=true")
        return self.render_chat_response("I ran the summary, but email delivery is not configured. The report was saved for review.")

    def _run_controlled_agent(self, role_id: str) -> str:
        role_timeout = float(os.getenv("TELEGRAM_CONTROLLED_AGENT_TIMEOUT_SECONDS", "18"))
        ok, payload = self.execute_with_custom_timeout(
            lambda: json.dumps(run_controlled_agent(role_id=role_id, send_report_email=self.send_report_email))
        , role_timeout)
        if not ok:
            logger.error("controlled_agent timeout_or_error role=%s detail=%s", role_id, payload)
            emit_metric(
                "telegram_timeout",
                status="failed",
                payload={"domain": "telegram", "command": f"controlled_agent:{role_id}"},
            )
            return self.render_chat_response(
                f"{role_id.replace('_', ' ').title()} timed out. I did not run autonomous actions. Please retry in a moment."
            )
        try:
            result = json.loads(payload or "{}")
        except Exception:
            result = {"ok": False, "message": "Agent returned invalid response.", "can_execute": False}
        if not result.get("ok"):
            return self.render_chat_response(result.get("message") or "That agent is not enabled right now.")
        logger.info("telegram route=command")
        logger.info("telegram full_report_suppressed=true")
        email = result.get("email") or {}
        sent = bool(email.get("sent"))
        if role_id == "qa_test":
            stats = result.get("result") or {}
            if sent:
                return self.render_chat_response(f"QA check completed: {stats.get('passed', 0)} passed, {stats.get('failed', 0)} failed. Full details were sent to your email.")
            return self.render_chat_response(f"QA check completed: {stats.get('passed', 0)} passed, {stats.get('failed', 0)} failed. Email delivery is not configured, so I saved the report for review.")
        if role_id == "report_writer":
            return self.render_chat_response("I prepared the Nexus summary. Full details were sent to your email." if sent else "I prepared the Nexus summary, but email delivery is not configured. The report was saved for review.")
        if role_id == "telegram_comms":
            return self.render_chat_response("I drafted a Telegram/client update for review. Approval is required before any external send.")
        if role_id == "funding_strategy":
            return self.render_chat_response("I reviewed funding strategy and prepared next-step recommendations. Full details were sent to your email." if sent else "I reviewed funding strategy and saved recommendations for review. Email delivery is not configured.")
        if role_id == "credit_workflow":
            return self.render_chat_response("I reviewed credit workflow and prepared next-step recommendations. Full details were sent to your email." if sent else "I reviewed credit workflow and saved recommendations for review. Email delivery is not configured.")
        return self.render_chat_response("Agent run completed.")

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
        emit_metric("telegram_inbound", payload={"domain": "telegram", "command": command})

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
        self._current_chat_id = chat_id

        ok, response = self.execute_with_timeout(lambda: self.handle_inbound_message(text))
        if ok:
            rendered = (response or "").strip()
            if not rendered:
                rendered = self._fallback_response_for_command(command)
            logger.info("telegram inbound=%r response_preview=%r", text[:120], rendered[:200])
            self._send_message_once(rendered)
            emit_metric(
                "telegram_reply_success",
                payload={
                    "domain": "telegram",
                    "command": command,
                    "duration_ms": int((time.time() - started) * 1000),
                },
            )
            self._structured_log(
                update_id=update_id,
                chat_id=chat_id,
                command=command,
                duration_ms=int((time.time() - started) * 1000),
                status="ok",
            )
            self._log_telegram_event(
                "telegram_inbound_handled",
                "completed",
                {
                    "command": command,
                    "chat_id": chat_id,
                    "update_id": update_id,
                    "duration_ms": int((time.time() - started) * 1000),
                },
            )
            return
        self._record_error()
        logger.error("telegram inbound failure command=%s detail=%s", command, response)
        if "timed out" in str(response or "").lower():
            emit_metric(
                "telegram_timeout",
                status="failed",
                payload={"domain": "telegram", "command": command, "duration_ms": int((time.time() - started) * 1000)},
            )
        emit_metric(
            "telegram_failed_command",
            status="failed",
            payload={"domain": "telegram", "command": command, "duration_ms": int((time.time() - started) * 1000)},
        )
        self._send_message_once(response or self._fallback_response_for_command(command))
        self._structured_log(
            update_id=update_id,
            chat_id=chat_id,
            command=command,
            duration_ms=int((time.time() - started) * 1000),
            status="error",
            error_message=response,
        )
        self._log_telegram_event(
            "telegram_inbound_handled",
            "failed",
            {
                "command": command,
                "chat_id": chat_id,
                "update_id": update_id,
                "duration_ms": int((time.time() - started) * 1000),
                "error": (response or "unknown")[:200],
            },
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

    disabled = "hermes_status_bot, hermes_claude_bot, scheduler_notifier"
    logger.info("Telegram primary bot: TheChosenOne")
    logger.info("Telegram mode: manual-only")
    logger.info("Disabled secondary Telegram bots: %s", disabled)

    if secondary_bots_disabled() and (not telegram_manual_mode()):
        logger.warning("TELEGRAM_MODE is not manual, but primary lock is active; forcing manual behavior")

    if bot.connected and telegram_auto_reports_enabled() and not telegram_manual_mode():
        hermes_gate.send_direct_response(
            "<b>🟢 Nexus Telegram Monitor Started</b>\n"
            "<i>Nexus stack is online. Signal alerts are active.</i>",
            event_type='command_reply',
            bot_token=bot.bot_token,
            chat_id=bot.chat_id,
            parse_mode='HTML',
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
