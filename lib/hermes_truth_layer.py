"""
hermes_truth_layer.py
======================
Collect verified evidence from all known artifact stores.
Returns a truth packet — never invents operational state.

Evidence levels (highest to lowest confidence):
  verified_file          — file exists on disk
  verified_supabase      — row confirmed in Supabase
  verified_workflow_output — workflow output artifact on disk
  verified_log           — JSONL log entry with timestamp
  unverified_claim       — ops_context reference only — NOT evidence

Core rule: ops_context counts are NOT evidence.
           Only artifact paths, Supabase IDs, and log entries are evidence.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class EvidenceItem:
    source: str                 # "artifact_registry", "supabase", "workflow_output", "source_intake", "decision_log"
    evidence_level: str         # "verified_file", "verified_supabase", "verified_log", "unverified_claim"
    label: str                  # human-readable description
    artifact_id: str = ""
    file_path: str = ""
    supabase_id: str = ""
    timestamp: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source":         self.source,
            "evidence_level": self.evidence_level,
            "label":          self.label,
            "artifact_id":    self.artifact_id,
            "file_path":      self.file_path,
            "supabase_id":    self.supabase_id,
            "timestamp":      self.timestamp,
            "metadata":       self.metadata,
        }


@dataclass
class TruthPacket:
    collected_at: str
    items: list[EvidenceItem] = field(default_factory=list)
    sources_probed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def verified_only(self) -> list[EvidenceItem]:
        return [i for i in self.items if i.evidence_level != "unverified_claim"]

    def by_source(self, source: str) -> list[EvidenceItem]:
        return [i for i in self.items if i.source == source]

    def summary_text(self) -> str:
        verified = self.verified_only()
        lines = [f"Evidence collected at {self.collected_at}:"]
        if not verified:
            lines.append("  No verified evidence found.")
        for item in verified[:20]:
            lines.append(f"  [{item.evidence_level}] {item.label}")
        if len(verified) > 20:
            lines.append(f"  ... and {len(verified) - 20} more verified items")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "collected_at":   self.collected_at,
            "sources_probed": self.sources_probed,
            "errors":         self.errors,
            "total":          len(self.items),
            "verified":       len(self.verified_only()),
            "items":          [i.to_dict() for i in self.items],
        }


# ── Collectors ────────────────────────────────────────────────────────────────

def _collect_artifact_registry(packet: TruthPacket) -> None:
    packet.sources_probed.append("artifact_registry")
    try:
        from lib.nexus_artifact_registry import REGISTRY_FILE
        if not REGISTRY_FILE.exists():
            return
        count = 0
        for line in REGISTRY_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                fpath = rec.get("file_path") or rec.get("artifact_path") or ""
                exists = bool(fpath and Path(fpath).exists())
                packet.items.append(EvidenceItem(
                    source="artifact_registry",
                    evidence_level="verified_file" if exists else "verified_log",
                    label=f"{rec.get('artifact_type','artifact')}: {Path(fpath).name if fpath else rec.get('artifact_id','')}",
                    artifact_id=rec.get("artifact_id") or rec.get("id") or "",
                    file_path=fpath,
                    timestamp=rec.get("registered_at") or rec.get("created_at") or "",
                    metadata={"agent": rec.get("agent_name",""), "artifact_type": rec.get("artifact_type","")},
                ))
                count += 1
                if count >= 100:
                    break
            except Exception:
                continue
    except Exception as e:
        packet.errors.append(f"artifact_registry: {e}")


def _collect_source_intake(packet: TruthPacket) -> None:
    packet.sources_probed.append("source_intake")
    try:
        from lib.hermes_telegram_source_intake import INTAKE_LOG
        if not INTAKE_LOG.exists():
            return
        count = 0
        for line in INTAKE_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                url = rec.get("url") or rec.get("raw_url") or ""
                packet.items.append(EvidenceItem(
                    source="source_intake",
                    evidence_level="verified_log",
                    label=f"source_intake: {url[:80]}",
                    artifact_id=rec.get("intake_id") or rec.get("source_id") or "",
                    timestamp=rec.get("submitted_at") or rec.get("created_at") or "",
                    metadata={"status": rec.get("status",""), "url": url},
                ))
                count += 1
                if count >= 50:
                    break
            except Exception:
                continue
    except Exception as e:
        packet.errors.append(f"source_intake: {e}")


def _collect_decision_logs(packet: TruthPacket) -> None:
    packet.sources_probed.append("decision_log")
    try:
        log_path = ROOT / "docs" / "reports" / "evidence" / "hermes_decision_log.jsonl"
        if not log_path.exists():
            return
        count = 0
        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                packet.items.append(EvidenceItem(
                    source="decision_log",
                    evidence_level="verified_log",
                    label=f"decision: {rec.get('decision_type','')} — {rec.get('summary','')[:60]}",
                    artifact_id=rec.get("decision_id") or "",
                    timestamp=rec.get("decided_at") or rec.get("timestamp") or "",
                ))
                count += 1
                if count >= 30:
                    break
            except Exception:
                continue
    except Exception as e:
        packet.errors.append(f"decision_log: {e}")


def _collect_workflow_outputs(packet: TruthPacket) -> None:
    packet.sources_probed.append("workflow_outputs")
    try:
        out_dir = ROOT / "docs" / "reports" / "evidence"
        if not out_dir.exists():
            return
        count = 0
        for f in sorted(out_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if count >= 20:
                break
            packet.items.append(EvidenceItem(
                source="workflow_outputs",
                evidence_level="verified_file",
                label=f"report: {f.name}",
                file_path=str(f),
                timestamp=datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            ))
            count += 1
    except Exception as e:
        packet.errors.append(f"workflow_outputs: {e}")


def _collect_agent_handoffs(packet: TruthPacket) -> None:
    packet.sources_probed.append("agent_handoffs")
    try:
        handoff_dir = ROOT / "docs" / "reports" / "agent_handoffs"
        if not handoff_dir.exists():
            return
        count = 0
        for f in sorted(handoff_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            if count >= 20:
                break
            packet.items.append(EvidenceItem(
                source="agent_handoffs",
                evidence_level="verified_file",
                label=f"handoff: {f.name}",
                file_path=str(f),
                timestamp=datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
            ))
            count += 1
    except Exception as e:
        packet.errors.append(f"agent_handoffs: {e}")


def _collect_supabase_recent(packet: TruthPacket) -> None:
    packet.sources_probed.append("supabase")
    try:
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not supabase_url or not supabase_key:
            return
        import urllib.request
        url = f"{supabase_url}/rest/v1/nexus_artifact_registry?select=id,artifact_type,file_path,registered_at&order=registered_at.desc&limit=10"
        req = urllib.request.Request(url, headers={
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=5) as resp:
            rows = json.loads(resp.read())
        for row in rows:
            packet.items.append(EvidenceItem(
                source="supabase",
                evidence_level="verified_supabase",
                label=f"supabase artifact: {row.get('artifact_type','')} id={row.get('id','')}",
                supabase_id=str(row.get("id", "")),
                file_path=row.get("file_path") or "",
                timestamp=row.get("registered_at") or "",
            ))
    except Exception as e:
        packet.errors.append(f"supabase: {e}")


# ── Main collector ─────────────────────────────────────────────────────────────

def collect_truth(
    include_supabase: bool = False,
) -> TruthPacket:
    """Collect all available verified evidence. Returns TruthPacket."""
    packet = TruthPacket(
        collected_at=datetime.now(timezone.utc).isoformat(),
    )
    _collect_artifact_registry(packet)
    _collect_source_intake(packet)
    _collect_decision_logs(packet)
    _collect_workflow_outputs(packet)
    _collect_agent_handoffs(packet)
    if include_supabase:
        _collect_supabase_recent(packet)
    return packet
