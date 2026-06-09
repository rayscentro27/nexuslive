"""
content_board.py — file-based Nexus Content Workspace Board (v1).

Single review surface for content as it moves idea → research → draft → render →
Ray review → approval → publish. Backed by a local JSONL file (one card per line);
NO database, NO paid API, NO network, NO publishing. Safe to import and run repeatedly.

State file: reports/content_engine/content_board.jsonl

Safety: this module only reads/writes the local board file. It never uploads, posts,
schedules, spends, changes credentials, or touches social_publish_executor.py.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BOARD_FILE = ROOT / "reports" / "content_engine" / "content_board.jsonl"

# Pipeline statuses (order = pipeline order; index used for sorting/progress)
STATUSES = [
    "Ideas",
    "Researched",
    "Drafted",
    "Podcast Scripted",
    "Video Packet Ready",
    "Video Rendered",
    "Needs Ray Review",
    "Approved for Unlisted",
    "Approved Public",
    "Published",
    "Performance Review",
    "Improve / Retry",
    "Archived / Rejected",
]

# Statuses that represent a Ray decision point (autonomous engine stops here)
RAY_REVIEW_STATUSES = {"Needs Ray Review"}
# Statuses only Ray may set (external/public exposure or executor action)
RAY_ONLY_STATUSES = {"Approved for Unlisted", "Approved Public", "Published"}

# Card field order (the v1 schema). Unknown extra keys are preserved.
# v1.1 (2026-06-09): additive prompt-library fields appended at the end. Existing cards that
# predate these keys keep working — every reader uses .get() with safe defaults.
FIELDS = [
    "board_id", "content_id", "campaign_id", "title", "topic", "status", "priority",
    "content_type", "platform_targets", "source_paths", "artifact_paths", "preview_paths",
    "approval_required", "approval_id", "approval_status", "compliance_status",
    "disclosure_present", "publish_risk_level", "recommended_next_action", "owner_agent",
    "created_at", "updated_at", "telegram_summary", "performance_check_status", "notes",
    # --- v1.1 prompt-library wiring (additive) ---
    "prompt_used", "quality_score", "generated_artifacts", "content_family", "parent_source_id",
    # --- v1.2 viral-pattern scout wiring (additive) ---
    "source_pattern_id", "source_inspiration_urls", "transformation_notes", "originality_score",
    # --- v1.3 telegram approval wiring (additive) ---
    "telegram_approval_request_id", "telegram_approval_status", "telegram_last_prompted_at",
    "telegram_decision", "telegram_decision_at",
    # --- v1.3 quality review fields (additive) ---
    "visual_quality_notes", "voice_quality_notes",
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_card(**kw: Any) -> dict:
    """Build a card dict with defaults; caller overrides via kwargs."""
    cid = kw.get("content_id") or ""
    board_id = kw.get("board_id") or ("card-" + (cid.split("-")[0] if cid else uuid.uuid4().hex[:8]))
    now = _now()
    card = {
        "board_id": board_id,
        "content_id": cid,
        "campaign_id": kw.get("campaign_id", ""),
        "title": kw.get("title", ""),
        "topic": kw.get("topic", ""),
        "status": kw.get("status", "Ideas"),
        "priority": kw.get("priority", "normal"),         # low | normal | high
        "content_type": kw.get("content_type", ""),
        "platform_targets": kw.get("platform_targets", []),
        "source_paths": kw.get("source_paths", []),
        "artifact_paths": kw.get("artifact_paths", []),
        "preview_paths": kw.get("preview_paths", []),
        "approval_required": kw.get("approval_required", False),
        "approval_id": kw.get("approval_id"),
        "approval_status": kw.get("approval_status", "none"),  # none|pending|approved|rejected
        "compliance_status": kw.get("compliance_status", "unknown"),  # unknown|pass|fail
        "disclosure_present": kw.get("disclosure_present", False),
        "publish_risk_level": kw.get("publish_risk_level", "internal"),  # internal|external/public|high
        "recommended_next_action": kw.get("recommended_next_action", ""),
        "owner_agent": kw.get("owner_agent", "content_worker"),
        "created_at": kw.get("created_at", now),
        "updated_at": now,
        "telegram_summary": kw.get("telegram_summary", ""),
        "performance_check_status": kw.get("performance_check_status", "n/a"),
        "notes": kw.get("notes", ""),
        # --- v1.1 prompt-library wiring (additive; safe defaults) ---
        "prompt_used": kw.get("prompt_used", ""),           # e.g. "youtube_shorts.md"
        "quality_score": kw.get("quality_score"),            # int 1-10 or None
        "generated_artifacts": kw.get("generated_artifacts", []),  # paths produced by the prompt run
        "content_family": kw.get("content_family", ""),     # repurposing group id
        "parent_source_id": kw.get("parent_source_id", ""),  # source/content this was derived from
        # --- v1.2 viral-pattern scout wiring (additive; safe defaults) ---
        "source_pattern_id": kw.get("source_pattern_id", ""),        # viral_pattern_card id (vp-...)
        "source_inspiration_urls": kw.get("source_inspiration_urls", []),  # studied (pattern-only) URLs
        "transformation_notes": kw.get("transformation_notes", ""),  # how the Nexus idea differs from source
        "originality_score": kw.get("originality_score"),            # int 1-10 or None
        # --- v1.3 telegram approval wiring (additive; safe defaults) ---
        "telegram_approval_request_id": kw.get("telegram_approval_request_id", ""),
        "telegram_approval_status": kw.get("telegram_approval_status", ""),   # ""|pending|approved|rejected|retry
        "telegram_last_prompted_at": kw.get("telegram_last_prompted_at", ""),
        "telegram_decision": kw.get("telegram_decision", ""),
        "telegram_decision_at": kw.get("telegram_decision_at", ""),
        # --- v1.3 quality review notes (additive) ---
        "visual_quality_notes": kw.get("visual_quality_notes", ""),
        "voice_quality_notes": kw.get("voice_quality_notes", ""),
    }
    # preserve any extra keys the caller passed
    for k, v in kw.items():
        if k not in card:
            card[k] = v
    return card


def load_board(path: Path | None = None) -> list[dict]:
    p = path or BOARD_FILE
    if not p.exists():
        return []
    cards = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cards.append(json.loads(line))
    return cards


def save_board(cards: list[dict], path: Path | None = None) -> None:
    p = path or BOARD_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")


def find(cards: list[dict], key: str) -> dict | None:
    """Find a card by board_id or content_id (exact or short-prefix)."""
    for c in cards:
        if c.get("board_id") == key or c.get("content_id") == key:
            return c
    for c in cards:
        if str(c.get("content_id", "")).startswith(key) or str(c.get("board_id", "")).startswith(key):
            return c
    return None


def upsert(card: dict, path: Path | None = None) -> tuple[dict, bool]:
    """Insert or replace a card (matched by board_id, else content_id). Returns (card, created)."""
    cards = load_board(path)
    for i, c in enumerate(cards):
        if c.get("board_id") == card.get("board_id") or (
            card.get("content_id") and c.get("content_id") == card.get("content_id")
        ):
            card["created_at"] = c.get("created_at", card.get("created_at"))
            card["updated_at"] = _now()
            cards[i] = card
            save_board(cards, path)
            return card, False
    cards.append(card)
    save_board(cards, path)
    return card, True


def counts_by_status(cards: list[dict]) -> dict[str, int]:
    out = {s: 0 for s in STATUSES}
    for c in cards:
        s = c.get("status", "Ideas")
        out[s] = out.get(s, 0) + 1
    return out
