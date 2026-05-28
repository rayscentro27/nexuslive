"""
youtube_source_registry.py
===========================
Tracks every YouTube channel or video Ray gives Nexus.
NO SOURCE DISAPPEARS. Every submission gets a persistent record.

Storage: docs/reports/youtube/source_registry.json
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT         = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "docs" / "reports" / "youtube"
REGISTRY_FILE = REGISTRY_DIR / "source_registry.json"

SourceType      = Literal["channel", "video", "playlist"]
SourceStatus    = Literal[
    "submitted",       # received, not yet processed
    "queued",          # in processing queue
    "processing",      # actively being analyzed
    "active",          # fully processed, in use
    "needs_review",    # flagged for quality/compliance review
    "rejected",        # rejected with reason
    "archived",        # no longer active but kept for history
]
TranscriptStatus = Literal[
    "not_started",
    "queued",
    "downloaded",
    "failed",
    "not_available",   # video has no captions/transcript
]
ResearchStatus  = Literal[
    "not_started",
    "intelligence_extracted",
    "monetization_mapped",
    "complete",
    "skipped",
]
MonetizationStatus = Literal[
    "not_evaluated",
    "high_value",
    "medium_value",
    "low_value",
    "not_applicable",
]


class YouTubeSourceRecord:
    """Immutable-style record for a single YouTube source."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def source_id(self) -> str:
        return self._data["source_id"]

    @property
    def url(self) -> str:
        return self._data["url"]

    @property
    def status(self) -> str:
        return self._data.get("status", "submitted")

    def to_dict(self) -> dict:
        return dict(self._data)

    def __repr__(self) -> str:
        return (
            f"YouTubeSourceRecord(id={self.source_id[:8]}, "
            f"url={self.url[:50]}, status={self.status})"
        )


class YouTubeSourceRegistry:
    """
    Persistent registry for all YouTube sources Ray submits to Nexus.

    Every source gets a unique source_id derived from its URL (stable across
    re-submissions). Records are never deleted — only status-updated.
    """

    def __init__(self):
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, dict] = self._load()

    # ── Public API ─────────────────────────────────────────────────────────────

    def register(
        self,
        url: str,
        source_type: SourceType,
        *,
        submitted_by: str = "raymond",
        channel_name: str = "",
        video_title: str = "",
        notes: str = "",
        supabase_id: str = "",
        workflow_output_id: str = "",
    ) -> YouTubeSourceRecord:
        """Register a new source or return the existing record if already tracked."""
        source_id = self._stable_id(url)

        if source_id in self._records:
            # Update mutable fields but preserve history
            rec = self._records[source_id]
            rec["last_seen_at"] = _now()
            if channel_name:
                rec["channel_name"] = channel_name
            if video_title:
                rec["video_title"] = video_title
            if supabase_id:
                rec["supabase_id"] = supabase_id
            if workflow_output_id:
                rec["workflow_output_id"] = workflow_output_id
            self._save()
            return YouTubeSourceRecord(rec)

        rec: dict = {
            "source_id":          source_id,
            "submitted_by":       submitted_by,
            "submitted_at":       _now(),
            "last_seen_at":       _now(),
            "source_type":        source_type,
            "url":                url,
            "channel_name":       channel_name,
            "video_title":        video_title,
            "status":             "submitted",
            "transcript_status":  "not_started",
            "quality_score":      None,
            "research_status":    "not_started",
            "monetization_status": "not_evaluated",
            "artifact_paths":     [],
            "rejection_reason":   "",
            "next_action":        "queue_for_processing",
            "notes":              notes,
            "supabase_id":        supabase_id,
            "workflow_output_id": workflow_output_id,
        }
        self._records[source_id] = rec
        self._save()
        return YouTubeSourceRecord(rec)

    def update(self, source_id: str, **fields) -> YouTubeSourceRecord | None:
        """Update a source record's fields. Returns None if not found."""
        if source_id not in self._records:
            return None
        rec = self._records[source_id]
        allowed = {
            "status", "transcript_status", "quality_score",
            "research_status", "monetization_status", "artifact_paths",
            "rejection_reason", "next_action", "channel_name", "video_title",
            "supabase_id", "workflow_output_id", "notes",
        }
        for k, v in fields.items():
            if k in allowed:
                rec[k] = v
        rec["updated_at"] = _now()
        self._save()
        return YouTubeSourceRecord(rec)

    def add_artifact(self, source_id: str, artifact_path: str) -> bool:
        """Append an artifact path to a source's artifact_paths list."""
        if source_id not in self._records:
            return False
        paths: list = self._records[source_id].setdefault("artifact_paths", [])
        if artifact_path not in paths:
            paths.append(artifact_path)
        self._records[source_id]["updated_at"] = _now()
        self._save()
        return True

    def get(self, source_id: str) -> YouTubeSourceRecord | None:
        rec = self._records.get(source_id)
        return YouTubeSourceRecord(rec) if rec else None

    def find_by_url(self, url: str) -> YouTubeSourceRecord | None:
        sid = self._stable_id(url)
        return self.get(sid)

    def all(self) -> list[YouTubeSourceRecord]:
        return [YouTubeSourceRecord(r) for r in self._records.values()]

    def by_status(self, status: SourceStatus) -> list[YouTubeSourceRecord]:
        return [YouTubeSourceRecord(r) for r in self._records.values()
                if r.get("status") == status]

    def pending_transcript(self) -> list[YouTubeSourceRecord]:
        return [YouTubeSourceRecord(r) for r in self._records.values()
                if r.get("transcript_status") in ("not_started", "queued")]

    def needs_research(self) -> list[YouTubeSourceRecord]:
        return [YouTubeSourceRecord(r) for r in self._records.values()
                if r.get("research_status") == "not_started"
                and r.get("status") not in ("rejected", "archived")]

    def summary_table(self) -> str:
        """Return a markdown table summarizing all sources."""
        if not self._records:
            return "No YouTube sources registered yet."
        rows = []
        for r in sorted(self._records.values(), key=lambda x: x.get("submitted_at", ""), reverse=True):
            rows.append(
                f"| {r['source_id'][:8]} | {r['source_type']} "
                f"| {(r.get('channel_name') or r.get('video_title') or r['url'])[:40]} "
                f"| {r['status']} | {r['transcript_status']} "
                f"| {r.get('quality_score') or 'N/A'} | {r['research_status']} |"
            )
        header = (
            "| ID | Type | Name/URL | Status | Transcript | Quality | Research |\n"
            "|---|---|---|---|---|---|---|"
        )
        return header + "\n" + "\n".join(rows)

    def count_by_status(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._records.values():
            s = r.get("status", "unknown")
            counts[s] = counts.get(s, 0) + 1
        return counts

    # ── Internals ──────────────────────────────────────────────────────────────

    def _stable_id(self, url: str) -> str:
        """Stable source_id derived from normalized URL — same URL always same ID."""
        normalized = url.strip().lower().rstrip("/")
        return "yt_" + hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def _load(self) -> dict[str, dict]:
        if not REGISTRY_FILE.exists():
            return {}
        try:
            return json.loads(REGISTRY_FILE.read_text())
        except Exception:
            return {}

    def _save(self) -> None:
        REGISTRY_FILE.write_text(json.dumps(self._records, indent=2))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_registry = YouTubeSourceRegistry()


def register_source(
    url: str,
    source_type: SourceType,
    **kwargs,
) -> YouTubeSourceRecord:
    return _registry.register(url, source_type, **kwargs)


def get_source(source_id: str) -> YouTubeSourceRecord | None:
    return _registry.get(source_id)


def find_by_url(url: str) -> YouTubeSourceRecord | None:
    return _registry.find_by_url(url)


def all_sources() -> list[YouTubeSourceRecord]:
    return _registry.all()


def sources_by_status(status: SourceStatus) -> list[YouTubeSourceRecord]:
    return _registry.by_status(status)


def registry_summary() -> str:
    return _registry.summary_table()


def registry_counts() -> dict[str, int]:
    return _registry.count_by_status()
