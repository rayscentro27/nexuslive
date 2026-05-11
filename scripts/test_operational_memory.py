#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from telegram_bot import NexusTelegramBot, OPS_MEMORY_FILE
from lib import hermes_ops_memory


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    bak = None
    if os.path.exists(OPS_MEMORY_FILE):
        with open(OPS_MEMORY_FILE, "r", encoding="utf-8") as f:
            bak = f.read()

    try:
        old_url = os.environ.get("SUPABASE_URL")
        old_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        old_key2 = os.environ.get("SUPABASE_KEY")
        os.environ["SUPABASE_URL"] = ""
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
        os.environ["SUPABASE_KEY"] = ""

        sample = {
            "latest_daily_plan": ["Funding workflow review", "Telegram routing verification"],
            "task_lifecycle": {"abc": "queued", "def": "failed"},
            "pending_approval": {"task": "deploy release", "reason": "deployment action"},
            "recent_completed": [{"task": "Telegram routing verification"}],
            "recent_failed": [{"task": "Funding workflow review", "reason": "timeout"}],
            "active_priorities": ["Funding workflow review"],
            "blocked_priorities": ["deploy release"],
            "completed_priorities": ["Telegram routing verification"],
            "recent_recommendations": ["Funding workflow review"],
        }
        with open(OPS_MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sample, f)

        bot = NexusTelegramBot.__new__(NexusTelegramBot)
        bot.ops_memory = NexusTelegramBot._load_operational_memory(bot)
        bot.last_plan_items = list(bot.ops_memory.get("latest_daily_plan", []))
        bot.task_lifecycle = dict(bot.ops_memory.get("task_lifecycle", {}))
        bot.pending_approval_action = bot.ops_memory.get("pending_approval")

        ok &= check("plan_survives_restart", bot.last_plan_items[:1] == ["Funding workflow review"])
        ok &= check("pending_approvals_survive_restart", bool(bot.pending_approval_action))
        ok &= check("failed_task_memory_survives_restart", "failed" in str(bot.task_lifecycle.values()).lower())

        s1 = NexusTelegramBot._resume_previous_work_summary(bot)
        ok &= check("resume_previous_work_uses_persisted_snapshot", "resuming previous work" in s1.lower())

        s2 = NexusTelegramBot._active_priorities_summary(bot)
        ok &= check("what_are_we_working_on_summary", "working on" in s2.lower() or "active priorities" in s2.lower())

        s3 = NexusTelegramBot._plan_item_status(bot, 2)
        ok &= check("did_we_finish_item_2_resolution", "item 2" in s3.lower())

        s4 = NexusTelegramBot._plan_item_status(bot, 1)
        ok &= check("did_we_finish_item_1_resolution", "item 1" in s4.lower())

        s5 = NexusTelegramBot._plan_item_status(bot, 3)
        ok &= check("did_we_finish_item_3_resolution", "item" in s5.lower())

        if old_url is not None:
            os.environ["SUPABASE_URL"] = old_url
        if old_key is not None:
            os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_key
        if old_key2 is not None:
            os.environ["SUPABASE_KEY"] = old_key2

        mem = hermes_ops_memory.load_memory(updated_by="test")
        ok &= check("supabase_down_fallback_to_local_json", isinstance(mem, dict) and bool(mem.get("updated_at")))

        merged = hermes_ops_memory.load_memory(updated_by="test_reconcile")
        ok &= check(
            "reconcile_prefers_live_approval_queue_over_stale_local",
            isinstance(merged.get("pending_approval_refs"), list),
        )

        ws = hermes_ops_memory.start_work_session(merged, "Stabilize Telegram operations", updated_by="test_ws_start")
        ok &= check("work_session_start", bool(ws.get("active_work_session_id")))
        ws_sum = hermes_ops_memory.summarize_work_session(ws)
        ok &= check("work_session_summarize", "work session" in ws_sum.lower())

        ws2 = hermes_ops_memory.pause_work_session(ws, updated_by="test_ws_pause")
        ok &= check("work_session_pause", ws2.get("active_work_session_id") is None)

        ws3 = hermes_ops_memory.resume_work_session(ws2, updated_by="test_ws_resume")
        ok &= check("work_session_resume", bool(ws3.get("active_work_session_id")))

        ws_reload = hermes_ops_memory.load_memory(updated_by="test_ws_reload")
        ok &= check("work_session_persists_restart", isinstance(ws_reload.get("work_sessions"), list) and len(ws_reload.get("work_sessions")) > 0)
    finally:
        if 'old_url' in locals():
            if old_url is None:
                os.environ.pop("SUPABASE_URL", None)
            else:
                os.environ["SUPABASE_URL"] = old_url
        if 'old_key' in locals():
            if old_key is None:
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            else:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = old_key
        if 'old_key2' in locals():
            if old_key2 is None:
                os.environ.pop("SUPABASE_KEY", None)
            else:
                os.environ["SUPABASE_KEY"] = old_key2
        if bak is None:
            try:
                os.remove(OPS_MEMORY_FILE)
            except FileNotFoundError:
                pass
        else:
            with open(OPS_MEMORY_FILE, "w", encoding="utf-8") as f:
                f.write(bak)

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
