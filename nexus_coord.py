#!/usr/bin/env python3
"""
Nexus Agent Coordination Helper

Shared by Claude Code, VS Code/Codex, and Hermes to sync via Supabase.

Common usage:
  python3 nexus_coord.py tasks codex
  python3 nexus_coord.py log codex modified "Updated worker recovery logic" scripts/ai_status.sh
  python3 nexus_coord.py task-done 42
  python3 nexus_coord.py activity --limit 20
  python3 nexus_coord.py summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
BASE_URL = f"{SUPABASE_URL}/rest/v1" if SUPABASE_URL else ""
REQUEST_TIMEOUT = 12

AGENT_ALIASES = {
    "claude": "claude-code",
    "claude-code": "claude-code",
    "codex": "codex",
    "vscode": "codex",
    "hermes": "hermes",
    "telegram": "hermes",
    "all": "all",
}


def die(message: str, code: int = 1) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(code)


def ensure_config() -> None:
    if not BASE_URL or not SUPABASE_KEY:
        die("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be set")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_agent(agent: str) -> str:
    normalized = AGENT_ALIASES.get(agent.strip().lower())
    return normalized or agent.strip()


def request(path: str, *, method: str = "GET", body: object | None = None, prefer: str | None = None) -> tuple[int, object, dict]:
    ensure_config()
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/{path}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = resp.read()
            payload = json.loads(raw) if raw else None
            return resp.status, payload, dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw = err.read()
        payload = None
        if raw:
            try:
                payload = json.loads(raw)
            except Exception:
                payload = raw.decode("utf-8", errors="ignore")
        return err.code, payload, dict(err.headers)
    except Exception as err:
        die(f"Supabase request failed: {err}")


def format_http_error(status: int, payload: object) -> str:
    if isinstance(payload, dict):
        return payload.get("message") or payload.get("hint") or payload.get("code") or str(payload)
    if isinstance(payload, list):
        return json.dumps(payload)[:200]
    return str(payload)[:200]


def log_activity(agent: str, action: str, description: str, file_path: str | None = None, metadata: dict | None = None) -> object:
    row = {
        "agent": normalize_agent(agent),
        "action": action,
        "description": description,
        "file_path": file_path,
        "metadata": metadata or {},
    }
    status, payload, _ = request("coord_activity", method="POST", body=[row], prefer="return=representation")
    if status >= 300:
        die(f"Could not log activity: {format_http_error(status, payload)}")
    print(f"✅ Logged: [{row['agent']}] {action} — {description}")
    if file_path:
        print(f"   file: {file_path}")
    return payload


def get_tasks(agent: str) -> list[dict]:
    agent = normalize_agent(agent)
    path = (
        "coord_tasks"
        "?select=*"
        f"&assigned_to=in.({urllib.parse.quote(agent)},{urllib.parse.quote('all')})"
        "&status=eq.pending"
        "&order=priority.desc"
        "&order=created_at.asc"
    )
    status, payload, _ = request(path)
    if status >= 300:
        die(f"Could not fetch tasks: {format_http_error(status, payload)}")
    tasks = payload or []
    if not tasks:
        print(f"No pending tasks for {agent}")
        return []

    print(f"\n📋 Pending tasks for {agent}:")
    for task in tasks:
        description = task.get("description")
        priority = (task.get("priority") or "normal").upper()
        assigned_to = task.get("assigned_to")
        print(f"  [{task['id']}] ({priority}) {task['title']}  → {assigned_to}")
        if description:
            print(f"       {description}")
    return tasks


def update_task(task_id: int, updates: dict, success_message: str) -> None:
    query = f"coord_tasks?id=eq.{task_id}"
    status, payload, _ = request(query, method="PATCH", body=updates, prefer="return=representation")
    if status >= 300:
        die(f"Could not update task {task_id}: {format_http_error(status, payload)}")
    print(success_message)


def complete_task(task_id: int) -> None:
    update_task(
        task_id,
        {"status": "done", "completed_at": now_iso()},
        f"✅ Task {task_id} marked done",
    )


def claim_task(task_id: int, agent: str) -> None:
    update_task(
        task_id,
        {"status": "in_progress", "claimed_at": now_iso(), "assigned_to": normalize_agent(agent)},
        f"🔄 Task {task_id} claimed by {normalize_agent(agent)}",
    )


def add_task(assigned_to: str, title: str, description: str | None = None, priority: str = "normal", posted_by: str = "user") -> int:
    row = {
        "assigned_to": normalize_agent(assigned_to),
        "title": title,
        "description": description,
        "priority": priority,
        "posted_by": normalize_agent(posted_by) if posted_by != "user" else posted_by,
    }
    status, payload, _ = request("coord_tasks", method="POST", body=[row], prefer="return=representation")
    if status >= 300:
        die(f"Could not create task: {format_http_error(status, payload)}")
    task_id = payload[0]["id"]
    print(f"✅ Task #{task_id} created for {row['assigned_to']}: {title}")
    return task_id


def get_activity(limit: int = 20, agent: str | None = None) -> list[dict]:
    path = f"coord_activity?select=*&order=created_at.desc&limit={limit}"
    if agent:
        path += f"&agent=eq.{urllib.parse.quote(normalize_agent(agent))}"
    status, payload, _ = request(path)
    if status >= 300:
        die(f"Could not fetch activity: {format_http_error(status, payload)}")
    entries = payload or []
    if not entries:
        print("No recent activity")
        return []

    label = normalize_agent(agent) if agent else "all agents"
    print(f"\n📜 Recent activity ({label}, last {len(entries)}):")
    for entry in entries:
        timestamp = (entry.get("created_at") or "")[:16].replace("T", " ")
        file_path = f" → {entry['file_path']}" if entry.get("file_path") else ""
        print(f"  {timestamp} [{entry['agent']}] {entry['action']}: {entry['description']}{file_path}")
    return entries


def get_context() -> list[dict]:
    status, payload, _ = request("coord_context?select=*&order=key.asc")
    if status >= 300:
        die(f"Could not fetch context: {format_http_error(status, payload)}")
    entries = payload or []
    print("\n🧠 Shared Context:")
    if not entries:
        print("  (empty)")
        return []
    for entry in entries:
        print(f"  {entry['key']}: {entry['value']}  (by {entry['updated_by']})")
    return entries


def set_context(key: str, value: str, agent: str) -> None:
    row = {
        "key": key,
        "value": value,
        "updated_by": normalize_agent(agent),
        "updated_at": now_iso(),
    }
    status, payload, _ = request("coord_context", method="POST", body=[row], prefer="resolution=merge-duplicates,return=representation")
    if status >= 300:
        die(f"Could not set context: {format_http_error(status, payload)}")
    print(f"✅ Context set: {key} = {value}")


def summary() -> None:
    get_context()
    get_activity(limit=10)
    for agent in ("claude-code", "codex", "hermes"):
        get_tasks(agent)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Nexus agent coordination helper")
    subparsers = parser.add_subparsers(dest="command")

    log_parser = subparsers.add_parser("log", help="Log agent activity")
    log_parser.add_argument("agent")
    log_parser.add_argument("action")
    log_parser.add_argument("description")
    log_parser.add_argument("file_path", nargs="?")

    tasks_parser = subparsers.add_parser("tasks", help="List pending tasks for an agent")
    tasks_parser.add_argument("agent")

    task_done_parser = subparsers.add_parser("task-done", help="Mark a task as done")
    task_done_parser.add_argument("task_id", type=int)

    task_claim_parser = subparsers.add_parser("task-claim", help="Claim a task for an agent")
    task_claim_parser.add_argument("task_id", type=int)
    task_claim_parser.add_argument("agent")

    add_task_parser = subparsers.add_parser("add-task", help="Create a coordination task")
    add_task_parser.add_argument("assigned_to")
    add_task_parser.add_argument("title")
    add_task_parser.add_argument("description", nargs="?")
    add_task_parser.add_argument("--priority", default="normal")
    add_task_parser.add_argument("--posted-by", default="user")

    activity_parser = subparsers.add_parser("activity", help="Show recent coordination activity")
    activity_parser.add_argument("--limit", type=int, default=20)
    activity_parser.add_argument("--agent")

    subparsers.add_parser("context", help="Show shared context")

    set_context_parser = subparsers.add_parser("set-context", help="Set a shared context key")
    set_context_parser.add_argument("key")
    set_context_parser.add_argument("value")
    set_context_parser.add_argument("agent")

    subparsers.add_parser("summary", help="Show activity, context, and task summary")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        summary()
        return

    if args.command == "log":
        log_activity(args.agent, args.action, args.description, args.file_path)
    elif args.command == "tasks":
        get_tasks(args.agent)
    elif args.command == "task-done":
        complete_task(args.task_id)
    elif args.command == "task-claim":
        claim_task(args.task_id, args.agent)
    elif args.command == "add-task":
        add_task(args.assigned_to, args.title, args.description, priority=args.priority, posted_by=args.posted_by)
    elif args.command == "activity":
        get_activity(limit=args.limit, agent=args.agent)
    elif args.command == "context":
        get_context()
    elif args.command == "set-context":
        set_context(args.key, args.value, args.agent)
    elif args.command == "summary":
        summary()
    else:
        parser.print_help()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
