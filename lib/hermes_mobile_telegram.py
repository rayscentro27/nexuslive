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

import atexit
import ctypes
import json
import os
import ssl
import struct
import time
import urllib.parse
import urllib.request
from pathlib import Path

from lib import hermes_mobile_conversation as HM
from lib import nexus_war_room_router as ROUTER
from lib import hermes_intelligent_layer as IL
from lib import hermes_live_action_guard as GUARD

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
OFFSET_FILE = ROOT / "logs" / "thechosenone" / ".hermes_mobile_offset"  # reuse logs dir

# Dedicated token ONLY — never fall back to TELEGRAM_BOT_TOKEN (TheChoseone).
TOKEN_ENV = "HERMES_MOBILE_BOT_TOKEN"
ALLOWED_CHAT_ENV = "HERMES_MOBILE_CHAT_ID"   # Ray-only


def _env(name: str) -> str | None:
    """Read from process env, else from gitignored .env (token never committed)."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(name + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return None


def _ssl_ctx() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _api(method: str, params: dict | None = None, timeout: int = 35) -> dict:
    token = _env(TOKEN_ENV)
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
        return json.load(resp)


LOCK_FILE = ROOT / "logs" / "thechosenone" / ".hermes_mobile.lock"

# A lock is only honored if the recorded PID's command line contains one of these.
# This is what tells a real Hermes Mobile loop apart from a reused PID (e.g. a macOS
# CommerceKit process that inherited the number after a reboot).
HERMES_MOBILE_MARKERS = ("run_hermes_mobile_telegram", "hermes_mobile", "NexusHermesMobileBot")


def _process_cmdline(pid: int) -> str | None:
    """Best-effort 'exec-path + argv' for a PID, or None if the process is gone /
    unreadable. Single seam used by the lock logic (mocked in tests).

    Implemented with the sysctl KERN_PROCARGS2 syscall via ctypes — deliberately NO
    subprocess fork, because forking can hang in this working directory (the same
    pathology the war-room _git_commit fix avoids). Only the executable path and argv
    are returned; the process environment block is parsed past and discarded, so no
    env vars / tokens are ever included."""
    try:
        libc = ctypes.CDLL("libc.dylib", use_errno=True)
        CTL_KERN, KERN_PROCARGS2, KERN_ARGMAX = 1, 49, 8
        # 1) how big can the args blob be?
        argmax = ctypes.c_int(0)
        sz = ctypes.c_size_t(ctypes.sizeof(argmax))
        mib2 = (ctypes.c_int * 2)(CTL_KERN, KERN_ARGMAX)
        if libc.sysctl(mib2, 2, ctypes.byref(argmax), ctypes.byref(sz), None, 0) != 0:
            return None
        # 2) fetch KERN_PROCARGS2 for the pid
        buf = ctypes.create_string_buffer(argmax.value)
        sz = ctypes.c_size_t(argmax.value)
        mib3 = (ctypes.c_int * 3)(CTL_KERN, KERN_PROCARGS2, int(pid))
        if libc.sysctl(mib3, 3, buf, ctypes.byref(sz), None, 0) != 0:
            return None                       # ESRCH (gone) / EINVAL / EPERM
        raw = buf.raw[:sz.value]
        if len(raw) < 4:
            return None
        # layout: int argc | exec_path\0 | \0-padding | argc * (argv\0) | env...
        argc = struct.unpack("i", raw[:4])[0]
        rest = raw[4:]
        nul = rest.find(b"\0")
        if nul < 0:
            return None
        exec_path = rest[:nul]
        i = nul
        while i < len(rest) and rest[i] == 0:  # skip NUL padding
            i += 1
        args = []
        for _ in range(max(argc, 0)):          # read exactly argc argv strings; stop
            if i >= len(rest):                 # before the environment block
                break
            end = rest.find(b"\0", i)
            if end < 0:
                end = len(rest)
            args.append(rest[i:end])
            i = end + 1
        text = b" ".join(p for p in [exec_path, *args] if p).decode("utf-8", "replace")
        return text or None
    except Exception:
        return None


def _read_lock() -> dict | None:
    """Parse the lock file. Accepts the new structured JSON format AND the legacy
    bare-PID format. Returns a dict with at least {'pid': int}, or None if the lock
    is missing/empty/unparseable."""
    try:
        raw = LOCK_FILE.read_text().strip()
    except (FileNotFoundError, OSError):
        return None
    if not raw:
        return None
    if raw.startswith("{"):                       # new structured format
        try:
            d = json.loads(raw)
            d["pid"] = int(d.get("pid"))
            return d
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
    try:                                          # legacy bare-PID format
        return {"pid": int(raw)}
    except ValueError:
        return None


def _write_lock() -> None:
    """Write a structured, secret-free lock record. No token, env, chat id, or
    message text — only operational identity fields. (Readers still accept the
    legacy bare-PID format for backward compatibility.)"""
    record = {
        "pid": os.getpid(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "process_name": "hermes_mobile",
        "runner": "scripts/run_hermes_mobile_telegram.py",
        "repo_path": str(ROOT),
        "owner": "hermes_mobile",
    }
    LOCK_FILE.write_text(json.dumps(record))


def _release_lock() -> None:
    """Remove the lock only if WE still own it (pid matches). Best-effort, runs on
    clean interpreter exit. (launchd SIGKILL won't run this, which is why stale-lock
    detection — not release — is the real safeguard.)"""
    rec = _read_lock()
    if rec is not None and rec.get("pid") == os.getpid():
        try:
            LOCK_FILE.unlink()
        except FileNotFoundError:
            pass


def _acquire_lock() -> bool:
    """Allow only one live Hermes Mobile loop.

    Returns True if we took the lock, False only if a *real* Hermes Mobile process
    already holds it. A recorded PID is honored as a live holder ONLY when it is
    alive AND its command line looks like the Hermes Mobile runner. A dead PID, or a
    PID the OS has reused for some other program (the post-reboot CommerceKit case),
    is treated as a stale lock and reclaimed so the advisor can start."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    rec = _read_lock()
    if rec is not None:
        pid = rec.get("pid")
        if isinstance(pid, int) and pid != os.getpid():
            cmd = _process_cmdline(pid)
            if cmd and any(m in cmd for m in HERMES_MOBILE_MARKERS):
                return False                      # a real Hermes Mobile loop holds it
            if cmd:
                print("[hermes_mobile] Removed stale Hermes Mobile lock: "
                      "PID existed but was not Hermes Mobile.")
            else:
                print("[hermes_mobile] Removed stale Hermes Mobile lock: "
                      "recorded PID is no longer running.")
            try:
                LOCK_FILE.unlink()
            except FileNotFoundError:
                pass
    _write_lock()
    atexit.register(_release_lock)
    return True


def token_present() -> bool:
    return bool(_env(TOKEN_ENV))


def allowed_chat_id() -> str | None:
    return _env(ALLOWED_CHAT_ENV)


def allowed_chat_ids() -> set[str]:
    """Set of allowed chat ids (comma-separated in HERMES_MOBILE_CHAT_ID).
    Supports the war-room group AND Ray's private 1:1 chat."""
    raw = _env(ALLOWED_CHAT_ENV) or ""
    return {c.strip() for c in raw.split(",") if c.strip()}


def detect_owner_chat_id() -> dict:
    """Read recent updates and return the most recent PRIVATE chat id (Ray's).
    Read-only. Requires Ray to have messaged the bot first."""
    try:
        d = _api("getUpdates", {"timeout": 0})
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}
    chats = []
    for u in d.get("result", []):
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat", {})
        if chat.get("type") == "private":
            chats.append({"chat_id": str(chat.get("id")),
                          "name": chat.get("first_name"), "username": chat.get("username")})
    return {"ok": True, "private_chats": chats, "latest": chats[-1] if chats else None}


def set_allowed_chat_id(chat_id: str) -> None:
    """Persist HERMES_MOBILE_CHAT_ID into the gitignored .env."""
    lines = ENV_FILE.read_text().splitlines() if ENV_FILE.exists() else []
    lines = [l for l in lines if not l.startswith(ALLOWED_CHAT_ENV + "=")]
    lines.append(f"{ALLOWED_CHAT_ENV}={chat_id}")
    ENV_FILE.write_text("\n".join(lines) + "\n")
    os.environ[ALLOWED_CHAT_ENV] = chat_id


def setup_instructions() -> str:
    return (
        "To launch Hermes Mobile on Telegram (test-only):\n"
        "1. Create a NEW bot with @BotFather (do NOT reuse TheChoseone's token).\n"
        f"2. Put its token in env as {TOKEN_ENV}=<token> (never commit it).\n"
        f"3. Set {ALLOWED_CHAT_ENV}=<your chat id> so only Ray's chat is answered.\n"
        "4. Re-run run_live() — it stays read-only and only replies to the allowed chat.\n"
        "Note: a dedicated token avoids a 409 conflict with the live command bot."
    )


def _intelligent_reply(text: str) -> dict | None:
    """Flag-gated advisor brain. Returns an IL result dict ONLY when:
      - HERMES_INTELLIGENT_LAYER_ENABLED=true, AND
      - the war-room router keeps the message with hermes_mobile (NOT an
        operational command — those stay with TheChoseone), AND
      - the message is advisor-style (opinion / research / prompt-building).
    Otherwise None, so existing behavior is unchanged. Never executes."""
    if not IL.enabled():
        return None
    if ROUTER.route(text).get("target") != "hermes_mobile":
        return None  # operational command — leave to existing routing / TheChoseone
    return IL.handle(text)


def handle_message(text: str, chat_id: str | None = None) -> dict:
    """Process one inbound message. READ-ONLY. Returns what WOULD be sent.
    Does not execute anything. Respects the war-room router (won't answer
    messages that belong to TheChoseone)."""
    r = ROUTER.route(text)
    if r["target"] != "hermes_mobile":
        # command-routed message: Hermes Mobile stays silent (TheChoseone handles it).
        # Live actions / worker requests route here -> Hermes never initiates them.
        return {"will_reply": False, "routed_to": r["target"], "reason": r["reason"],
                "command_text": r.get("command_text"), "executed": False}

    # ── HARD SAFETY GUARD (flag-independent): if the message is still in Hermes's
    # lane (e.g. "hermes, send emails to leads") but is a live action, refuse +
    # hand off safely. Runs BEFORE the intelligent layer and the model fallback.
    guard = GUARD.refusal_if_live_action(text)
    if guard is not None:
        return {"will_reply": True, "routed_to": "hermes_mobile",
                "reply_text": guard, "provider": "live_action_guard",
                "safety_guard": True, "executed": False, "read_only": True}

    il = _intelligent_reply(text)
    if il:
        return {"will_reply": True, "routed_to": "hermes_mobile",
                "reply_text": il["reply_text"], "provider": "intelligent_layer",
                "model": None, "used_fallback": False,
                "command_draft": il.get("command_draft"),
                "intelligent_layer": True, "intent": il.get("intent"),
                "executed": False, "read_only": True}

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


def _send(chat_id: str, text: str) -> None:
    # Telegram hard limit ~4096 chars; trim defensively.
    # Duplicate-send guard: drop identical/burst replies so a looping poller can't spam.
    def _do() -> bool:
        _api("sendMessage", {"chat_id": chat_id, "text": text[:3900]}, timeout=20)
        return True
    try:
        from lib import telegram_send_guard as _guard
        _guard.guarded(_do, text[:3900], str(chat_id), purpose="hermes_mobile_reply")
    except Exception:
        # Guard import/logic must never break a legitimate reply.
        _do()


def _strip_mention(text: str) -> str:
    """Clean an inbound message: remove any @mention (groups deliver '@Bot question')
    and a leading 'Hermes,' name-address. Read-only cleanup. Preserves the question."""
    import re
    t = re.sub(r"@\w+", " ", text or "")                       # any @mention, anywhere
    t = re.sub(r"^\s*hermes(\s+mobile)?[\s,:apostrophe-]*", "", t, flags=re.I)  # leading "Hermes,"
    return re.sub(r"\s+", " ", t).strip()


INTRO_TEXT = ("Hermes Mobile Advisor — your read-only Nexus advisor. I explain reports, "
              "summarize status, recommend next moves, and draft commands for TheChoseone. "
              "I never execute, send, approve, trade, or deploy.\n\n"
              "Try: 'what is Nexus doing right now?' · 'what needs my attention?' · "
              "'how do we make money in 30 days?' · 'help'")

HELP_TEXT = ("I can help with:\n"
             "• Nexus status — 'what is Nexus doing?'\n"
             "• Your queue — 'what needs my attention?' / 'what can I approve?'\n"
             "• Strategy — 'how do we make money in 30 days?' / 'what should I do next?'\n"
             "• Explain — 'explain the daily report'\n"
             "• Drafts — 'turn this into a task' / 'give me a prompt'\n"
             "I'm read-only: I propose and draft commands for TheChoseone, never execute.")


def _reply_for(raw_text: str) -> str:
    """Build the reply for a raw inbound message. Handles /start, help, and empty
    mentions explicitly; everything else goes through the conversation pipeline.
    Read-only: never executes. If the message is a command, it DRAFTS it for
    TheChoseone."""
    low = (raw_text or "").strip().lower()
    if low in ("/start", "start", "/start@nexushermesmobilebot"):
        return INTRO_TEXT
    if low in ("help", "/help", "commands", "/help@nexushermesmobilebot"):
        return HELP_TEXT
    text = _strip_mention(raw_text)
    if not text:                       # only a bare @mention, nothing else
        return HELP_TEXT
    # ── HARD SAFETY GUARD (flag-independent): _reply_for is the live send path and
    # is only reached when Hermes is directly addressed (DM or @mention). Never let
    # a live action reach the intelligent layer or the model fallback.
    guard = GUARD.refusal_if_live_action(text)
    if guard is not None:
        _log_message(text, guard, provider="live_action_guard")
        return guard
    # ── Hermes Advisor Brain v1 (partner-first): handles conversation, advice,
    # research-framing, approval handoffs, operator interpretation, and capability
    # truth — using Ray's profile + read-only Operator Core. Never a canned command
    # dump. Legacy pipeline below remains only as a safety fallback if the brain errors.
    try:
        from lib import hermes_advisor_brain as ADV
        reply = ADV.answer_with_advisor_mode(text)
        if reply and reply.strip():
            _log_message(text, reply, provider="advisor_brain")
            return reply
    except Exception:
        pass
    il = _intelligent_reply(text)      # flag-gated; None when off or operational cmd
    if il:
        _log_message(text, il["reply_text"], provider="intelligent_layer")
        return il["reply_text"]
    resp = HM.respond_llm(text)
    out = HM.format_for_telegram(resp)
    r = ROUTER.route(text)
    if r["is_command"]:
        out += (f"\n\n📋 That's a command — send to TheChoseone:\n  {r.get('command_text', text)}"
                "\n(I don't execute; I only advise.)")
    _log_message(text, out, provider=resp.get("provider"))
    return out


def _log_message(cleaned: str, reply: str, provider: str | None = None) -> None:
    """Log cleaned user message + reply (for debugging). No secrets stored."""
    try:
        p = ROOT / "logs" / "proof_automation" / "hermes_mobile_messages.log"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                 "cleaned_message": cleaned[:200],
                                 "provider": provider,
                                 "reply_preview": reply[:160]}) + "\n")
    except Exception:
        pass


def run_live(max_seconds: int | None = None, max_messages: int | None = None) -> int:
    """Read-only long-poll loop. Replies ONLY to the allowed PRIVATE chat (Ray).
    Ignores groups and any other chat. Never executes/sends/approves/trades."""
    if not token_present():
        print("[hermes_mobile] BLOCKED: no dedicated token.\n" + setup_instructions())
        return 1
    allowed = allowed_chat_id()
    allowed_set = allowed_chat_ids()
    if not allowed_set:
        print("[hermes_mobile] BLOCKED: no allowed chat id (Ray-only required). "
              "Run detect_owner_chat_id() after messaging the bot.")
        return 1
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Single-instance lock: refuse to start if another live loop is already running
    # (overlapping pollers cause getUpdates conflicts / connection resets).
    if not _acquire_lock():
        print("[hermes_mobile] BLOCKED: another loop is already running (lock held). "
              "Stop it first to avoid getUpdates conflicts.")
        return 1
    try:
        offset = int(OFFSET_FILE.read_text().strip())
    except Exception:
        offset = 0
    start = time.time()
    handled = 0
    print(f"[hermes_mobile] read-only loop live · replying only to chat {allowed} · @NexusHermesMobileBot")
    # NOTE: no auto "hello" on start — it was being mistaken for a reply on restarts.
    # Send a one-time hello only if explicitly requested.
    if os.environ.get("HERMES_MOBILE_SEND_HELLO", "false").lower() == "true":
        try:
            _send(allowed, INTRO_TEXT)
        except Exception as e:
            print("[hermes_mobile] could not send hello:", str(e)[:80])
    while True:
        if max_seconds and time.time() - start > max_seconds:
            print("[hermes_mobile] max_seconds reached; stopping.")
            return 0
        # SHORT polling (timeout=0): long-poll connections were being reset by the
        # local network proxy ("connection reset by peer"). Short requests survive.
        try:
            d = _api("getUpdates", {"offset": offset, "timeout": 0}, timeout=15)
        except Exception as e:
            print("[hermes_mobile] getUpdates error:", str(e)[:80])
            time.sleep(3)
            continue
        ups = d.get("result", [])
        if not ups:
            time.sleep(2)
            continue
        for u in ups:
            offset = u["update_id"] + 1
            OFFSET_FILE.write_text(str(offset))
            msg = u.get("message") or {}
            chat = msg.get("chat", {})
            text = msg.get("text", "")
            # Locked to the allowed chats (war-room group + Ray's private chat).
            # Every other chat is ignored.
            if str(chat.get("id")) not in allowed_set:
                continue
            if not text:
                continue
            # Group lane rules:
            #  - If Ray explicitly @mentions/addresses Hermes, always answer (for a
            #    command ask, we DRAFT the command, never execute).
            #  - Otherwise stay in our lane: conversation only; skip commands so
            #    TheChoseone handles them (prevents double replies). DMs: answer all.
            if chat.get("type") in ("group", "supergroup"):
                low_raw = (text or "").lower()
                mentioned = ("@nexushermesmobilebot" in low_raw
                             or low_raw.strip().startswith("hermes"))
                if not mentioned:
                    try:
                        # Skip ANY TheChoseone command (verb/alias/typo) so Hermes
                        # never double-replies after TheChoseone handled it.
                        if ROUTER.looks_like_command(_strip_mention(text)):
                            continue
                    except Exception:
                        pass
            try:
                _send(str(chat.get("id")), _reply_for(text))
            except Exception as e:
                print("[hermes_mobile] reply error:", str(e)[:80])
            handled += 1
            if max_messages and handled >= max_messages:
                print(f"[hermes_mobile] handled {handled} messages; stopping.")
                return 0


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "detect":
        print(json.dumps(detect_owner_chat_id(), indent=2))
    else:
        raise SystemExit(run_live())
