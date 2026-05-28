"""
Hermes Artifact Memory
Tracks every produced artifact (path, type, run_id, ts, summary).
Lets Hermes answer "what was the last CEO packet?" without scanning the filesystem each time.
Persisted at docs/reports/hermes_artifact_memory.jsonl.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ARTIFACT_MEMORY_FILE = Path("docs/reports/hermes_artifact_memory.jsonl")
ARTIFACT_MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)


class HermesArtifactMemory:
    """
    Register and retrieve artifacts by type.
    """

    def register(
        self,
        artifact_type: str,
        path: str | Path,
        run_id: str = "",
        summary: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = {
            "artifact_type": artifact_type,
            "path": str(path),
            "run_id": run_id,
            "summary": summary,
            "metadata": metadata or {},
            "registered_at": datetime.utcnow().isoformat() + "Z",
        }
        with open(ARTIFACT_MEMORY_FILE, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def latest(self, artifact_type: str) -> dict[str, Any] | None:
        records = self._all_of_type(artifact_type)
        return records[-1] if records else None

    def history(self, artifact_type: str, n: int = 10) -> list[dict[str, Any]]:
        return self._all_of_type(artifact_type)[-n:]

    def all_types(self) -> list[str]:
        seen: set[str] = set()
        result = []
        for r in self._all():
            t = r.get("artifact_type", "")
            if t and t not in seen:
                seen.add(t)
                result.append(t)
        return result

    def summary_table(self) -> str:
        types = self.all_types()
        if not types:
            return "No artifacts registered yet."
        lines = ["| Type | Latest Artifact | Registered At |", "|------|----------------|---------------|"]
        for t in types:
            rec = self.latest(t)
            if rec:
                fname = Path(rec["path"]).name
                lines.append(f"| {t} | {fname} | {rec['registered_at'][:19]} |")
        return "\n".join(lines)

    def find_path(self, artifact_type: str) -> str | None:
        rec = self.latest(artifact_type)
        if rec:
            p = Path(rec["path"])
            return str(p) if p.exists() else None
        return None

    # ── internals ─────────────────────────────────────────────────────────────

    def _all(self) -> list[dict[str, Any]]:
        if not ARTIFACT_MEMORY_FILE.exists():
            return []
        lines = ARTIFACT_MEMORY_FILE.read_text().strip().splitlines()
        result = []
        for line in lines:
            try:
                result.append(json.loads(line))
            except Exception:
                pass
        return result

    def _all_of_type(self, artifact_type: str) -> list[dict[str, Any]]:
        return [r for r in self._all() if r.get("artifact_type") == artifact_type]


# ── Module-level singleton ─────────────────────────────────────────────────────
_memory = HermesArtifactMemory()


def register_artifact(artifact_type: str, path: str | Path, run_id: str = "", summary: str = "", **meta) -> dict:
    return _memory.register(artifact_type, path, run_id, summary, meta)


def latest_artifact(artifact_type: str) -> dict | None:
    return _memory.latest(artifact_type)


def artifact_summary_table() -> str:
    return _memory.summary_table()
