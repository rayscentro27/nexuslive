"""
hermes_active_memory_reader.py — Unified safe interface for live Telegram memory.

This is the SOLE entry point for Telegram-facing code that reads executive
memory.  It enforces the Hermes Memory Safety Contract (Rule 3):

  - Returns empty/neutral data when Supabase is unreachable or empty
  - NEVER falls back to hardcoded archived defaults
  - All reads are logged with source tag for audit
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("HermesActiveMemoryReader")

ROOT = Path(__file__).resolve().parent.parent

CATEGORIES = [
    "monetization_priorities",
    "business_goals",
    "affiliate_campaigns",
    "content_backlog",
    "unfinished_systems",
    "infrastructure_problems",
    "active_workers",
    "operational_philosophy",
    "execution_priorities",
]

_CACHE: dict | None = None
_CACHE_TS: float = 0.0
_CACHE_TTL = 120


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase_env() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return url, key


def _sb_select(path: str, timeout: int = 8) -> list[dict]:
    import urllib.request
    url, key = _supabase_env()
    if not url or not key:
        return []
    try:
        req = urllib.request.Request(
            f"{url}/rest/v1/{path}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return []


def _empty_memory() -> dict:
    """Return a neutral memory dict — NO stale defaults that impersonate live state.

    Per Memory Safety Contract Rule 1: all categories except operational_philosophy
    are empty.  operational_philosophy contains standing safety directives (not stale
    live-state impersonation).
    """
    return {cat: [] for cat in CATEGORIES} | {
        "operational_philosophy": [
            "NEXUS_DRY_RUN=true always — never publish, bill, or deploy without approval",
            "Evidence-first: no task marked complete without evidence_ref",
            "Safe autonomous mode: workers generate drafts, human approves publication",
            "Paper trading only — 6-month verified performance minimum before live",
            "No guaranteed income claims or financial guarantees in any output",
        ],
        "updated_at": _now_iso(),
        "version": 1,
        "source": "active_memory_reader_empty",
    }


def _neutral_context_message() -> str:
    return (
        "[Executive memory is empty or unavailable. "
        "Run `nexus executive status` to check the live state.]"
    )


def load_active_memory(force_refresh: bool = False) -> dict:
    """Load memory from Supabase only. Returns empty/neutral on failure or empty DB.

    This is the safe replacement for hermes_executive_memory.load_memory()
    in all Telegram-facing code paths.
    """
    global _CACHE, _CACHE_TS

    if not force_refresh and _CACHE and (time.monotonic() - _CACHE_TS < _CACHE_TTL):
        return _CACHE

    rows = _sb_select(
        "hermes_executive_memory?select=category,items,updated_at"
        "&order=category.asc&limit=20"
    )
    if rows:
        mem = {cat: [] for cat in CATEGORIES}
        all_empty = True
        for row in rows:
            cat = row.get("category")
            items = row.get("items")
            if cat in CATEGORIES and isinstance(items, list) and items:
                mem[cat] = items
                all_empty = False
        mem["updated_at"] = max(
            (r.get("updated_at", "") for r in rows), default=_now_iso()
        )
        mem["version"] = 1
        mem["source"] = "active_memory_reader_supabase"
        if all_empty:
            mem = _empty_memory()
        _CACHE = mem
        _CACHE_TS = time.monotonic()
        return mem

    _CACHE = _empty_memory()
    _CACHE_TS = time.monotonic()
    return _CACHE


def build_telegram_context(max_chars: int = 400) -> str:
    """Compact context snippet for Telegram — returns empty string if no live data."""
    mem = load_active_memory()
    lines: list[str] = []

    priorities = mem.get("execution_priorities", [])[:2]
    if priorities:
        lines.append("Priorities: " + " | ".join(priorities))

    problems = mem.get("infrastructure_problems", [])[:1]
    if problems:
        lines.append("Issues: " + " | ".join(problems))

    if not lines:
        return ""

    return " ".join(lines)[:max_chars]


def build_context_block(max_items_per_category: int = 3) -> str:
    """Return context block for quality escalation — neutral if no live data."""
    mem = load_active_memory()
    sections: list[str] = []
    priority_map = {
        "infrastructure_problems": "INFRASTRUCTURE ISSUES",
        "monetization_priorities": "MONETIZATION",
        "active_workers": "ACTIVE WORKERS",
    }
    for cat, label in priority_map.items():
        items = mem.get(cat, [])[:max_items_per_category]
        if items:
            lines = "\n".join(f"  - {i}" for i in items)
            sections.append(f"**{label}**\n{lines}")

    if not sections:
        return ""

    updated = mem.get("updated_at", "unknown")[:10]
    return f"[Executive Memory — as of {updated}]\n\n" + "\n\n".join(sections)


def active_memory_available() -> bool:
    """Quick check: does Supabase have any non-empty executive memory rows?"""
    mem = load_active_memory()
    return any(mem.get(cat) for cat in CATEGORIES)


def status_summary() -> str:
    """Human-readable summary — clearly notes when data is unavailable."""
    mem = load_active_memory()
    if not any(mem.get(cat) for cat in CATEGORIES):
        return (
            "Active executive memory is empty or unavailable.\n"
            "Use `load_archived_executive_memory_defaults()` to view "
            "the archived baseline, or run `nexus executive status`."
        )
    lines = [
        f"Hermes Active Memory (v{mem.get('version', 1)}, "
        f"updated {mem.get('updated_at', '?')[:10]})",
        "",
    ]
    for cat in CATEGORIES:
        items = mem.get(cat, [])
        label = cat.replace("_", " ").title()
        lines.append(f"[{label}] ({len(items)} items)")
        for item in items[:3]:
            lines.append(f"  * {item}")
        if len(items) > 3:
            lines.append(f"  ... +{len(items) - 3} more")
        lines.append("")
    return "\n".join(lines).strip()
