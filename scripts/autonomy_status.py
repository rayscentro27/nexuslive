#!/usr/bin/env python3
"""
Shared autonomy status source for Nexus operator surfaces.

Provides one structured view that Hermes, email, and humans can all reference.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path


ROOT = Path("/Users/raymonddavis/nexus-ai")
CHECK_SCRIPT = ROOT / "scripts" / "check_autonomy_stack.sh"
TRADING_STATUS_SCRIPT = ROOT / "scripts" / "trading_autonomy_status.py"
STRATEGY_TESTER_STATUS_FILE = ROOT / "logs" / "strategy_tester_status.json"
SCHEDULER_LOG = ROOT / "hermes" / "logs" / "scheduler.log"
SCHEDULER_ERR_LOG = ROOT / "hermes" / "logs" / "scheduler.err.log"


def run_command(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=90,
    )


def parse_check_output(raw: str) -> dict:
    lines = raw.splitlines()

    def first(pattern: str) -> str:
        for line in lines:
            if pattern in line:
                return line.strip()
        return ""

    return {
        "openrouter": first("model="),
        "gmail": first("@gmail.com"),
        "email_pipeline": first("Email pipeline"),
        "scheduler": first("Scheduler"),
        "hermes_gateway": first("Hermes gateway"),
        "fail_lines": [line.strip() for line in lines if "FAIL" in line],
    }


def pending_task_count(agent: str) -> int:
    result = run_command(["python3", "nexus_coord.py", "tasks", agent], cwd=ROOT)
    return sum(1 for line in (result.stdout or "").splitlines() if line.strip().startswith("- ["))


def tail_matches(path: Path, markers: tuple[str, ...], limit: int = 3) -> list[str]:
    if not path.exists():
        return []
    matches = []
    for line in path.read_text(errors="ignore").splitlines()[-120:]:
        if any(marker in line for marker in markers):
            matches.append(line.strip())
    return matches[-limit:]


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def build_status() -> dict:
    checked_at = datetime.now().strftime("%Y-%m-%d %H:%M MST")

    check_result = run_command([str(CHECK_SCRIPT)], cwd=ROOT)
    raw = (check_result.stdout or "").strip()
    parsed = parse_check_output(raw)

    recent_activity = tail_matches(
        SCHEDULER_LOG,
        (
            "Lead check done",
            "Reputation check done",
            "Signal analysis done",
            "Research pipeline done",
            "Email summary sent",
            "Checking leads",
        ),
    )
    recent_errors = tail_matches(
        SCHEDULER_ERR_LOG,
        ("ERROR", "WARN", "FAIL", "Traceback"),
        limit=5,
    )

    tasks = {
        "codex": pending_task_count("codex"),
        "hermes": pending_task_count("hermes"),
        "claude-code": pending_task_count("claude-code"),
    }

    trading = {}
    trading_result = run_command(["python3", str(TRADING_STATUS_SCRIPT), "--format", "json"], cwd=ROOT)
    if trading_result.returncode == 0 and (trading_result.stdout or "").strip():
        try:
            trading = json.loads(trading_result.stdout)
        except Exception:
            trading = {}

    strategy_testing = read_json(STRATEGY_TESTER_STATUS_FILE)

    overall = "healthy" if not parsed["fail_lines"] else "needs_attention"

    return {
        "checked_at": checked_at,
        "overall": overall,
        "checks": parsed,
        "tasks": tasks,
        "trading": trading,
        "strategy_testing": strategy_testing,
        "recent_activity": recent_activity,
        "recent_errors": recent_errors,
        "raw_check_output": raw,
    }


def print_brief(status: dict) -> None:
    checks = status["checks"]
    tasks = status["tasks"]
    recent = status["recent_activity"][-1] if status["recent_activity"] else "No recent scheduler summary line found"
    print(f"Hermes brief status — {status['checked_at']}")
    print(f"OpenRouter: {checks.get('openrouter') or 'unknown'}")
    print(f"Gmail: {checks.get('gmail') or 'unknown'}")
    print(
        "Agents: "
        f"{checks.get('email_pipeline') or 'email unknown'} | "
        f"{checks.get('scheduler') or 'scheduler unknown'} | "
        f"{checks.get('hermes_gateway') or 'hermes unknown'}"
    )
    print(
        "Pending tasks: "
        f"codex={tasks['codex']} hermes={tasks['hermes']} claude-code={tasks['claude-code']}"
    )
    trading = status.get("trading") or {}
    if trading:
        saved = trading.get("saved_status") or {}
        receiver_ok = "error" not in (trading.get("health") or {})
        print(
            "Trading: "
            f"{'paper' if saved.get('dry_run', True) else 'live'} / "
            f"{'auto' if saved.get('auto_trading') else 'manual'} / "
            f"receiver={'ok' if receiver_ok else 'down'}"
        )
    strategy = status.get("strategy_testing") or {}
    if strategy:
        summary = strategy.get("summary") or {}
        top = (strategy.get("top_strategies") or [None])[0]
        top_label = top.get("strategy_id") if top else "none"
        print(
            "Strategy tester: "
            f"eligible={summary.get('eligible_candidate_count', 0)} / "
            f"top={top_label}"
        )
    print(f"Recent activity: {recent}")
    print("Full detail goes to email/logs if needed.")


def print_attention(status: dict) -> None:
    print(f"Needs attention — {status['checked_at']}")
    if status["checks"]["fail_lines"]:
        print("Stack warnings:")
        for line in status["checks"]["fail_lines"][:3]:
            print(line)
    else:
        print("Stack warnings: none right now")
    tasks = status["tasks"]
    print(
        "Pending tasks: "
        f"codex={tasks['codex']} hermes={tasks['hermes']} claude-code={tasks['claude-code']}"
    )
    if status["recent_errors"]:
        print("Recent errors:")
        for line in status["recent_errors"][-2:]:
            print(line)
    else:
        print("Recent errors: none in scheduler tail")
    trading = status.get("trading") or {}
    if trading:
        saved = trading.get("saved_status") or {}
        if "error" in (trading.get("health") or {}):
            print("Trading warning: receiver health check failed")
        else:
            print(
                "Trading: "
                f"{'paper' if saved.get('dry_run', True) else 'live'} / "
                f"{'auto' if saved.get('auto_trading') else 'manual'}"
            )
    strategy = status.get("strategy_testing") or {}
    if strategy:
        warnings = strategy.get("warnings") or []
        summary = strategy.get("summary") or {}
        if warnings:
            print(f"Strategy tester: {warnings[0]}")
        else:
            print(
                "Strategy tester: "
                f"eligible={summary.get('eligible_candidate_count', 0)} "
                f"submitted={summary.get('submitted_candidate_count', 0)}"
            )
    print("Full detail goes to email/logs if needed.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "brief", "attention", "full"), default="json")
    args = parser.parse_args()

    status = build_status()
    if args.format == "json":
        print(json.dumps(status, indent=2))
    elif args.format == "brief":
        print_brief(status)
    elif args.format == "attention":
        print_attention(status)
    else:
        print(status["raw_check_output"])


if __name__ == "__main__":
    main()
