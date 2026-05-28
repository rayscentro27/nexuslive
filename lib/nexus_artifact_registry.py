"""
nexus_artifact_registry.py
============================
Single local/Supabase-aware registry for ALL Nexus artifacts created by any agent.

NO ARTIFACT = NO CLAIM. Every agent output must be registered here.

Storage:
  1. Local: docs/reports/artifact_registry/nexus_artifact_registry.jsonl
            docs/reports/artifact_registry/nexus_artifact_registry_latest.md
  2. Supabase: nexus_artifacts table (if configured)

Evidence levels:
  verified_file           — file path confirmed to exist on disk
  verified_supabase       — row confirmed in Supabase
  verified_workflow_output — workflow_output ID confirmed
  unverified_claim        — no artifact backing (BLOCKED)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT         = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT / "docs" / "reports" / "artifact_registry"
REGISTRY_FILE = REGISTRY_DIR / "nexus_artifact_registry.jsonl"
REGISTRY_MD   = REGISTRY_DIR / "nexus_artifact_registry_latest.md"

AgentType = Literal[
    "claude_code", "codex", "opencode", "hermes",
    "worker", "manual_ray", "unknown",
]
SourceType = Literal[
    "youtube_channel", "youtube_video", "github_repo",
    "trading_strategy", "credit_repair_strategy", "business_funding",
    "grant", "affiliate_program", "monetization_idea",
    "blocker", "ceo_packet", "content_packet", "report",
    "code_change", "other",
]
ArtifactType = Literal[
    "markdown_report", "json_report", "transcript", "source_registry",
    "strategy_packet", "content_packet", "monetization_packet",
    "decision_log", "compliance_review", "blocker_report",
    "test_result", "diff", "prompt", "code_file",
]
ArtifactStatus = Literal[
    "created", "completed", "failed", "needs_review",
    "needs_ray_review", "low_quality_rejected", "missing_source", "stale",
]
EvidenceLevel = Literal[
    "verified_file", "verified_supabase", "verified_workflow_output", "unverified_claim",
]


class ArtifactRecord:
    """Represents a single registered artifact."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def artifact_id(self) -> str:
        return self._data["artifact_id"]

    @property
    def file_path(self) -> str:
        return self._data.get("file_path", "")

    @property
    def evidence_level(self) -> str:
        return self._data.get("evidence_level", "unverified_claim")

    @property
    def is_verified(self) -> bool:
        return self.evidence_level != "unverified_claim"

    def to_dict(self) -> dict:
        return dict(self._data)

    def __repr__(self) -> str:
        return (
            f"ArtifactRecord(id={self.artifact_id[:8]}, "
            f"type={self._data.get('artifact_type')}, "
            f"evidence={self.evidence_level})"
        )


class NexusArtifactRegistry:
    """
    Persistent registry for all Nexus artifacts.

    Append-only JSONL log. Queries scan the log and deduplicate by artifact_id.
    Supabase writes attempted if configured; falls back to local-only.
    """

    def __init__(self):
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def register_artifact(
        self,
        *,
        agent_name: str,
        agent_type: AgentType = "unknown",
        source_input: str = "",
        source_type: SourceType = "other",
        artifact_type: ArtifactType = "markdown_report",
        title: str = "",
        summary: str = "",
        file_path: str = "",
        task_id: str = "",
        parent_task_id: str = "",
        repo: str = "",
        branch: str = "",
        commit_hash: str = "",
        status: ArtifactStatus = "created",
        evidence_level: EvidenceLevel | None = None,
        tags: list[str] | None = None,
        related_artifacts: list[str] | None = None,
        what_hermes_should_know: str = "",
        next_action: str = "",
        requires_ray_approval: bool = False,
        approval_reason: str = "",
        **extra: Any,
    ) -> ArtifactRecord:
        """Register an artifact and return its record."""
        artifact_id = "art_" + uuid.uuid4().hex[:16]

        # Auto-detect evidence level from file_path
        if evidence_level is None:
            if file_path and Path(file_path).exists():
                evidence_level = "verified_file"
            elif file_path:
                evidence_level = "unverified_claim"
            else:
                evidence_level = "unverified_claim"

        # Compute checksum if file exists
        checksum = ""
        if file_path and Path(file_path).exists():
            try:
                checksum = hashlib.md5(Path(file_path).read_bytes()).hexdigest()
            except Exception:
                pass

        record: dict = {
            "artifact_id":            artifact_id,
            "task_id":                task_id,
            "parent_task_id":         parent_task_id,
            "created_at":             _now(),
            "updated_at":             _now(),
            "agent_name":             agent_name,
            "agent_type":             agent_type,
            "source_input":           source_input,
            "source_type":            source_type,
            "artifact_type":          artifact_type,
            "title":                  title,
            "summary":                summary,
            "file_path":              file_path,
            "repo":                   repo,
            "branch":                 branch,
            "commit_hash":            commit_hash,
            "status":                 status,
            "evidence_level":         evidence_level,
            "tags":                   tags or [],
            "related_artifacts":      related_artifacts or [],
            "what_hermes_should_know": what_hermes_should_know,
            "next_action":            next_action,
            "requires_ray_approval":  requires_ray_approval,
            "approval_reason":        approval_reason,
            "checksum":               checksum,
            **{k: v for k, v in extra.items() if k not in record},
        }

        self._append(record)
        self._try_supabase_write(record)
        self._update_markdown_summary()

        return ArtifactRecord(record)

    def mark_artifact_status(self, artifact_id: str, status: ArtifactStatus) -> bool:
        """Append a status-update record for an artifact."""
        records = self._all_records()
        existing = next((r for r in reversed(records) if r.get("artifact_id") == artifact_id), None)
        if not existing:
            return False
        update = {**existing, "status": status, "updated_at": _now(), "_update": True}
        self._append(update)
        return True

    def find_artifacts(
        self,
        query: str = "",
        tags: list[str] | None = None,
        source_type: SourceType | None = None,
        artifact_type: ArtifactType | None = None,
        agent_name: str | None = None,
        limit: int = 20,
    ) -> list[ArtifactRecord]:
        """Search artifacts by multiple criteria."""
        records = self._deduplicated_records()
        results = []
        q = query.lower()
        for r in reversed(records):
            if source_type and r.get("source_type") != source_type:
                continue
            if artifact_type and r.get("artifact_type") != artifact_type:
                continue
            if agent_name and r.get("agent_name") != agent_name:
                continue
            if tags and not any(t in r.get("tags", []) for t in tags):
                continue
            if q and q not in json.dumps(r).lower():
                continue
            results.append(ArtifactRecord(r))
            if len(results) >= limit:
                break
        return results

    def latest_artifacts(self, limit: int = 20) -> list[ArtifactRecord]:
        records = self._deduplicated_records()
        return [ArtifactRecord(r) for r in records[-limit:]]

    def find_by_source_url(self, url: str) -> list[ArtifactRecord]:
        records = self._deduplicated_records()
        return [ArtifactRecord(r) for r in records
                if url in r.get("source_input", "")]

    def find_by_task_id(self, task_id: str) -> list[ArtifactRecord]:
        records = self._deduplicated_records()
        return [ArtifactRecord(r) for r in records
                if r.get("task_id") == task_id]

    def find_youtube_artifacts(self) -> list[ArtifactRecord]:
        records = self._deduplicated_records()
        return [ArtifactRecord(r) for r in records
                if r.get("source_type") in ("youtube_channel", "youtube_video")]

    def find_agent_outputs(self, agent_name: str) -> list[ArtifactRecord]:
        records = self._deduplicated_records()
        return [ArtifactRecord(r) for r in records
                if r.get("agent_name") == agent_name]

    def create_registry_summary(self) -> str:
        """Return a markdown summary of recent artifacts."""
        records = self._deduplicated_records()
        if not records:
            return "No artifacts registered yet."
        rows = ""
        for r in reversed(records[-20:]):
            icon = "✅" if r.get("evidence_level") == "verified_file" else "⚠️"
            rows += (
                f"| {icon} | {r['artifact_id'][:8]} | {r.get('agent_name','?')} "
                f"| {r.get('artifact_type','?')} "
                f"| {r.get('title','')[:40]} | {r.get('status','?')} |\n"
            )
        return (
            f"# Nexus Artifact Registry\n"
            f"*{len(records)} artifacts total — last updated {_now()}*\n\n"
            f"| Verified | ID | Agent | Type | Title | Status |\n"
            f"|---|---|---|---|---|---|\n"
            f"{rows}"
        )

    def count_by_agent(self) -> dict[str, int]:
        records = self._deduplicated_records()
        counts: dict[str, int] = {}
        for r in records:
            agent = r.get("agent_name", "unknown")
            counts[agent] = counts.get(agent, 0) + 1
        return counts

    def count_by_source_type(self) -> dict[str, int]:
        records = self._deduplicated_records()
        counts: dict[str, int] = {}
        for r in records:
            st = r.get("source_type", "other")
            counts[st] = counts.get(st, 0) + 1
        return counts

    # ── Internals ──────────────────────────────────────────────────────────────

    def _all_records(self) -> list[dict]:
        if not REGISTRY_FILE.exists():
            return []
        records = []
        for line in REGISTRY_FILE.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records

    def _deduplicated_records(self) -> list[dict]:
        """Return latest state per artifact_id (latest update wins)."""
        records = self._all_records()
        seen: dict[str, dict] = {}
        for r in records:
            aid = r.get("artifact_id", "")
            if aid:
                seen[aid] = r
        return list(seen.values())

    def _append(self, record: dict) -> None:
        REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        with REGISTRY_FILE.open("a") as f:
            f.write(json.dumps(record) + "\n")

    def _try_supabase_write(self, record: dict) -> None:
        """Attempt Supabase write; log local-only if unavailable."""
        try:
            import os, urllib.request
            url  = os.getenv("SUPABASE_URL", "")
            key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
            if not url or not key:
                return
            payload = json.dumps({
                "artifact_id":   record["artifact_id"],
                "agent_name":    record["agent_name"],
                "artifact_type": record["artifact_type"],
                "source_type":   record["source_type"],
                "title":         record["title"],
                "summary":       record["summary"],
                "file_path":     record["file_path"],
                "status":        record["status"],
                "evidence_level": record["evidence_level"],
                "created_at":    record["created_at"],
                "metadata":      {
                    k: v for k, v in record.items()
                    if k not in ("artifact_id", "agent_name", "artifact_type",
                                 "source_type", "title", "summary", "file_path",
                                 "status", "evidence_level", "created_at")
                },
            }).encode()
            req = urllib.request.Request(
                f"{url}/rest/v1/nexus_artifacts",
                data=payload,
                headers={
                    "apikey":        key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                    "Prefer":        "return=minimal",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5):
                pass
        except Exception:
            pass  # Supabase unavailable — local registry only

    def _update_markdown_summary(self) -> None:
        try:
            REGISTRY_MD.write_text(self.create_registry_summary())
        except Exception:
            pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_registry = NexusArtifactRegistry()


def register_artifact(**kwargs) -> ArtifactRecord:
    return _registry.register_artifact(**kwargs)


def find_artifacts(**kwargs) -> list[ArtifactRecord]:
    return _registry.find_artifacts(**kwargs)


def latest_artifacts(limit: int = 20) -> list[ArtifactRecord]:
    return _registry.latest_artifacts(limit)


def find_by_source_url(url: str) -> list[ArtifactRecord]:
    return _registry.find_by_source_url(url)


def find_by_task_id(task_id: str) -> list[ArtifactRecord]:
    return _registry.find_by_task_id(task_id)


def find_youtube_artifacts() -> list[ArtifactRecord]:
    return _registry.find_youtube_artifacts()


def find_agent_outputs(agent_name: str) -> list[ArtifactRecord]:
    return _registry.find_agent_outputs(agent_name)


def mark_artifact_status(artifact_id: str, status: ArtifactStatus) -> bool:
    return _registry.mark_artifact_status(artifact_id, status)


def create_registry_summary() -> str:
    return _registry.create_registry_summary()
