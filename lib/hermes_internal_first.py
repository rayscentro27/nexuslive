from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import json
import os
from pathlib import Path

from lib import hermes_ops_memory
from lib.hermes_knowledge_brain import get_funding_knowledge, get_recent_recommendations
from lib.demo_readiness import run_demo_readiness_check
from lib.hermes_email_knowledge_intake import recent_knowledge_email_intake
from lib.hermes_runtime_config import get_internal_first_keywords
from lib.operational_priorities import top_focus_summary
from lib.notebooklm_ingest_adapter import load_dry_run_queue, summarize_intake_queue


CONF_INTERNAL_CONFIRMED = "INTERNAL_CONFIRMED"
CONF_INTERNAL_PARTIAL = "INTERNAL_PARTIAL"
CONF_INTERNAL_STALE = "INTERNAL_STALE"
CONF_GENERAL_FALLBACK = "GENERAL_FALLBACK"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_stale(updated_at: str, stale_hours: int = 72) -> bool:
    if not updated_at:
        return True
    try:
        dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        age_seconds = (datetime.now(timezone.utc) - dt).total_seconds()
        return age_seconds > (int(stale_hours) * 3600)
    except Exception:
        return True


def _default_rules() -> dict[str, list[str]]:
    return get_internal_first_keywords()


def _parse_json_env(name: str, default: dict[str, list[str]]) -> dict[str, list[str]]:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): [str(x).lower() for x in (v or [])] for k, v in data.items()}
    except Exception:
        pass
    return default


@dataclass
class InternalFirstReply:
    text: str
    confidence: str
    source: str
    matched_topic: str


def try_internal_first(raw: str) -> InternalFirstReply | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
    rules = _parse_json_env("HERMES_INTERNAL_FIRST_KEYWORDS", _default_rules())
    topic = ""
    for key, phrases in rules.items():
        if any(p in text for p in phrases):
            topic = key
            break
    if not topic:
        return None

    mem = hermes_ops_memory.load_memory(updated_by="internal_first_reply")
    mem_updated = str(mem.get("updated_at") or "")
    stale = _is_stale(mem_updated, stale_hours=72)
    confidence_default = CONF_INTERNAL_STALE if stale else CONF_INTERNAL_CONFIRMED
    if topic == "opencode":
        done = mem.get("recent_completed") or []
        if done:
            latest = done[-3:]
            bullets = "; ".join(str(x.get("task") or x) for x in latest)
            return InternalFirstReply(
                text=f"Direct answer: latest completed work includes {bullets}.\nSource: internal operational memory.\nNext: ask 'show pending tasks' for the active queue.",
                confidence=confidence_default,
                source="operational_memory.recent_completed",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="Direct answer: I do not have recent completed OpenCode/Codex tasks in internal memory yet.\nSource: internal operational memory.\nNext: run a fresh status snapshot to update activity.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="operational_memory",
            matched_topic=topic,
        )

    if topic == "funding":
        rows = get_funding_knowledge(limit=3)
        if rows:
            bullets = "; ".join(str(r.get("summary") or "").strip()[:120] for r in rows if str(r.get("summary") or "").strip())
            return InternalFirstReply(
                text=f"Direct answer: current funding blockers/signals: {bullets}.\nSource: funding intelligence from Knowledge Brain.\nNext: clear the top blocker, then rerun readiness check.",
                confidence=confidence_default,
                source="knowledge_brain.funding",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="Direct answer: no fresh funding blockers are recorded internally.\nSource: funding intelligence/Knowledge Brain.\nNext: run funding workflow review to refresh data.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="knowledge_brain.funding",
            matched_topic=topic,
        )

    if topic == "today":
        recs = get_recent_recommendations(limit=3)
        pending = mem.get("pending_approval_refs") or []
        first = (recs[0].get("summary") if recs else "Review pending approvals and clear blockers.")
        focus = top_focus_summary()
        return InternalFirstReply(
            text=f"Direct answer: start with '{first}'.\nInternal priorities:\n{focus}\nSource: internal recommendations + approvals ({len(pending)} pending).\nNext: close approvals first, then highest-impact workflow.",
            confidence=confidence_default,
            source="operational_memory+knowledge_brain",
            matched_topic=topic,
        )

    if topic == "knowledge_email":
        rows = recent_knowledge_email_intake(limit=5)
        if rows:
            return InternalFirstReply(
                text=f"Direct answer: {len(rows)} recent knowledge-intake email runs are recorded.\nSource: internal knowledge intake reports.\nNext: ask for full report by email if you want details.",
                confidence=confidence_default,
                source="knowledge_email_intake",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="Direct answer: no recent knowledge-intake email runs found.\nSource: internal knowledge intake records.\nNext: send a 'Knowledge Load' email to seed intake.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="knowledge_email_intake",
            matched_topic=topic,
        )

    if topic == "travel":
        ready = run_demo_readiness_check()
        score = ready.get("score")
        status = ready.get("status")
        return InternalFirstReply(
            text=f"Direct answer: remote readiness is {status} ({score}).\nSource: internal demo/remote readiness checks.\nNext: verify pending approvals and today priorities before travel.",
            confidence=confidence_default,
            source="demo_readiness",
            matched_topic=topic,
        )

    if topic == "notebooklm":
        queue_path = Path(__file__).resolve().parent.parent / "reports" / "knowledge_intake" / "notebooklm_intake_queue.json"
        queue = load_dry_run_queue(str(queue_path))
        msg = summarize_intake_queue(queue)
        return InternalFirstReply(
            text=f"Direct answer: {msg}\nSource: NotebookLM dry-run intake queue.",
            confidence=confidence_default if queue else CONF_INTERNAL_PARTIAL,
            source=str(queue_path),
            matched_topic=topic,
        )

    if topic == "marketing":
        root = Path(__file__).resolve().parent.parent
        files = [
            root / "marketing" / "launch_checklist.md",
            root / "marketing" / "content_calendar_30_days.md",
            root / "marketing" / "social_profile_copy.md",
            root / "marketing" / "beta_invite_email_v2.md",
        ]
        ready = [p.name for p in files if p.exists()]
        if ready:
            return InternalFirstReply(
                text=(
                    "Direct answer: marketing artifacts are staged and pending execution review.\n"
                    f"Ready docs: {', '.join(ready[:4])}.\n"
                    "Next: run soft-launch checklist and approve first weekly content batch."
                ),
                confidence=confidence_default,
                source="marketing/*.md",
                matched_topic=topic,
            )
        return InternalFirstReply(
            text="Direct answer: no marketing research artifacts were found in the current local set.\nNext: generate/update marketing docs before launch.",
            confidence=CONF_INTERNAL_PARTIAL,
            source="marketing/",
            matched_topic=topic,
        )

    return None
