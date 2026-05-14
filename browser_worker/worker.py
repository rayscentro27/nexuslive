#!/usr/bin/env python3
"""
Nexus Autonomous Browser Worker
Polls browser_tasks table, executes tasks with Playwright + Hermes, reports to Telegram.

Usage:
    python3 worker.py                   # run worker loop
    python3 worker.py --once <type>     # run one task type immediately
    python3 worker.py --status          # show recent tasks

Task types:
    oracle_check      — OCI ARM instance status via CLI
    stripe_check      — Recent Stripe events + webhook health
    nexuslive_check   — Load nexuslive site and check key elements
    supabase_check    — Verify Supabase tables are healthy
    open              — LLM-driven free-form task (payload.task = "description")
"""

import os
import sys
import json
import time
import logging
import asyncio
import importlib
from pathlib import Path
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BROWSER] %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / "logs" / "browser_worker.log"),
    ],
)
logger = logging.getLogger("BrowserWorker")

POLL_INTERVAL = 30  # seconds between queue checks
SCRIPTED_TASKS = {
    "oracle_check":    "browser_worker.tasks.oracle_check",
    "stripe_check":    "browser_worker.tasks.stripe_check",
    "nexuslive_check": "browser_worker.tasks.nexuslive_check",
    "supabase_check":  "browser_worker.tasks.supabase_check",
}


def _send_telegram(text: str):
    from lib.hermes_gate import send as gate_send

    gate_send(text, event_type="critical_alert", severity="critical")


async def run_task(task: dict) -> dict:
    """Execute a single browser task. Returns result dict."""
    task_type = task.get("task_type", "")
    payload = task.get("payload", {}) or {}
    logger.info(f"Running task: {task_type} (id={task['id']})")

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--memory-pressure-off",
            ],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        try:
            if task_type in SCRIPTED_TASKS:
                module = importlib.import_module(SCRIPTED_TASKS[task_type])
                result = await module.run(page, payload)
            elif task_type == "open":
                from browser_worker.llm_executor import run_open_task
                task_desc = payload.get("task", "Check the current page and report what you see")
                start_url = payload.get("url", "about:blank")
                if start_url != "about:blank":
                    await page.goto(start_url, wait_until="domcontentloaded", timeout=20000)
                result = await run_open_task(page, task_desc)
            else:
                result = {"status": "error", "summary": f"Unknown task type: {task_type}"}
        except Exception as e:
            result = {"status": "error", "summary": f"Task crashed: {str(e)[:200]}"}
            logger.exception(f"Task {task_type} crashed")
        finally:
            await browser.close()

    return result


async def process_task(task: dict):
    from browser_worker.task_queue import complete_task

    task_type = task.get("task_type", "?")
    task_id = task["id"]

    result = await run_task(task)
    summary = result.get("summary", "")
    error = result.get("summary") if result.get("status") == "error" else None

    complete_task(
        task_id=task_id,
        result=json.dumps(result, default=str),
        error=error,
        screenshot_url=None,
    )

    # Telegram notification
    requested_by = task.get("requested_by", "system")
    icon = "✅" if result.get("status") == "ok" else "❌"
    msg = (
        f"{icon} <b>Browser Task: {task_type}</b>\n"
        f"Requested by: {requested_by}\n\n"
        f"{summary[:800]}"
    )
    if result.get("status") == "error":
        _send_telegram(msg)
    logger.info(f"Task {task_id} done — {result.get('status','?')}")


async def worker_loop():
    from browser_worker.task_queue import claim_next_task

    logger.info("🌐 Browser Worker started — polling every %ds", POLL_INTERVAL)
    logger.info("Telegram startup notice suppressed by policy")

    while True:
        try:
            task = claim_next_task()
            if task:
                await process_task(task)
            else:
                await asyncio.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("Shutting down.")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(POLL_INTERVAL)


async def run_once(task_type: str, payload: dict = None):
    """Run one task immediately without touching the DB queue."""
    fake_task = {
        "id": 0,
        "task_type": task_type,
        "payload": payload or {},
        "requested_by": "cli",
    }
    result = await run_task(fake_task)
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Nexus Browser Worker")
    p.add_argument("--once", metavar="TASK_TYPE",
                   choices=list(SCRIPTED_TASKS.keys()) + ["open"],
                   help="Run one task immediately and exit")
    p.add_argument("--task", metavar="DESCRIPTION",
                   help="Task description for --once open")
    p.add_argument("--url", metavar="URL",
                   help="Starting URL for --once open")
    p.add_argument("--status", action="store_true",
                   help="Show recent tasks from queue")
    args = p.parse_args()

    if args.status:
        from browser_worker.task_queue import get_recent_tasks
        tasks = get_recent_tasks(limit=10)
        for t in tasks:
            ts = t.get("created_at", "?")[:16]
            print(f"[{ts}] {t['task_type']:<20} {t['status']:<10} {t.get('requested_by','?')}")
    elif args.once:
        payload = {}
        if args.task:
            payload["task"] = args.task
        if args.url:
            payload["url"] = args.url
        asyncio.run(run_once(args.once, payload))
    else:
        asyncio.run(worker_loop())
