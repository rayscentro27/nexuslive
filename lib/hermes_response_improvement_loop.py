"""
hermes_response_improvement_loop.py
Analyzes logged knowledge gaps and proposes language-pack updates,
new intent aliases, and memory items for Ray's approval.
No Supabase writes. No paid API calls.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lib.hermes_knowledge_gap_logger import load_recent_knowledge_gaps
from lib.hermes_language_pack import (
    CATEGORY_EXTERNAL_INFO, CATEGORY_UNKNOWN, CATEGORY_SYSTEM_HEALTH,
    CATEGORY_MONETIZATION, CATEGORY_CONTENT_ASSET,
    GAP_UNSUPPORTED_EXTERNAL, GAP_MISSING_ROUTE, GAP_MISSING_ACTIVE_MEMORY,
)

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "docs" / "reports" / "knowledge_gaps"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def analyze_knowledge_gaps(limit: int = 50) -> list[dict[str, Any]]:
    """Load recent gaps and group them by category and reason."""
    gaps = load_recent_knowledge_gaps(limit=limit)
    open_gaps = [g for g in gaps if g.get("status") == "open"]
    return open_gaps


def propose_language_pack_updates(gaps: list[dict] | None = None) -> list[dict[str, Any]]:
    """For each unknown gap, propose adding the phrase to a language-pack category."""
    if gaps is None:
        gaps = analyze_knowledge_gaps()
    proposals = []
    seen: set[str] = set()
    for g in gaps:
        msg = g.get("normalized_message", "") or g.get("user_message", "")
        if not msg or msg in seen:
            continue
        seen.add(msg)
        cat = g.get("category", "")
        reason = g.get("reason", "")
        if reason in (GAP_MISSING_ROUTE,) and cat == CATEGORY_UNKNOWN:
            proposals.append({
                "proposal_type": "new_phrase_alias",
                "phrase": msg[:80],
                "suggested_category": _infer_category(msg),
                "current_category": cat,
                "reason": reason,
                "ray_approval_needed": True,
            })
    return proposals


def propose_new_intent_aliases(gaps: list[dict] | None = None) -> list[dict[str, Any]]:
    """Propose adding new aliases to hermes_command_router/intake.py."""
    if gaps is None:
        gaps = analyze_knowledge_gaps()
    aliases = []
    seen: set[str] = set()
    for g in gaps:
        msg = g.get("normalized_message", "")
        if not msg or msg in seen:
            continue
        seen.add(msg)
        suggested = _infer_intent_alias(msg)
        if suggested:
            aliases.append({
                "proposal_type": "intent_alias",
                "phrase": msg[:80],
                "suggested_intent": suggested,
                "file": "hermes_command_router/intake.py",
                "ray_approval_needed": True,
            })
    return aliases


def propose_memory_items(gaps: list[dict] | None = None) -> list[dict[str, Any]]:
    """Propose adding items to active memory when gap shows repeated question."""
    if gaps is None:
        gaps = analyze_knowledge_gaps()
    # Group by normalized message to find repeated gaps
    counts: dict[str, int] = {}
    by_msg: dict[str, dict] = {}
    for g in gaps:
        msg = g.get("normalized_message", "")
        if msg:
            counts[msg] = counts.get(msg, 0) + 1
            by_msg[msg] = g
    proposals = []
    for msg, count in counts.items():
        if count >= 2:
            proposals.append({
                "proposal_type": "active_memory_item",
                "phrase": msg[:80],
                "asked_count": count,
                "category": by_msg[msg].get("category", ""),
                "suggested_action": "add_to_nexus_knowledge or add_language_route",
                "ray_approval_needed": True,
            })
    return proposals


def create_response_improvement_report() -> str:
    """Generate a full improvement report as a markdown file. Returns the path."""
    ts = _now_ts()
    gaps = analyze_knowledge_gaps()
    lang_updates = propose_language_pack_updates(gaps)
    aliases = propose_new_intent_aliases(gaps)
    memory = propose_memory_items(gaps)

    lines = [
        f"# Hermes Response Improvement Report",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"## Summary",
        f"- Open gaps: {len(gaps)}",
        f"- Language-pack update proposals: {len(lang_updates)}",
        f"- Intent alias proposals: {len(aliases)}",
        f"- Memory item proposals: {len(memory)}",
        "",
        f"## Open Knowledge Gaps",
    ]
    if not gaps:
        lines.append("_No open gaps._")
    for i, g in enumerate(gaps[:20], 1):
        lines += [
            f"",
            f"### {i}. {g.get('user_message', '?')[:80]}",
            f"- **Category:** {g.get('category', '?')}",
            f"- **Reason:** {g.get('reason', '?')}",
            f"- **Priority:** {g.get('priority', '?')}",
            f"- **Handler needed:** `{g.get('suggested_handler', '?')}`",
        ]
    lines += [
        "",
        "## Language-Pack Update Proposals",
        "(Ray approval required before applying)",
    ]
    for p in lang_updates:
        lines += [
            f"",
            f"- **Phrase:** `{p['phrase']}`",
            f"  → Suggested category: `{p['suggested_category']}`",
        ]
    lines += [
        "",
        "## Intent Alias Proposals",
        "(Add to hermes_command_router/intake.py)",
    ]
    for a in aliases:
        lines += [
            f"",
            f"- **Phrase:** `{a['phrase']}`",
            f"  → Suggested intent: `{a['suggested_intent']}`",
        ]
    lines += [
        "",
        "## Repeated Questions (Active Memory Candidates)",
    ]
    for m in memory:
        lines += [
            f"",
            f"- **Phrase:** `{m['phrase']}` (asked {m['asked_count']}×)",
            f"  → Action: {m['suggested_action']}",
        ]
    lines += [
        "",
        "## Next Recommended Step",
        "1. Review gap list above.",
        "2. For external-info gaps: decide whether to add a provider.",
        "3. For repeated unknown gaps: add phrase to hermes_language_pack.py.",
        "4. For monetization gaps: ensure business_opportunities Supabase table is populated.",
        "5. Mark resolved gaps with status: resolved in hermes_knowledge_gaps.jsonl.",
    ]

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"response_improvement_report_{ts}.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(report_path)


def _infer_category(message: str) -> str:
    t = message.lower()
    if any(k in t for k in ["health", "status", "broken", "down", "system", "provider"]):
        return "system_health"
    if any(k in t for k in ["money", "revenue", "monetize", "opportunity", "make money"]):
        return "monetization_question"
    if any(k in t for k in ["weather", "news", "price", "score"]):
        return "external_info_question"
    if any(k in t for k in ["what can you", "capabilities", "help", "commands"]):
        return "capability_question"
    return "unknown_or_unresolved"


def _infer_intent_alias(message: str) -> str:
    t = message.lower()
    if any(k in t for k in ["health", "status", "broken", "down"]):
        return "health_check"
    if any(k in t for k in ["money", "revenue", "opportunity"]):
        return "business_opportunities"
    if any(k in t for k in ["what can you", "help", "capabilities"]):
        return "capability_question"
    return ""
