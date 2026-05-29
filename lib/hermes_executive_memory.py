"""
Hermes Executive Memory Layer
==============================
Persistent operational intelligence memory with 9 structured categories.
Stored in Supabase (hermes_executive_memory table) + local JSON fallback.
Injected into every major Hermes reasoning cycle for context-grounded replies.

Categories:
  1. monetization_priorities   — current revenue levers in priority order
  2. business_goals            — time-bound measurable goals
  3. affiliate_campaigns       — active/pending affiliate programs
  4. content_backlog           — queued content ideas with status
  5. unfinished_systems        — half-built infrastructure & tech debt
  6. infrastructure_problems   — live issues, degraded services
  7. active_workers            — running/scheduled worker status
  8. operational_philosophy    — standing directives (safety, style, approach)
  9. execution_priorities      — today's top 3-5 must-do items
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("HermesExecutiveMemory")

ROOT = Path(__file__).resolve().parent.parent
LOCAL_FILE = ROOT / ".hermes_executive_memory.json"

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
_CACHE_TTL = 120  # 2-minute cache


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supabase_env() -> tuple[str, str]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    return url, key


def _sb_upsert(table: str, payload: dict, timeout: int = 8) -> bool:
    import urllib.request
    url, key = _supabase_env()
    if not url or not key:
        return False
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/{table}",
            data=data,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception as exc:
        logger.debug("Supabase upsert failed: %s", exc)
        return False


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


# ── Default memory ────────────────────────────────────────────────────────────

def _default_memory() -> dict:
    return {
        "monetization_priorities": [
            "Launch Nexus AI affiliate program via Beehiiv newsletter CTAs",
            "Integrate Lendio/Nav.com affiliate links in SEO articles",
            "Set up YouTube channel monetization (1000 subs target)",
        ],
        "business_goals": [
            "Reach 500 newsletter subscribers by end of Q2 2026",
            "Publish 30 days of consistent content across all channels",
            "Document 6 months paper trading performance before any live consideration",
        ],
        "affiliate_campaigns": [
            "Lendio — small business funding (roi_score: 94) — pending CTA integration",
            "Nav.com — business credit monitoring (roi_score: 92) — pending CTA integration",
            "TubeBuddy — YouTube growth (roi_score: 88) — ready to promote",
        ],
        "content_backlog": [
            "YT script: 'How AI Finds Business Funding in 2026'",
            "Newsletter: Nexus Weekly Digest #1",
            "SEO article: 'Best AI Tools for Small Business Owners'",
            "TikTok hooks: 3x 'AI Money' series",
        ],
        "unfinished_systems": [
            "Beehiiv newsletter — login session pending, forms not yet live",
            "YouTube Studio — 6 profile links not yet added manually",
            "OpenRouter as content-tier provider — not yet in model_routing_rules",
            "7 legacy false completions in agent_dispatch_tasks need remediation",
        ],
        "infrastructure_problems": [
            "Ollama (netcup, localhost:11555) — OFFLINE, content falls back to templates",
            "Oracle VM (161.153.40.41) — online but llm-worker service status unknown",
        ],
        "active_workers": [
            "content_worker — daily pipeline @ 6am (templates when Ollama offline)",
            "research_worker — synthesis pipeline @ 7am",
            "affiliate_worker — audit @ 8am",
            "ceo_brief_worker — morning briefing @ 7am",
            "improvement_worker — continuous improvement queue",
        ],
        "operational_philosophy": [
            "NEXUS_DRY_RUN=true always — never publish, bill, or deploy without approval",
            "Evidence-first: no task marked complete without evidence_ref",
            "Safe autonomous mode: workers generate drafts, human approves publication",
            "Paper trading only — 6-month verified performance minimum before live",
            "No guaranteed income claims or financial guarantees in any output",
        ],
        "execution_priorities": [],
        "updated_at": _now_iso(),
        "version": 1,
    }


# ── Load / save ───────────────────────────────────────────────────────────────

def load_memory(force_refresh: bool = False) -> dict:
    global _CACHE, _CACHE_TS

    if not force_refresh and _CACHE and (time.monotonic() - _CACHE_TS < _CACHE_TTL):
        return _CACHE

    # Try Supabase first
    rows = _sb_select(
        "hermes_executive_memory?select=category,items,updated_at&order=category.asc&limit=20"
    )
    if rows:
        defaults = _default_memory()
        mem = defaults.copy()
        all_empty = True
        for row in rows:
            cat = row.get("category")
            items = row.get("items")
            if cat in CATEGORIES and isinstance(items, list):
                # Use DB row only if it has content; otherwise keep defaults
                if items:
                    mem[cat] = items
                    all_empty = False
        mem["updated_at"] = max(
            (r.get("updated_at", "") for r in rows), default=_now_iso()
        )
        # Seed Supabase with defaults if all categories were empty
        if all_empty:
            for cat in CATEGORIES:
                _sb_upsert(
                    "hermes_executive_memory",
                    {"category": cat, "items": defaults.get(cat, []), "updated_by": "seed"},
                )
        _CACHE = mem
        _CACHE_TS = time.monotonic()
        _save_local(mem)
        return mem

    # Fall back to local file
    if LOCAL_FILE.exists():
        try:
            mem = json.loads(LOCAL_FILE.read_text())
            _CACHE = mem
            _CACHE_TS = time.monotonic()
            return mem
        except Exception:
            pass

    mem = _default_memory()
    _CACHE = mem
    _CACHE_TS = time.monotonic()
    _save_local(mem)
    return mem


def _save_local(mem: dict) -> None:
    try:
        LOCAL_FILE.write_text(json.dumps(mem, indent=2, default=str))
    except Exception:
        pass


def update_category(category: str, items: list[str], source: str = "user") -> bool:
    """Update one memory category in Supabase and local cache."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown category: {category}. Valid: {CATEGORIES}")

    global _CACHE
    mem = load_memory()
    mem[category] = items
    mem["updated_at"] = _now_iso()

    ok = _sb_upsert(
        "hermes_executive_memory",
        {
            "category": category,
            "items": items,
            "updated_by": source,
            "updated_at": _now_iso(),
        },
    )

    _save_local(mem)
    _CACHE = mem
    _CACHE_TS = time.monotonic()
    return ok


def append_to_category(category: str, item: str, source: str = "auto") -> bool:
    """Append one item to a category without overwriting existing items."""
    mem = load_memory()
    existing = mem.get(category, [])
    if item not in existing:
        existing.append(item)
    return update_category(category, existing, source=source)


def remove_from_category(category: str, item_substring: str) -> list[str]:
    """Remove items containing item_substring. Returns removed items."""
    mem = load_memory()
    existing = mem.get(category, [])
    removed = [i for i in existing if item_substring.lower() in i.lower()]
    kept = [i for i in existing if item_substring.lower() not in i.lower()]
    if removed:
        update_category(category, kept, source="user_remove")
    return removed


# ── Context injection ─────────────────────────────────────────────────────────

def build_context_block(max_items_per_category: int = 4) -> str:
    """Return a concise markdown context block for injection into Hermes prompts."""
    mem = load_memory()

    sections: list[str] = []

    priority_map = {
        "execution_priorities": "TODAY'S PRIORITIES",
        "infrastructure_problems": "INFRASTRUCTURE ISSUES",
        "unfinished_systems": "UNFINISHED SYSTEMS",
        "monetization_priorities": "MONETIZATION",
        "business_goals": "BUSINESS GOALS",
        "affiliate_campaigns": "ACTIVE AFFILIATES",
        "content_backlog": "CONTENT BACKLOG",
        "active_workers": "ACTIVE WORKERS",
        "operational_philosophy": "OPERATING RULES",
    }

    for cat, label in priority_map.items():
        items = mem.get(cat, [])[:max_items_per_category]
        if items:
            lines = "\n".join(f"  - {i}" for i in items)
            sections.append(f"**{label}**\n{lines}")

    updated = mem.get("updated_at", "unknown")[:10]
    header = f"[Executive Memory — as of {updated}]"
    return header + "\n\n" + "\n\n".join(sections)


def build_telegram_context(max_chars: int = 600) -> str:
    """Compact context block for Telegram injection (character-limited)."""
    mem = load_memory()

    lines: list[str] = []

    priorities = mem.get("execution_priorities", [])[:3]
    if priorities:
        lines.append("Priorities: " + " | ".join(priorities))

    problems = mem.get("infrastructure_problems", [])[:2]
    if problems:
        lines.append("Issues: " + " | ".join(problems))

    return " ".join(lines)[:max_chars]


# ── Status summary ────────────────────────────────────────────────────────────

def status_summary() -> str:
    """Human-readable summary of current executive memory state."""
    mem = load_memory()
    lines = [
        f"Hermes Executive Memory (v{mem.get('version',1)}, updated {mem.get('updated_at','?')[:10]})",
        "",
    ]
    for cat in CATEGORIES:
        items = mem.get(cat, [])
        label = cat.replace("_", " ").title()
        lines.append(f"[{label}] ({len(items)} items)")
        for item in items[:3]:
            lines.append(f"  • {item}")
        if len(items) > 3:
            lines.append(f"  … +{len(items) - 3} more")
        lines.append("")
    return "\n".join(lines).strip()


# ── Auto-update from live data ────────────────────────────────────────────────

def refresh_from_live_data() -> dict[str, int]:
    """Pull live Supabase state and update dynamic categories. Returns change counts."""
    changes: dict[str, int] = {}

    # Infrastructure problems — from worker_failure_events (unresolved)
    try:
        from scripts.prelaunch_utils import rest_select
        failures = rest_select(
            "worker_failure_events?select=worker_id,failure_type,error_message,created_at"
            "&resolved=eq.false&order=created_at.desc&limit=10",
            timeout=8,
        ) or []
        if failures:
            problems = [
                f"{f.get('worker_id','?')} — {f.get('failure_type','?')}: {str(f.get('error_message',''))[:80]}"
                for f in failures[:5]
            ]
            update_category("infrastructure_problems", problems, source="live_refresh")
            changes["infrastructure_problems"] = len(problems)
    except Exception:
        pass

    # Active workers — from worker_daily_quotas (today)
    try:
        from datetime import date as _date
        today = _date.today().isoformat()
        quotas = rest_select(
            f"worker_daily_quotas?select=worker_id,quota_type,current_count,target_per_day,met"
            f"&quota_date=eq.{today}&limit=20",
            timeout=8,
        ) or []
        if quotas:
            worker_lines = [
                f"{q.get('worker_id','?')} — {q.get('quota_type','?')}: "
                f"{q.get('current_count',0)}/{q.get('target_per_day',1)} "
                f"({'✓' if q.get('met') else '…'})"
                for q in quotas
            ]
            update_category("active_workers", worker_lines, source="live_refresh")
            changes["active_workers"] = len(worker_lines)
    except Exception:
        pass

    return changes
