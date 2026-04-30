#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from telegram_bot import NexusTelegramBot, TelegramReportSender
from lib.telegram_role_config import hermes_chat_enabled, validate_ops_polling

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


def make_bot() -> NexusTelegramBot:
    os.environ.setdefault("TELEGRAM_OPS_BOT_TOKEN", "ops-token")
    os.environ.setdefault("TELEGRAM_OPS_CHAT_ID", "chat-1")
    os.environ.setdefault("TELEGRAM_REPORTS_BOT_TOKEN", "reports-token")
    os.environ.setdefault("TELEGRAM_REPORTS_CHAT_ID", "chat-1")
    bot = NexusTelegramBot()
    bot.chat_id = "chat-1"
    bot.connected = True
    return bot


def test_ops_bot_uses_ops_token():
    os.environ["TELEGRAM_OPS_BOT_TOKEN"] = "ops-token-1"
    os.environ["TELEGRAM_OPS_CHAT_ID"] = "chat-1"
    bot = NexusTelegramBot()
    check("ops bot uses ops token", bot.bot_token == "ops-token-1", bot.bot_token)


def test_reports_sender_uses_reports_token():
    os.environ["TELEGRAM_REPORTS_BOT_TOKEN"] = "reports-token-1"
    os.environ["TELEGRAM_REPORTS_CHAT_ID"] = "chat-2"
    sender = TelegramReportSender()
    check("reports sender uses reports token", sender.bot_token == "reports-token-1", sender.bot_token)
    check("reports sender uses reports chat id", sender.chat_id == "chat-2", sender.chat_id)


def test_shared_token_rejected_by_default():
    os.environ["TELEGRAM_OPS_BOT_TOKEN"] = "shared-token"
    os.environ["TELEGRAM_REPORTS_BOT_TOKEN"] = "shared-token"
    os.environ["TELEGRAM_OPS_CHAT_ID"] = "chat-1"
    os.environ["TELEGRAM_REPORTS_CHAT_ID"] = "chat-1"
    os.environ["TELEGRAM_ALLOW_SHARED_TOKEN"] = "false"
    ok, errors = validate_ops_polling()
    check("shared token rejected by default", ok is False and any("reports token" in error for error in errors), str(errors))


def test_hermes_chat_disabled_by_default():
    os.environ["ENABLE_HERMES_CHAT_BOT"] = "false"
    check("Hermes chat bot disabled by default", hermes_chat_enabled() is False, str(hermes_chat_enabled()))


def test_status_command_does_not_call_llm():
    bot = make_bot()
    called = {"status": 0, "send": []}
    bot.safe_status_summary = lambda: called.__setitem__("status", called["status"] + 1) or "ok"
    bot.send_message = lambda message, parse_mode="HTML": called["send"].append(message) or True

    update = {
        "update_id": 101,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": "status",
        },
    }
    bot.handle_update(update)
    check("status command handled locally", called["status"] == 1, str(called))
    check("status command sends one reply", len(called["send"]) == 1, str(called["send"]))


def test_duplicate_update_ignored():
    bot = make_bot()
    sent: list[str] = []
    bot.safe_help_text = lambda: "help"
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True

    update = {
        "update_id": 202,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": "help",
        },
    }
    bot.handle_update(update)
    bot.handle_update(update)
    check("duplicate update id ignored", len(sent) == 1, str(sent))


def test_ignore_self_messages():
    bot = make_bot()
    sent: list[str] = []
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True

    update = {
        "update_id": 303,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 99, "is_bot": True},
            "text": "status",
        },
    }
    bot.handle_update(update)
    check("bot ignores its own messages", not sent, str(sent))


def test_long_message_rejected_safely():
    bot = make_bot()
    sent: list[str] = []
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True
    long_text = "x" * (bot.max_inbound_chars + 20)

    update = {
        "update_id": 404,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": long_text,
        },
    }
    bot.handle_update(update)
    check("long message rejected safely", bool(sent) and "Message too long" in sent[0], sent[0] if sent else "no reply")


def test_unknown_command_returns_help():
    bot = make_bot()
    sent: list[str] = []
    bot.safe_help_text = lambda: "SAFE HELP"
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True

    update = {
        "update_id": 505,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": "do something wild",
        },
    }
    bot.handle_update(update)
    check("unknown command returns help", sent == ["SAFE HELP"], str(sent))


def test_command_timeout_handled():
    bot = make_bot()
    bot.command_timeout_seconds = 0.01
    bot.handle_coordination_command = lambda text: (__import__("time").sleep(0.05) or "late")
    sent: list[str] = []
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True

    update = {
        "update_id": 606,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": "status",
        },
    }
    bot.handle_update(update)
    check("command timeout handled", bool(sent) and "timed out" in sent[0].lower(), sent[0] if sent else "no reply")


def test_no_recursive_loop():
    bot = make_bot()
    sent: list[str] = []
    bot.send_message = lambda message, parse_mode="HTML": sent.append(message) or True

    incoming = {
        "update_id": 707,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 1, "is_bot": False},
            "text": "help",
        },
    }
    reflected = {
        "update_id": 708,
        "message": {
            "chat": {"id": "chat-1"},
            "from": {"id": 99, "is_bot": True},
            "text": "Safe commands",
        },
    }
    bot.handle_update(incoming)
    bot.handle_update(reflected)
    check("no recursive telegram loop", len(sent) == 1, str(sent))


def main() -> int:
    test_ops_bot_uses_ops_token()
    test_reports_sender_uses_reports_token()
    test_shared_token_rejected_by_default()
    test_hermes_chat_disabled_by_default()
    test_status_command_does_not_call_llm()
    test_duplicate_update_ignored()
    test_ignore_self_messages()
    test_long_message_rejected_safely()
    test_unknown_command_returns_help()
    test_command_timeout_handled()
    test_no_recursive_loop()

    failed = [name for name, ok, _ in _results if not ok]
    print()
    if failed:
        print(f"{len(failed)} test(s) failed")
        for name in failed:
            print(f" - {name}")
        return 1
    print(f"All {len(_results)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
