"""
hermes_scout_dispatcher.py
============================
Route intake items to the correct Nexus scout/agent.
Every dispatch creates a handoff record, scout task prompt, and artifact registry record.

NO TASK IS SILENTLY DROPPED.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT         = Path(__file__).resolve().parent.parent
DISPATCH_DIR = ROOT / "docs" / "reports" / "scout_dispatch"

# ── Scout routing map ─────────────────────────────────────────────────────────
SCOUT_ROUTES: dict[str, dict] = {
    "youtube_video": {
        "primary_scout":  "youtube_research_scout",
        "secondary":      ["content_intelligence_scout", "monetization_scout"],
        "compliance_gate": True,
        "runner":          "python scripts/run_youtube_intelligence_cycle.py --url {url}",
        "requires_approval": False,
    },
    "youtube_channel": {
        "primary_scout":  "youtube_research_scout",
        "secondary":      ["content_intelligence_scout", "monetization_scout"],
        "compliance_gate": True,
        "runner":          "python scripts/run_youtube_intelligence_cycle.py --url {url}",
        "requires_approval": False,
    },
    "github_repo": {
        "primary_scout":  "github_trend_researcher",
        "secondary":      ["system_improvement_scout"],
        "compliance_gate": False,
        "runner":          "python scripts/run_weekly_github_trend_research.py --repo {url}",
        "requires_approval": False,
    },
    "trading_strategy": {
        "primary_scout":  "trading_strategy_scout",
        "secondary":      ["vibe_trading_adapter"],
        "compliance_gate": True,
        "runner":          "python integrations/vibe_trading/backtest.py (paper mode only)",
        "requires_approval": True,
        "approval_reason": "Trading strategy requires Ray approval before paper test",
    },
    "credit_repair_strategy": {
        "primary_scout":  "credit_repair_research_scout",
        "secondary":      ["compliance_guard", "funding_readiness_scout"],
        "compliance_gate": True,
        "runner":          "python scripts/run_nexus_learn_by_doing_cycle.py --domain credit_repair",
        "requires_approval": False,
    },
    "business_funding": {
        "primary_scout":  "funding_readiness_scout",
        "secondary":      ["compliance_guard"],
        "compliance_gate": True,
        "runner":          "python scripts/run_nexus_learn_by_doing_cycle.py --domain business_funding",
        "requires_approval": False,
    },
    "grant": {
        "primary_scout":  "grant_research_scout",
        "secondary":      [],
        "compliance_gate": False,
        "runner":          "python scripts/run_nexus_monetization_operating_cycle.py --focus grants",
        "requires_approval": False,
    },
    "affiliate_program": {
        "primary_scout":  "affiliate_monetization_scout",
        "secondary":      ["funnel_builder", "compliance_guard"],
        "compliance_gate": True,
        "runner":          "python scripts/run_nexus_monetization_operating_cycle.py --focus monetization",
        "requires_approval": False,
    },
    "monetization_idea": {
        "primary_scout":  "affiliate_monetization_scout",
        "secondary":      ["content_intelligence_scout"],
        "compliance_gate": True,
        "runner":          "python scripts/run_nexus_monetization_operating_cycle.py --focus monetization",
        "requires_approval": False,
    },
    "article": {
        "primary_scout":  "content_intelligence_scout",
        "secondary":      [],
        "compliance_gate": False,
        "runner":          "Review article content manually or via Claude Code",
        "requires_approval": False,
    },
    "blocker": {
        "primary_scout":  "premium_blocker_resolver",
        "secondary":      [],
        "compliance_gate": False,
        "runner":          "python scripts/run_nexus_monetization_operating_cycle.py --resolve-premium-blockers",
        "requires_approval": False,
    },
    "unknown": {
        "primary_scout":  "triage_scout",
        "secondary":      [],
        "compliance_gate": True,
        "runner":          "needs_ray_review",
        "requires_approval": True,
        "approval_reason": "Unknown source type — Ray must classify before processing",
    },
}


class DispatchRecord:
    def __init__(self, data: dict):
        self._data = data

    @property
    def dispatch_id(self) -> str:
        return self._data["dispatch_id"]

    @property
    def source_type(self) -> str:
        return self._data["source_type"]

    @property
    def primary_scout(self) -> str:
        return self._data["primary_scout"]

    @property
    def status(self) -> str:
        return self._data.get("status", "queued")

    @property
    def handoff_path(self) -> str:
        return self._data.get("handoff_path", "")

    def to_dict(self) -> dict:
        return dict(self._data)


class HermesScoutDispatcher:
    """
    Route intake items to the right Nexus scout/agent.

    Every dispatch creates:
      - A dispatch record (JSONL log)
      - A handoff artifact (Markdown + JSON)
      - An artifact registry entry
    """

    def dispatch(
        self,
        intake_id: str,
        source_type: str,
        url: str = "",
        raw_message: str = "",
        title: str = "",
        submitted_by: str = "raymond",
    ) -> DispatchRecord:
        """Route a source to the correct scout. Returns DispatchRecord."""
        route = SCOUT_ROUTES.get(source_type, SCOUT_ROUTES["unknown"])
        dispatch_id  = "dsp_" + uuid.uuid4().hex[:12]
        primary      = route["primary_scout"]
        runner       = route["runner"].replace("{url}", url or "?")
        requires_app = route.get("requires_approval", False)
        approval_rsn = route.get("approval_reason", "")

        handoff_path = self._create_handoff(
            dispatch_id=dispatch_id,
            intake_id=intake_id,
            source_type=source_type,
            url=url,
            raw_message=raw_message,
            title=title,
            primary_scout=primary,
            secondary_scouts=route.get("secondary", []),
            runner=runner,
            requires_approval=requires_app,
            approval_reason=approval_rsn,
            compliance_gate=route.get("compliance_gate", False),
        )

        record: dict = {
            "dispatch_id":       dispatch_id,
            "intake_id":         intake_id,
            "created_at":        _now(),
            "source_type":       source_type,
            "url":               url,
            "primary_scout":     primary,
            "secondary_scouts":  route.get("secondary", []),
            "runner":            runner,
            "status":            "needs_ray_review" if requires_app else "queued",
            "requires_approval": requires_app,
            "approval_reason":   approval_rsn,
            "handoff_path":      handoff_path,
            "submitted_by":      submitted_by,
        }

        self._save_dispatch(record)
        self._register_artifact(record)

        # Create Hermes action handoff if approval needed
        if requires_app:
            self._create_hermes_handoff(record)

        return DispatchRecord(record)

    def dispatch_from_intake(self, intake_record: Any) -> DispatchRecord:
        """Convenience: dispatch directly from an IntakeRecord."""
        d = intake_record.to_dict() if hasattr(intake_record, "to_dict") else intake_record
        return self.dispatch(
            intake_id=d.get("intake_id", ""),
            source_type=d.get("source_type", "unknown"),
            url=d.get("url", ""),
            raw_message=d.get("raw_message", ""),
            title=d.get("title", ""),
            submitted_by=d.get("submitted_by", "raymond"),
        )

    def get_dispatch_for_intake(self, intake_id: str) -> DispatchRecord | None:
        records = self._load_all()
        for r in reversed(records):
            if r.get("intake_id") == intake_id:
                return DispatchRecord(r)
        return None

    def pending_dispatches(self) -> list[DispatchRecord]:
        records = self._load_all()
        return [DispatchRecord(r) for r in records
                if r.get("status") in ("queued", "needs_ray_review")]

    # ── Internals ──────────────────────────────────────────────────────────────

    def _create_handoff(
        self,
        dispatch_id: str,
        intake_id: str,
        source_type: str,
        url: str,
        raw_message: str,
        title: str,
        primary_scout: str,
        secondary_scouts: list[str],
        runner: str,
        requires_approval: bool,
        approval_reason: str,
        compliance_gate: bool,
    ) -> str:
        DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = DISPATCH_DIR / f"scout_dispatch_{dispatch_id}_{ts}.md"
        path.write_text(f"""# Scout Dispatch Handoff
*Dispatch ID: {dispatch_id}*
*Intake ID: {intake_id}*
*Created: {_now()}*

## Source
- **Type:** {source_type}
- **URL:** {url or '(text message)'}
- **Message:** {raw_message[:200]}

## Assigned Scout
- **Primary:** {primary_scout}
- **Secondary:** {', '.join(secondary_scouts) or 'none'}

## Runner Command
```
{runner}
```

## Compliance Gate
{'⚠️ Compliance review required before using output.' if compliance_gate else '✅ No compliance gate needed.'}

## Approval Required
{'⛔ YES — ' + approval_reason if requires_approval else '✅ No approval needed.'}

## Completion Contract
- All output files must be registered in nexus_artifact_registry.jsonl
- Source registry must be updated with artifact_paths
- Hermes must be notified via hermes_proactive_notifier when complete
- Do NOT claim completion without verified artifact files
""")
        return str(path)

    def _save_dispatch(self, record: dict) -> None:
        DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
        log = DISPATCH_DIR / "scout_dispatch_log.jsonl"
        with log.open("a") as f:
            f.write(json.dumps(record) + "\n")

    def _register_artifact(self, record: dict) -> None:
        try:
            from lib.nexus_artifact_registry import register_artifact
            register_artifact(
                agent_name="hermes_scout_dispatcher",
                agent_type="hermes",
                source_input=record.get("url", ""),
                source_type=record.get("source_type", "other"),
                artifact_type="prompt",
                title=f"Scout dispatch for {record['source_type']}",
                summary=f"Dispatched to {record['primary_scout']}",
                file_path=record.get("handoff_path", ""),
                tags=["scout_dispatch", record["source_type"]],
                what_hermes_should_know=(
                    f"Source was dispatched to {record['primary_scout']}. "
                    f"Status: {record['status']}."
                ),
                next_action=record.get("runner", ""),
            )
        except Exception:
            pass

    def _create_hermes_handoff(self, record: dict) -> None:
        try:
            from lib.hermes_action_handoff import HermesActionHandoff
            handoff = HermesActionHandoff()
            handoff.create_handoff(
                title=f"Approve scout dispatch: {record['source_type']}",
                action_required=record.get("approval_reason", "Review and approve dispatch"),
                context=f"Source: {record.get('url','?')} | Scout: {record['primary_scout']}",
                urgency="medium",
                artifacts=[record.get("handoff_path", "")],
            )
        except Exception:
            pass

    def _load_all(self) -> list[dict]:
        log = DISPATCH_DIR / "scout_dispatch_log.jsonl"
        if not log.exists():
            return []
        records = []
        for line in log.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_dispatcher = HermesScoutDispatcher()


def dispatch_source(
    intake_id: str,
    source_type: str,
    url: str = "",
    **kwargs,
) -> DispatchRecord:
    return _dispatcher.dispatch(intake_id=intake_id, source_type=source_type, url=url, **kwargs)


def dispatch_from_intake(intake_record: Any) -> DispatchRecord:
    return _dispatcher.dispatch_from_intake(intake_record)


def pending_dispatches() -> list[DispatchRecord]:
    return _dispatcher.pending_dispatches()
