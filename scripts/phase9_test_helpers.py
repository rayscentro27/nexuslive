"""Shared helpers for Phase 9 routing cleanup tests."""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BANNED_EVIDENCE_MARKERS = (
    "artifact_inventory",
    "handoff dump",
    "i can answer from verified artifacts",
    "strategic context from evidence",
    "i wasn't able to generate a quality response",
)


def make_bot():
    os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
    os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"
    import telegram_bot

    telegram_bot.NexusTelegramBot.test_connection = lambda self: None
    return telegram_bot.NexusTelegramBot()


def latest_file(pattern: str) -> Path:
    matches = sorted(glob.glob(str(ROOT / pattern)))
    if not matches:
        raise FileNotFoundError(pattern)
    return Path(matches[-1])


def latest_json(pattern: str) -> dict:
    return json.loads(latest_file(pattern).read_text(encoding="utf-8"))


def latest_text(pattern: str) -> str:
    return latest_file(pattern).read_text(encoding="utf-8")


def cleanup_env() -> None:
    os.environ.pop("HERMES_CFO_LOOP_MODE", None)
    os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)
