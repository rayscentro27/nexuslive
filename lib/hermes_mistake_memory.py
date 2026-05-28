"""
hermes_mistake_memory.py — Hermes Mistake Memory + Pattern Correction
======================================================================
Tracks repeated mistakes, rejections, and failed patterns.
Hermes learns from recurrence so it doesn't repeat the same errors.

Artifact: docs/reports/hermes_mistake_memory.json

Usage:
    from lib.hermes_mistake_memory import HermesMistakeMemory
    mem = HermesMistakeMemory()
    mem.record_pattern("weak_cta", "monetization", "Content without CTA went live", ...)
    mem.get_active_corrections()
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT        = Path(__file__).resolve().parent.parent
MEMORY_FILE = ROOT / "docs" / "reports" / "hermes_mistake_memory.json"

PATTERN_CATEGORIES = [
    "risky_opportunity_repeated",
    "rejected_idea_repeated",
    "weak_monetization_repeated",
    "credit_strategy_rejected_repeatedly",
    "trading_strategy_poor_performance_repeated",
    "content_no_revenue_path",
    "github_tool_suggested_never_tested",
    "missing_artifact_repeated",
    "provider_api_failure_repeated",
    "supabase_failure_repeated",
    "artifact_missing_claimed_complete",
]

STATUSES = ["active", "corrected", "needs_ray_review", "ignored_with_reason"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text())
        except Exception:
            pass
    return {"patterns": [], "correction_rules": [], "summary": {}}


def _save_memory(data: dict) -> None:
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps(data, indent=2, default=str))


class HermesMistakeMemory:

    def __init__(self) -> None:
        self._data = _load()

    def record_pattern(
        self,
        pattern: str,
        category: str,
        evidence: str,
        correction_rule: str = "",
        status: str = "active",
    ) -> dict:
        """
        Record a new mistake pattern or increment existing one.
        Returns the pattern record.
        """
        # Check for existing pattern (fuzzy match by first 60 chars)
        key = pattern[:60].lower()
        existing = next(
            (p for p in self._data["patterns"] if p.get("pattern", "")[:60].lower() == key),
            None,
        )
        if existing:
            existing["recurrence_count"] = existing.get("recurrence_count", 1) + 1
            existing["last_seen"]        = _now()
            existing["evidence_log"]     = existing.get("evidence_log", []) + [evidence]
            if correction_rule and correction_rule not in existing.get("correction_rules", []):
                existing.setdefault("correction_rules", []).append(correction_rule)
            if status != "active":
                existing["status"] = status
            _save_memory(self._data)
            return existing

        record = {
            "id":               f"mistake_{len(self._data['patterns'])+1:04d}",
            "pattern":          pattern,
            "category":         category if category in PATTERN_CATEGORIES else "other",
            "evidence":         evidence,
            "evidence_log":     [evidence],
            "recurrence_count": 1,
            "correction_rules": [correction_rule] if correction_rule else [],
            "status":           status if status in STATUSES else "active",
            "first_seen":       _now(),
            "last_seen":        _now(),
            "why_it_matters":   self._derive_why(category, pattern),
        }
        self._data["patterns"].append(record)
        _save_memory(self._data)
        return record

    def mark_corrected(self, pattern_id: str, correction_note: str = "") -> bool:
        for p in self._data["patterns"]:
            if p.get("id") == pattern_id:
                p["status"]      = "corrected"
                p["corrected_at"] = _now()
                if correction_note:
                    p["correction_note"] = correction_note
                _save_memory(self._data)
                return True
        return False

    def flag_for_ray(self, pattern_id: str, reason: str = "") -> bool:
        for p in self._data["patterns"]:
            if p.get("id") == pattern_id:
                p["status"] = "needs_ray_review"
                if reason:
                    p["ray_review_reason"] = reason
                _save_memory(self._data)
                return True
        return False

    def get_active_corrections(self) -> list[dict]:
        return [p for p in self._data["patterns"] if p.get("status") == "active"]

    def get_high_recurrence(self, min_count: int = 3) -> list[dict]:
        return sorted(
            [p for p in self._data["patterns"] if p.get("recurrence_count", 0) >= min_count],
            key=lambda x: x.get("recurrence_count", 0), reverse=True,
        )

    def get_all(self) -> list[dict]:
        return self._data.get("patterns", [])

    def summary(self) -> dict:
        patterns = self._data.get("patterns", [])
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        for p in patterns:
            by_status[p.get("status", "?")] = by_status.get(p.get("status", "?"), 0) + 1
            by_category[p.get("category", "?")] = by_category.get(p.get("category", "?"), 0) + 1
        return {
            "total_patterns":    len(patterns),
            "active":            by_status.get("active", 0),
            "corrected":         by_status.get("corrected", 0),
            "needs_ray_review":  by_status.get("needs_ray_review", 0),
            "high_recurrence":   len(self.get_high_recurrence()),
            "by_category":       by_category,
            "most_common":       sorted(patterns, key=lambda x: x.get("recurrence_count", 0), reverse=True)[:3],
        }

    def render_md(self) -> str:
        patterns = self._data.get("patterns", [])
        s = self.summary()
        lines = [
            "# Hermes Mistake Memory",
            f"*Last updated: {_now()}*\n",
            f"**Total patterns:** {s['total_patterns']} | **Active:** {s['active']} | **Corrected:** {s['corrected']} | **Needs Ray review:** {s['needs_ray_review']}\n",
            "## Active Correction Rules\n",
        ]
        active = [p for p in patterns if p.get("status") == "active"]
        if not active:
            lines.append("*No active mistakes recorded yet.*\n")
        for p in active:
            emoji = "🔴" if p.get("recurrence_count", 1) >= 3 else "🟡"
            lines.append(f"### {emoji} [{p.get('recurrence_count',1)}x] {p.get('pattern', '')}")
            lines.append(f"*Category: {p.get('category','')} | First: {p.get('first_seen','')[:10]} | Last: {p.get('last_seen','')[:10]}*")
            lines.append(f"**Why it matters:** {p.get('why_it_matters', '')}")
            for rule in p.get("correction_rules", []):
                lines.append(f"✅ Rule: _{rule}_")
            lines.append("")
        lines.append("## Needs Ray Review\n")
        flagged = [p for p in patterns if p.get("status") == "needs_ray_review"]
        for p in flagged:
            lines.append(f"- **{p.get('pattern','')}** — {p.get('ray_review_reason', 'flagged for review')}")
        return "\n".join(lines)

    def _derive_why(self, category: str, pattern: str) -> str:
        why_map = {
            "artifact_missing_claimed_complete": "Claiming completion without artifacts undermines trust and wastes review cycles.",
            "risky_opportunity_repeated":        "Repeatedly evaluating the same risky idea wastes compute and increases the chance of approval creep.",
            "weak_monetization_repeated":        "Revenue paths without CTAs produce no revenue regardless of content quality.",
            "provider_api_failure_repeated":     "Repeated API failures block other agents downstream and burn retry budget.",
            "missing_artifact_repeated":         "Workflows that produce no artifacts cannot be audited or improved.",
            "content_no_revenue_path":           "Content without a monetization path is marketing spend with no ROI.",
        }
        return why_map.get(category, f"Pattern detected in category: {category}")
