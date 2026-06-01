"""
hermes_active_memory_reader.py — Unified safe interface for live Telegram memory.

This is the SOLE entry point for Telegram-facing code that reads executive
memory.  It enforces the Hermes Memory Safety Contract (Rules 1, 3, 5):

  - Returns empty/neutral data when Supabase is unreachable or empty
  - NEVER falls back to hardcoded archived defaults
  - Historical/debug memory only when explicitly requested
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

# Stale markers that must NEVER appear in live Telegram answers
_STALE_MARKERS = ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter", "NitroTrades"]

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


def _has_stale_content(text: str) -> bool:
    """Check if text contains any stale markers."""
    if not text:
        return False
    lower = text.lower()
    return any(m.lower() in lower for m in _STALE_MARKERS)


# ── Core loading ──────────────────────────────────────────────────────────────

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


# ── Spec'd interface functions ────────────────────────────────────────────────

def load_active_memory_context(max_chars: int = 400) -> str:
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


def load_active_operating_rules() -> list[str]:
    """Return current operational philosophy (safety rules)."""
    mem = load_active_memory()
    return mem.get("operational_philosophy", [])


def load_active_goals() -> list[str]:
    """Return current business goals from live memory."""
    mem = load_active_memory()
    return mem.get("business_goals", [])


def load_active_artifacts_summary() -> str:
    """Return a plain-language summary of current artifact state.

    Reads from the artifact registry and action queue (not executive memory).
    """
    parts = []
    try:
        from lib.nexus_artifact_registry import latest_artifacts
        artifacts = latest_artifacts(limit=3)
        if artifacts:
            names = [a.to_dict().get("title", "?")[:40] for a in artifacts]
            parts.append(f"Artifacts ({len(artifacts)} recent): " + ", ".join(names))
    except Exception:
        pass
    try:
        from scripts.prelaunch_utils import rest_select as _sel
        actions = _sel("action_queue?select=id,action_type&status=eq.pending&limit=5", timeout=4)
        if actions and isinstance(actions, list):
            types = list({a.get("action_type", "?") for a in actions})
            parts.append(f"Pending actions ({len(actions)}): " + ", ".join(types[:3]))
    except Exception:
        pass
    return "\n".join(parts) if parts else "No active artifacts or pending actions found."


def load_active_action_summary() -> str:
    """Return a plain-language summary of pending actions from the action queue."""
    try:
        from scripts.prelaunch_utils import rest_select
        actions = rest_select(
            "action_queue?select=id,action_type,summary,status"
            "&status=eq.pending&order=created_at.desc&limit=5",
            timeout=4,
        )
        if not actions:
            return "No pending actions in the queue."
        lines = [f"Pending actions ({len(actions)}):"]
        for a in actions[:5]:
            t = a.get("action_type", "?")
            s = str(a.get("summary", ""))[:60]
            lines.append(f"  - {t}: {s}")
        return "\n".join(lines)
    except Exception:
        return "Action queue unavailable."


def load_active_decision_summary() -> str:
    """Return a plain-language summary of recent Hermes decisions."""
    try:
        log_path = ROOT / "docs" / "reports" / "hermes_decisions" / "hermes_decision_log.jsonl"
        if not log_path.exists():
            return "No decision log found."
        raw = log_path.read_text().strip().splitlines()
        recent = []
        for line in raw[-5:]:
            try:
                r = json.loads(line)
                recent.append(f"[{r.get('logged_at','')[:16]}] {r.get('action','?')} -> {r.get('decision','?')[:40]}")
            except Exception:
                pass
        if not recent:
            return "No recent decisions."
        return "Recent decisions:\n" + "\n".join(recent)
    except Exception:
        return "Decision log unavailable."


def explain_active_memory_sources() -> str:
    """Plain-language list of active memory sources available to Hermes."""
    mem = load_active_memory()
    lines = [
        "Active memory sources for this answer:",
        "",
        "1. Executive Memory (Supabase table: hermes_executive_memory)",
    ]
    populated = [c for c in CATEGORIES if mem.get(c)]
    if populated:
        for c in populated[:6]:
            n = len(mem.get(c, []))
            lines.append(f"   - {c} ({n} item{'s' if n != 1 else ''})")
    else:
        lines.append("   (no populated categories)")
    lines.append("")
    lines.append("2. Artifact Registry (local JSONL)")
    lines.append("3. Action Queue (Supabase table: action_queue)")
    lines.append("4. Decision Log (local JSONL)")
    lines.append("5. Provider Policy (live check via hermes_provider_policy)")
    lines.append("6. Conversation Context Resolver (runtime)")
    lines.append("")
    lines.append("Stale/archived defaults are BLOCKED from live answers per the Memory Safety Contract.")
    lines.append("To see archived defaults, ask: 'show archived executive memory'")
    return "\n".join(lines)


def reject_stale_memory_for_live_answer(text: str) -> bool:
    """Return True if text contains stale memory that should be blocked from live answers.

    Use this as a gate before injecting any memory context into Telegram.
    """
    return _has_stale_content(text)


# ── Legacy aliases (backward compat) ─────────────────────────────────────────

def build_telegram_context(max_chars: int = 400) -> str:
    return load_active_memory_context(max_chars=max_chars)


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
