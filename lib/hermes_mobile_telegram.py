"""
Hermes Mobile — Telegram wiring (READ-ONLY, dry-run by default).

A SEPARATE Telegram bot for the conversational advisor. It must NOT reuse
TheChoseone's token (that would cause a 409 conflict / break the live command
bot). It uses its own dedicated token HERMES_MOBILE_BOT_TOKEN.

Behavior per message:
  1. build read-only context (redacted)
  2. call Hermes Mobile respond_llm() (local model, falls back to template)
  3. send a conversational reply
  4. if the user wants an action, include a COMMAND DRAFT for TheChoseone
  5. NEVER execute the command, send email/DM, approve, trade, deploy, or spend.

If the dedicated token is missing: do NOT fail. Stay in dry_run and report the
blocker with setup instructions. Live polling is only started by run_live()
which requires an explicit token + Ray-only chat allowlist.
"""
from __future__ import annotations

import os

from lib import hermes_mobile_conversation as HM
from lib import nexus_war_room_router as ROUTER

# Dedicated token ONLY — never fall back to TELEGRAM_BOT_TOKEN (TheChoseone).
TOKEN_ENV = "HERMES_MOBILE_BOT_TOKEN"
ALLOWED_CHAT_ENV = "HERMES_MOBILE_CHAT_ID"   # Ray-only; defaults to TELEGRAM_CHAT_ID if set


def token_present() -> bool:
    return bool(os.environ.get(TOKEN_ENV))


def allowed_chat_id() -> str | None:
    return os.environ.get(ALLOWED_CHAT_ENV) or os.environ.get("TELEGRAM_CHAT_ID")


def setup_instructions() -> str:
    return (
        "To launch Hermes Mobile on Telegram (test-only):\n"
        "1. Create a NEW bot with @BotFather (do NOT reuse TheChoseone's token).\n"
        f"2. Put its token in env as {TOKEN_ENV}=<token> (never commit it).\n"
        f"3. Set {ALLOWED_CHAT_ENV}=<your chat id> so only Ray's chat is answered.\n"
        "4. Re-run run_live() — it stays read-only and only replies to the allowed chat.\n"
        "Note: a dedicated token avoids a 409 conflict with the live command bot."
    )


def handle_message(text: str, chat_id: str | None = None) -> dict:
    """Process one inbound message. READ-ONLY. Returns what WOULD be sent.
    Does not execute anything. Respects the war-room router (won't answer
    messages that belong to TheChoseone)."""
    r = ROUTER.route(text)
    if r["target"] != "hermes_mobile":
        # command-routed message: Hermes Mobile stays silent (TheChoseone handles it)
        return {"will_reply": False, "routed_to": r["target"], "reason": r["reason"],
                "command_text": r.get("command_text"), "executed": False}

    resp = HM.respond_llm(text)
    reply = HM.format_for_telegram(resp)
    return {
        "will_reply": True, "routed_to": "hermes_mobile",
        "reply_text": reply,
        "provider": resp.get("provider"), "model": resp.get("model"),
        "used_fallback": resp.get("used_fallback"),
        "command_draft": resp.get("command_draft"),   # text only — NOT executed
        "executed": False, "read_only": True,
    }


def status() -> dict:
    return {
        "token_present": token_present(),
        "token_env": TOKEN_ENV,
        "allowed_chat_configured": bool(allowed_chat_id()),
        "mode": "live_ready" if token_present() else "dry_run",
        "reuses_thechoseone_token": False,
        "read_only": True,
    }


def run_live() -> int:
    """Start long-poll loop — ONLY if a dedicated token + allowed chat exist, and
    only replies to the allowed chat. Read-only. Not auto-started anywhere."""
    if not token_present():
        print("[hermes_mobile_telegram] BLOCKED: no dedicated token.\n" + setup_instructions())
        return 1
    if not allowed_chat_id():
        print("[hermes_mobile_telegram] BLOCKED: no allowed chat id (Ray-only required).")
        return 1
    # Live polling intentionally not implemented in this read-only build; wiring is
    # ready but launching the loop requires Ray's explicit test-only approval.
    print("[hermes_mobile_telegram] Token + chat present. Live loop is gated pending "
          "Ray's explicit test-only launch approval. No polling started.")
    return 0
