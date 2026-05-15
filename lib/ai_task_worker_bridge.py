from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable

from .ai_task_dispatch import claim_next_task, complete_task, list_tasks


def recover_stale_tasks(timeout_minutes: int = 30) -> int:
    recovered = 0
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
    for row in list_tasks(status="running", limit=100):
        started_at = row.get("started_at")
        if not started_at:
            continue
        try:
            started = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        except Exception:
            continue
        if started < cutoff:
            if complete_task(str(row.get("id")), str(row.get("assigned_worker") or "worker"), "Recovered stale task timeout", status="failed", error_summary="stale task timeout"):
                recovered += 1
    return recovered


def run_worker_loop(worker_id: str, handler: Callable[[dict], tuple[str, str]], poll_seconds: int = 20) -> None:
    concurrency = int(os.getenv("AI_TASK_WORKER_CONCURRENCY", "1"))
    running = 0
    while True:
        recover_stale_tasks(timeout_minutes=int(os.getenv("AI_TASK_STALE_MINUTES", "30")))
        if running >= concurrency:
            time.sleep(poll_seconds)
            continue
        task = claim_next_task(worker_id)
        if not task:
            time.sleep(poll_seconds)
            continue
        running += 1
        try:
            status, summary = handler(task)
            if status not in {"completed", "failed", "waiting_review"}:
                status = "completed"
            complete_task(str(task.get("id")), worker_id, summary, status=status)
        except Exception as exc:
            complete_task(str(task.get("id")), worker_id, f"Worker failure: {exc}", status="failed", error_summary=str(exc))
        finally:
            running = max(0, running - 1)
