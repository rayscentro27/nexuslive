#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import lib.ai_task_dispatch as dispatch
from lib.ai_task_dispatch import WORKER_DEFINITIONS
from lib.ai_task_worker_bridge import recover_stale_tasks
from lib.hermes_supabase_first import nexus_knowledge_reply


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True

    ok &= check("worker definitions include opencode", "opencode_codex" in WORKER_DEFINITIONS)
    ok &= check("worker definitions include claude", "claude_code" in WORKER_DEFINITIONS)
    ok &= check("worker definitions include openclaude", "openclaude" in WORKER_DEFINITIONS)
    ok &= check("approval gating catches production deploy", dispatch.requires_manual_approval("deploy", "production deploy now") is True)
    ok &= check("approval gating allows safe report", dispatch.requires_manual_approval("report", "write internal report") is False)
    ok &= check("routing to claude for redesign", dispatch.suggest_worker("redesign workforce office ui") == "claude_code")

    created = dispatch.create_task(
        created_by="test",
        source="telegram",
        title="Test task",
        instructions="run safe tests",
    )
    ok &= check("queue creation returns task payload", isinstance(created, dict) and bool(created.get("id")))

    # Hermes command parsing
    r1 = nexus_knowledge_reply("Send this to OpenCode: run scripts and report")
    r2 = nexus_knowledge_reply("What tasks are running?")
    r3 = nexus_knowledge_reply("Pause OpenCode tasks")
    r4 = nexus_knowledge_reply("Resume Claude Code queue")
    ok &= check("Hermes dispatch command parsed", isinstance(r1, str) and "OpenCode" in r1)
    ok &= check("Hermes running tasks command parsed", isinstance(r2, str))
    ok &= check("Hermes pause command parsed", isinstance(r3, str) and "Paused" in r3)
    ok &= check("Hermes resume command parsed", isinstance(r4, str) and "Resumed" in r4)

    # Stale recovery should be safe with empty/no-supabase state
    recovered = recover_stale_tasks(timeout_minutes=1)
    ok &= check("stale task recovery executes", isinstance(recovered, int))

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
