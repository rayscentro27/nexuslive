#!/usr/bin/env python3
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.hermes_roadmap_intelligence import next_steps, roadmap_summary, tester_readiness_view, update_task_status
from lib.hermes_supabase_first import nexus_knowledge_reply


def check(label: str, ok: bool) -> bool:
    print(f"{'[PASS]' if ok else '[FAIL]'} {label}")
    return ok


def main() -> int:
    ok = True
    s = roadmap_summary()
    ok &= check("roadmap loads", isinstance(s, dict) and int(s.get("total_tasks") or 0) >= 30)

    steps = next_steps(limit=20)
    ok &= check("next steps engine returns list", isinstance(steps, list) and len(steps) >= 10)

    t = tester_readiness_view()
    ok &= check("tester readiness shape", "tester_readiness_percent" in t)

    updated = update_task_status(3, "paused")
    ok &= check("task status update works", isinstance(updated, dict) and updated.get("status") == "paused")

    responses = [
        nexus_knowledge_reply("What should we work on next?"),
        nexus_knowledge_reply("What are the next 20 steps?"),
        nexus_knowledge_reply("Hermes do task 1"),
        nexus_knowledge_reply("What did we learn?"),
        nexus_knowledge_reply("What systems are weak?"),
        nexus_knowledge_reply("What should Claude Code review?"),
        nexus_knowledge_reply("Show updated roadmap"),
    ]
    ok &= check("conversational roadmap commands parse", all(isinstance(r, str) and len(r) > 0 for r in responses))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
