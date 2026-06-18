"""telegram_send_guard.py — duplicate-send + rate-limit protection for ALL outbound
Telegram/War Room messages.

Why: bots that bypass the hermes_gate policy (e.g. the mobile long-poll loop) can
resend the same message in a loop and spam Telegram. This guard sits at the RAW send
level so every path is protected regardless of caller.

Rules:
- Exact-duplicate suppression: same (purpose, chat, body) within 30 min is dropped.
- Auto purpose cooldown: at most 1 *auto* send per purpose per 30 min (e.g. war_room).
- Per-purpose burst limit: max 3 sends per purpose per 10 min.
- TELEGRAM_MANUAL_ONLY=true blocks all *auto* sends entirely.
- --force / force=True bypasses dedup+rate (use only for explicit user-requested sends).
- Suppressions are logged locally only — never sent to Telegram.
- Store keeps NO secrets: only one-way hashes, masked chat tail, timestamps, purpose.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger("telegram_send_guard")

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "outputs" / "telegram_send_guard" / "recent_sends.json"

DEDUP_WINDOW_SEC = int(os.getenv("TELEGRAM_GUARD_DEDUP_SEC", "1800"))        # 30 min
AUTO_COOLDOWN_SEC = int(os.getenv("TELEGRAM_GUARD_AUTO_COOLDOWN_SEC", "1800"))  # 30 min
BURST_WINDOW_SEC = int(os.getenv("TELEGRAM_GUARD_BURST_SEC", "600"))        # 10 min
BURST_MAX = int(os.getenv("TELEGRAM_GUARD_BURST_MAX", "3"))                 # 3 per window
PRUNE_AFTER_SEC = 3600


def _manual_only() -> bool:
    return os.getenv("TELEGRAM_MANUAL_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"}


def _hash(text: str, chat_id: str, purpose: str) -> str:
    return hashlib.sha256(f"{purpose}|{chat_id}|{text}".encode("utf-8", "ignore")).hexdigest()[:16]


def _load() -> dict:
    try:
        return json.loads(STORE.read_text())
    except Exception:
        return {"sends": []}


def _save(data: dict) -> None:
    cutoff = time.time() - PRUNE_AFTER_SEC
    data["sends"] = [s for s in data.get("sends", []) if s.get("ts", 0) >= cutoff][-500:]
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(json.dumps(data, indent=2))
    except Exception as exc:
        logger.warning("guard store write failed: %s", exc)


def allow_send(text: str, chat_id: str, purpose: str = "general", *, force: bool = False, is_auto: bool = False) -> tuple[bool, str]:
    """Return (allowed, reason). Does NOT record — call record_send() after a real send."""
    if force:
        return True, "forced"
    if is_auto and _manual_only():
        return False, "manual_only_blocks_auto"
    now = time.time()
    sends = _load().get("sends", [])
    h = _hash(text, str(chat_id), purpose)

    for s in sends:
        if s.get("hash") == h and now - s.get("ts", 0) < DEDUP_WINDOW_SEC:
            return False, f"duplicate_within_{DEDUP_WINDOW_SEC}s"

    if is_auto:
        for s in sends:
            if s.get("purpose") == purpose and s.get("auto") and now - s.get("ts", 0) < AUTO_COOLDOWN_SEC:
                return False, f"auto_cooldown_{AUTO_COOLDOWN_SEC}s"

    recent = [s for s in sends if s.get("purpose") == purpose and now - s.get("ts", 0) < BURST_WINDOW_SEC]
    if len(recent) >= BURST_MAX:
        return False, f"burst_limit_{BURST_MAX}_per_{BURST_WINDOW_SEC}s"

    return True, "allowed"


def record_send(text: str, chat_id: str, purpose: str = "general", *, is_auto: bool = False) -> None:
    data = _load()
    data.setdefault("sends", []).append({
        "hash": _hash(text, str(chat_id), purpose),
        "ts": time.time(),
        "purpose": purpose,
        "auto": is_auto,
        "chat_tail": str(chat_id)[-4:],  # masked, never the full id
    })
    _save(data)


def guarded(send_fn, text: str, chat_id: str, purpose: str = "general", *, force: bool = False, is_auto: bool = False) -> bool:
    """Run send_fn() only if allowed; record on success. send_fn must return truthy on success.

    Never raises — guard failures fail open to the caller's own error handling, but a
    suppression returns False without sending.
    """
    try:
        allowed, reason = allow_send(text, chat_id, purpose, force=force, is_auto=is_auto)
    except Exception as exc:
        logger.warning("guard check failed (%s); allowing send", exc)
        allowed, reason = True, "guard_error_fail_open"
    if not allowed:
        logger.info("telegram_send_guard SUPPRESSED purpose=%s reason=%s", purpose, reason)
        return False
    ok = bool(send_fn())
    if ok:
        try:
            record_send(text, chat_id, purpose, is_auto=is_auto)
        except Exception as exc:
            logger.warning("guard record failed: %s", exc)
    return ok
