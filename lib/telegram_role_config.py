from __future__ import annotations

import os
from dataclasses import dataclass


def _env_truthy(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class TelegramRoleConfig:
    role: str
    token: str
    chat_id: str
    token_source: str
    chat_source: str
    warnings: list[str]


def _resolve_with_fallback(primary: str, fallbacks: list[str]) -> tuple[str, str, list[str]]:
    warnings: list[str] = []
    if os.getenv(primary):
        return os.getenv(primary, "").strip(), primary, warnings
    for fallback in fallbacks:
        value = os.getenv(fallback, "").strip()
        if value:
            warnings.append(f"{primary} not set; falling back to legacy {fallback}")
            return value, fallback, warnings
    return "", "unset", warnings


def get_ops_config() -> TelegramRoleConfig:
    token, token_source, warnings = _resolve_with_fallback(
        "TELEGRAM_OPS_BOT_TOKEN",
        ["TELEGRAM_INBOUND_BOT_TOKEN", "HERMES_BOT_TOKEN", "NEXUS_ONE_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"],
    )
    chat_id, chat_source, chat_warnings = _resolve_with_fallback(
        "TELEGRAM_OPS_CHAT_ID",
        ["TELEGRAM_CHAT_ID"],
    )
    return TelegramRoleConfig("ops", token, chat_id, token_source, chat_source, warnings + chat_warnings)


def get_reports_config() -> TelegramRoleConfig:
    token, token_source, warnings = _resolve_with_fallback(
        "TELEGRAM_REPORTS_BOT_TOKEN",
        ["NEXUS_ONE_BOT_TOKEN", "TELEGRAM_BOT_TOKEN"],
    )
    chat_id, chat_source, chat_warnings = _resolve_with_fallback(
        "TELEGRAM_REPORTS_CHAT_ID",
        ["TELEGRAM_CHAT_ID"],
    )
    return TelegramRoleConfig("reports", token, chat_id, token_source, chat_source, warnings + chat_warnings)


def get_chat_config() -> TelegramRoleConfig:
    token, token_source, warnings = _resolve_with_fallback(
        "TELEGRAM_HERMES_CHAT_BOT_TOKEN",
        ["TELEGRAM_BOT_TOKEN"],
    )
    chat_id, chat_source, chat_warnings = _resolve_with_fallback(
        "TELEGRAM_HERMES_CHAT_ID",
        ["TELEGRAM_CHAT_ID"],
    )
    return TelegramRoleConfig("chat", token, chat_id, token_source, chat_source, warnings + chat_warnings)


def hermes_chat_enabled() -> bool:
    return _env_truthy("ENABLE_HERMES_CHAT_BOT", "false")


def allow_shared_token() -> bool:
    return _env_truthy("TELEGRAM_ALLOW_SHARED_TOKEN", "false")


def shared_token_detected() -> bool:
    ops = get_ops_config().token
    reports = get_reports_config().token
    chat = get_chat_config().token if hermes_chat_enabled() else ""
    values = [token for token in [ops, reports, chat] if token]
    return len(values) != len(set(values))


def validate_ops_polling() -> tuple[bool, list[str]]:
    ops = get_ops_config()
    reports = get_reports_config()
    chat = get_chat_config()
    errors: list[str] = []
    if not ops.token:
        errors.append("TELEGRAM_OPS_BOT_TOKEN is not configured")
    if not ops.chat_id:
        errors.append("TELEGRAM_OPS_CHAT_ID is not configured")
    if ops.token and reports.token and ops.token == reports.token and not allow_shared_token():
        errors.append("Ops token matches reports token; refusing shared-token polling by default")
    if hermes_chat_enabled() and ops.token and chat.token and ops.token == chat.token:
        errors.append("Ops token matches Hermes chat token; refusing polling")
    return (not errors), errors


def validate_reports_sender() -> tuple[bool, list[str]]:
    reports = get_reports_config()
    errors: list[str] = []
    if not reports.token:
        errors.append("TELEGRAM_REPORTS_BOT_TOKEN is not configured")
    if not reports.chat_id:
        errors.append("TELEGRAM_REPORTS_CHAT_ID is not configured")
    return (not errors), errors


def validate_chat_bot() -> tuple[bool, list[str]]:
    if not hermes_chat_enabled():
        return True, ["Hermes chat bot disabled by default"]
    ops = get_ops_config()
    reports = get_reports_config()
    chat = get_chat_config()
    errors: list[str] = []
    if not chat.token:
        errors.append("TELEGRAM_HERMES_CHAT_BOT_TOKEN is required when ENABLE_HERMES_CHAT_BOT=true")
    if not chat.chat_id:
        errors.append("TELEGRAM_HERMES_CHAT_ID is required when ENABLE_HERMES_CHAT_BOT=true")
    if chat.token and ops.token and chat.token == ops.token:
        errors.append("Hermes chat token must not match ops token")
    if chat.token and reports.token and chat.token == reports.token:
        errors.append("Hermes chat token must not match reports token")
    return (not errors), errors
