"""
report.py — Structured Hermes Report format.
Every response from the command router uses this format.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


StatusLevel = str  # "healthy" | "warning" | "critical" | "blocked" | "unknown"


def build(
    status: StatusLevel,
    what_happened: str,
    evidence: list[str],
    recommendation: str,
    action_needed: str = "none",
    next_best_step: str = "",
    command: str = "",
) -> str:
    """Return a formatted Hermes Report as plain text."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    status_emoji = {
        "healthy":  "✅",
        "warning":  "⚠️",
        "critical": "🚨",
        "blocked":  "🔴",
        "unknown":  "❓",
    }.get(status, "❓")

    lines = [
        "═" * 52,
        f"  HERMES REPORT  {ts}",
        "═" * 52,
    ]
    if command:
        lines += [f"  Command: {command}", ""]

    lines += [
        f"Status: {status_emoji} {status.upper()}",
        "",
        "What Happened:",
        f"  {what_happened}",
        "",
        "Evidence:",
    ]
    for e in evidence:
        lines.append(f"  • {e}")

    lines += [
        "",
        "Recommendation:",
        f"  {recommendation}",
        "",
        f"Action Needed From You: {action_needed}",
    ]

    if next_best_step:
        lines += ["", f"Next Best Step: {next_best_step}"]

    lines.append("═" * 52)
    return "\n".join(lines)


def build_telegram(
    status: StatusLevel,
    what_happened: str,
    evidence: list[str],
    recommendation: str,
    action_needed: str = "none",
    next_best_step: str = "",
) -> str:
    """Return HTML-formatted version for Telegram."""
    status_emoji = {
        "healthy":  "✅",
        "warning":  "⚠️",
        "critical": "🚨",
        "blocked":  "🔴",
        "unknown":  "❓",
    }.get(status, "❓")

    ev_lines = "\n".join(f"  • {e}" for e in evidence)
    nbs = f"\n<b>Next Best Step:</b> {next_best_step}" if next_best_step else ""

    return (
        f"<b>Hermes Report</b>\n\n"
        f"<b>Status:</b> {status_emoji} {status.upper()}\n\n"
        f"<b>What Happened:</b>\n{what_happened}\n\n"
        f"<b>Evidence:</b>\n{ev_lines}\n\n"
        f"<b>Recommendation:</b>\n{recommendation}\n\n"
        f"<b>Action Needed:</b> {action_needed}"
        f"{nbs}"
    )
