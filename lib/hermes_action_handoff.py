"""
Hermes Action Handoff
Creates structured handoff packets when Hermes identifies an action that requires
Ray's attention or approval — instead of acting autonomously on approval-required items.
Also handles Ray feedback saving (Part 9).
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

HANDOFF_DIR  = Path("docs/reports/hermes_handoffs")
FEEDBACK_DIR = Path("docs/reports/ray_feedback")
HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

HANDOFF_STATUSES = ("pending_ray", "in_progress", "approved", "rejected", "done")


class HermesActionHandoff:
    """
    Create structured handoff packets for Ray.
    Used when Hermes identifies an action that requires approval.
    """

    def create_handoff(
        self,
        title: str,
        action_required: str,
        context: str,
        urgency: str = "normal",
        artifacts: list[str] | None = None,
        options: list[dict] | None = None,
        run_id: str = "",
    ) -> dict[str, Any]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        handoff_id = f"handoff_{ts}"
        packet = {
            "handoff_id": handoff_id,
            "run_id": run_id,
            "title": title,
            "action_required": action_required,
            "context": context,
            "urgency": urgency,               # normal | high | critical
            "artifacts": artifacts or [],
            "options": options or [],          # [{label, description, consequence}]
            "status": "pending_ray",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "resolved_at": None,
            "resolution_note": "",
        }
        path = self._save_handoff(packet, ts)
        packet["path"] = str(path)
        return packet

    def resolve_handoff(
        self,
        handoff_id: str,
        status: str,
        resolution_note: str = "",
    ) -> dict[str, Any] | None:
        files = list(HANDOFF_DIR.glob(f"*{handoff_id}*.json"))
        if not files:
            return None
        packet = json.loads(files[0].read_text())
        packet["status"] = status
        packet["resolved_at"] = datetime.utcnow().isoformat() + "Z"
        packet["resolution_note"] = resolution_note
        files[0].write_text(json.dumps(packet, indent=2))
        return packet

    def pending_handoffs(self) -> list[dict[str, Any]]:
        result = []
        for f in sorted(HANDOFF_DIR.glob("*.json")):
            try:
                p = json.loads(f.read_text())
                if p.get("status") == "pending_ray":
                    result.append(p)
            except Exception:
                pass
        return result

    def all_handoffs(self, n: int = 20) -> list[dict[str, Any]]:
        files = sorted(HANDOFF_DIR.glob("*.json"))[-n:]
        result = []
        for f in files:
            try:
                result.append(json.loads(f.read_text()))
            except Exception:
                pass
        return result

    def _save_handoff(self, packet: dict, ts: str) -> Path:
        slug = packet["title"][:40].replace(" ", "_").lower()
        path = HANDOFF_DIR / f"handoff_{ts}_{slug}.json"
        path.write_text(json.dumps(packet, indent=2))
        # Also save markdown summary
        md = self._render_md(packet)
        md_path = HANDOFF_DIR / f"handoff_{ts}_{slug}.md"
        md_path.write_text(md)
        return path

    def _render_md(self, p: dict) -> str:
        lines = [
            f"# Handoff: {p['title']}",
            f"*ID: {p['handoff_id']} | Created: {p['created_at'][:19]} | Urgency: {p['urgency']}*\n",
            f"## Action Required",
            p["action_required"],
            "",
            f"## Context",
            p["context"],
            "",
        ]
        if p.get("artifacts"):
            lines.append("## Related Artifacts")
            for a in p["artifacts"]:
                lines.append(f"- `{a}`")
            lines.append("")
        if p.get("options"):
            lines.append("## Options for Ray")
            for opt in p["options"]:
                lines.append(f"### {opt.get('label', 'Option')}")
                lines.append(opt.get("description", ""))
                if opt.get("consequence"):
                    lines.append(f"*Consequence: {opt['consequence']}*")
                lines.append("")
        lines.append(f"**Status:** {p['status']}")
        return "\n".join(lines)


class RayFeedbackStore:
    """
    Save Ray's feedback/lessons for future Hermes context.
    """

    def save(self, message: str, category: str = "general", run_id: str = "") -> dict[str, Any]:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        record = {
            "feedback_id": f"feedback_{ts}",
            "run_id": run_id,
            "category": category,
            "message": message,
            "saved_at": datetime.utcnow().isoformat() + "Z",
        }
        path = FEEDBACK_DIR / f"ray_feedback_{ts}.json"
        path.write_text(json.dumps(record, indent=2))
        record["path"] = str(path)
        return record

    def recent(self, n: int = 10) -> list[dict[str, Any]]:
        files = sorted(FEEDBACK_DIR.glob("ray_feedback_*.json"))[-n:]
        result = []
        for f in files:
            try:
                result.append(json.loads(f.read_text()))
            except Exception:
                pass
        return result

    def by_category(self, category: str) -> list[dict[str, Any]]:
        return [r for r in self.recent(100) if r.get("category") == category]


# ── Singletons ─────────────────────────────────────────────────────────────────
_handoff  = HermesActionHandoff()
_feedback = RayFeedbackStore()


def create_handoff(title: str, action_required: str, context: str, **kwargs) -> dict:
    return _handoff.create_handoff(title, action_required, context, **kwargs)


def save_ray_feedback(message: str, category: str = "general", run_id: str = "") -> dict:
    return _feedback.save(message, category, run_id)


def pending_handoffs() -> list[dict]:
    return _handoff.pending_handoffs()
