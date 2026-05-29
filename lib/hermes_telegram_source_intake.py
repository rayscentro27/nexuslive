"""
hermes_telegram_source_intake.py
===================================
Process links and source messages sent by Ray through Telegram.

Every source Ray sends gets:
  1. Detected and classified
  2. An intake record (local + Supabase)
  3. A source registry entry (YouTube, GitHub, etc.)
  4. A scout/agent dispatch assignment
  5. An artifact registry record
  6. A reply to Ray

NO SOURCE DISAPPEARS. Every Telegram link creates a persistent record.

Storage:
  docs/reports/intake/telegram_source_intake.jsonl
  docs/reports/intake/telegram_source_intake_latest.md
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

ROOT       = Path(__file__).resolve().parent.parent
INTAKE_DIR = ROOT / "docs" / "reports" / "intake"
INTAKE_LOG = INTAKE_DIR / "telegram_source_intake.jsonl"
INTAKE_MD  = INTAKE_DIR / "telegram_source_intake_latest.md"

SourceType = Literal[
    "youtube_video", "youtube_channel",
    "github_repo",
    "article",
    "affiliate_program",
    "trading_strategy",
    "credit_repair_strategy",
    "business_funding",
    "grant",
    "monetization_idea",
    "nexus_improvement",
    "unknown",
]

IntakeStatus = Literal[
    "received", "registered", "routed", "queued",
    "processing", "completed", "blocked", "failed", "needs_ray_review",
]

# ── URL detectors ─────────────────────────────────────────────────────────────
_YT_VIDEO_RE   = re.compile(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)', re.I)
_YT_CHANNEL_RE = re.compile(r'https?://(?:www\.)?youtube\.com/(?:channel/[\w-]+|@[\w-]+|c/[\w-]+)', re.I)
_GITHUB_RE     = re.compile(r'https?://github\.com/[\w.-]+/[\w.-]+', re.I)
_URL_RE        = re.compile(r'https?://[^\s<>"\']+', re.I)

# ── Text pattern classifiers ──────────────────────────────────────────────────
_TRADING_KW    = ["scalp", "backtest", "strategy", "eur/usd", "gbp/usd", "forex",
                  "moving average", "rsi", "macd", "support", "resistance"]
_CREDIT_KW     = ["credit repair", "dispute letter", "collection", "fico", "credit score",
                  "charge-off", "derogatory", "credit report"]
_FUNDING_KW    = ["grant", "sba loan", "business funding", "startup capital",
                  "angel investor", "venture capital", "crowdfunding"]
_AFFILIATE_KW  = ["affiliate", "commission", "referral program", "partner program",
                  "earn per sale", "recurring commission"]
_MONETI_KW     = ["monetization", "revenue stream", "passive income", "side hustle",
                  "lead magnet", "funnel", "offer"]


class IntakeRecord:
    def __init__(self, data: dict):
        self._data = data

    @property
    def intake_id(self) -> str:
        return self._data["intake_id"]

    @property
    def source_type(self) -> str:
        return self._data["source_type"]

    @property
    def url(self) -> str:
        return self._data.get("url", "")

    @property
    def status(self) -> str:
        return self._data.get("status", "received")

    @property
    def assigned_scout(self) -> str:
        return self._data.get("assigned_scout", "")

    def to_dict(self) -> dict:
        return dict(self._data)

    def telegram_reply(self) -> str:
        """Build a Telegram reply message for Ray."""
        st = self.source_type.replace("_", " ").title()
        scout = self.assigned_scout or "triage_scout"
        url_line = f"\nURL: {self.url}" if self.url else ""
        intent = self._data.get("attached_intent", "").strip()
        intent_line = f"\nRay's question: \"{intent}\"" if intent else ""
        artifact_id = self._data.get("artifact_registry_id", "")
        artifact_line = f"\nArtifact: {artifact_id}" if artifact_id else ""
        intake_path = f"docs/reports/intake/telegram_source_intake.jsonl"
        pending = self._data.get("next_action", "run_nexus_operating_cycle")
        return (
            f"NEXUS SOURCE RECEIVED\n"
            f"\nType: {st}{url_line}{intent_line}"
            f"\nStatus: {self.status}"
            f"\nAssigned scout: {scout}"
            f"\nIntake ID: {self.intake_id[:20]}"
            f"{artifact_line}"
            f"\n\nArtifacts pending:"
            f"\n  - transcript / content extraction"
            f"\n  - quality review"
            f"\n  - recommendation packet"
            f"\nNext action: {pending}"
            f"\nEvidence: {intake_path}"
            f"\n\nI will process this source or create a handoff if direct processing is unavailable."
        )


class HermesTelegramSourceIntake:
    """
    Process any Telegram message from Ray that contains a URL or source idea.
    Classifies, registers, dispatches, and replies.
    """

    def process(
        self,
        raw_message: str,
        submitted_by: str = "raymond",
        attached_intent: str = "",
    ) -> "IntakeRecord":
        """
        Main entry point. Process any incoming Telegram message.
        Returns an IntakeRecord (always — never raises).

        attached_intent: the user's question when a URL arrived in a larger message.
        """
        url         = self._extract_url(raw_message)
        source_type = self._classify(raw_message, url)
        priority    = self._priority(source_type)
        scout       = self._assign_scout(source_type, raw_message)

        # Strip the URL from the message to isolate the question
        intent = attached_intent or raw_message
        import re as _re
        intent_text = _re.sub(r'https?://\S+', '', intent).strip(" ,.-")

        record = {
            "intake_id":              "src_" + uuid.uuid4().hex[:16],
            "submitted_by":           submitted_by,
            "submitted_at":           _now(),
            "platform":               "telegram",
            "source_type":            source_type,
            "raw_message":            raw_message[:500],
            "url":                    url,
            "title":                  "",
            "classification":         source_type,
            "priority":               priority,
            "assigned_scout":         scout,
            "status":                 "registered",
            "supabase_id":            "",
            "artifact_registry_id":   "",
            "workflow_output_id":     "",
            "next_action":            self._next_action(source_type),
            "requires_ray_approval":  self._requires_approval(source_type),
            "attached_intent":        intent_text[:200],
            "error":                  "",
        }

        self._save_intake(record)
        self._register_in_source_registry(record)
        self._register_in_artifact_registry(record)
        self._try_supabase_write(record)
        self._create_claude_code_handoff_if_needed(record)

        return IntakeRecord(record)

    def get_recent(self, limit: int = 10) -> list[IntakeRecord]:
        """Return the most recent intake records."""
        records = self._load_all()
        return [IntakeRecord(r) for r in records[-limit:]]

    def get_by_intake_id(self, intake_id: str) -> IntakeRecord | None:
        for r in self._load_all():
            if r.get("intake_id") == intake_id:
                return IntakeRecord(r)
        return None

    def intake_summary(self) -> str:
        """Return a human-readable summary of the intake queue."""
        records = self._load_all()
        if not records:
            return "No sources received yet. Send Ray a link or idea."
        counts: dict[str, int] = {}
        for r in records:
            st = r.get("source_type", "unknown")
            counts[st] = counts.get(st, 0) + 1
        lines = [f"**Telegram Source Intake** ({len(records)} total)"]
        for st, n in sorted(counts.items()):
            lines.append(f"  • {st}: {n}")
        # Show latest 3
        lines.append("\n**Most Recent:**")
        for r in records[-3:]:
            name = r.get("url") or r.get("raw_message", "")[:40]
            lines.append(f"  [{r.get('intake_id','?')[:12]}] {r.get('source_type','?')} — {name}")
        return "\n".join(lines)

    # ── Classification ─────────────────────────────────────────────────────────

    def _extract_url(self, text: str) -> str:
        m = _URL_RE.search(text)
        return m.group(0).rstrip(".,);\"'") if m else ""

    def _classify(self, text: str, url: str) -> SourceType:
        lower = text.lower()
        if url:
            if _YT_VIDEO_RE.search(url):
                return "youtube_video"
            if _YT_CHANNEL_RE.search(url):
                return "youtube_channel"
            if _GITHUB_RE.search(url):
                return "github_repo"
        if any(kw in lower for kw in _TRADING_KW):
            return "trading_strategy"
        if any(kw in lower for kw in _CREDIT_KW):
            return "credit_repair_strategy"
        if any(kw in lower for kw in _FUNDING_KW):
            return "business_funding"
        if any(kw in lower for kw in _AFFILIATE_KW):
            return "affiliate_program"
        if any(kw in lower for kw in _MONETI_KW):
            return "monetization_idea"
        if url:
            return "article"
        return "unknown"

    def _assign_scout(self, source_type: SourceType, text: str) -> str:
        scout_map = {
            "youtube_video":          "youtube_research_scout",
            "youtube_channel":        "youtube_research_scout",
            "github_repo":            "github_trend_researcher",
            "article":                "content_intelligence_scout",
            "affiliate_program":      "affiliate_monetization_scout",
            "trading_strategy":       "trading_strategy_scout",
            "credit_repair_strategy": "credit_repair_research_scout",
            "business_funding":       "funding_readiness_scout",
            "grant":                  "grant_research_scout",
            "monetization_idea":      "affiliate_monetization_scout",
            "nexus_improvement":      "system_improvement_scout",
            "unknown":                "triage_scout",
        }
        return scout_map.get(source_type, "triage_scout")

    def _priority(self, source_type: SourceType) -> str:
        high = {"trading_strategy", "business_funding", "grant", "youtube_channel"}
        low  = {"nexus_improvement", "unknown"}
        if source_type in high:
            return "high"
        if source_type in low:
            return "low"
        return "medium"

    def _requires_approval(self, source_type: SourceType) -> bool:
        return source_type in {"trading_strategy"}

    def _next_action(self, source_type: SourceType) -> str:
        actions = {
            "youtube_video":          "run_youtube_intelligence_cycle",
            "youtube_channel":        "run_youtube_intelligence_cycle",
            "github_repo":            "run_github_trend_research",
            "trading_strategy":       "run_trading_strategy_scout (requires Ray approval)",
            "credit_repair_strategy": "run_credit_repair_research",
            "business_funding":       "run_funding_readiness_research",
            "affiliate_program":      "run_affiliate_monetization_scout",
            "unknown":                "needs_ray_review",
        }
        return actions.get(source_type, "run_nexus_operating_cycle")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save_intake(self, record: dict) -> None:
        INTAKE_DIR.mkdir(parents=True, exist_ok=True)
        with INTAKE_LOG.open("a") as f:
            f.write(json.dumps(record) + "\n")
        self._update_md_summary()

    def _register_in_source_registry(self, record: dict) -> None:
        url = record.get("url", "")
        if not url:
            return
        source_type = record.get("source_type", "unknown")
        if source_type not in ("youtube_video", "youtube_channel"):
            return
        try:
            from lib.youtube_source_registry import _registry
            yt_type = "video" if source_type == "youtube_video" else "channel"
            src = _registry.register(
                url=url,
                source_type=yt_type,
                submitted_by=record.get("submitted_by", "raymond"),
                notes=f"Registered via Telegram intake {record['intake_id']}",
            )
            record["artifact_registry_id"] = src.source_id
        except Exception:
            pass

    def _register_in_artifact_registry(self, record: dict) -> None:
        try:
            from lib.nexus_artifact_registry import register_artifact
            art = register_artifact(
                agent_name="hermes_telegram_intake",
                agent_type="hermes",
                source_input=record.get("url") or record.get("raw_message", "")[:200],
                source_type=self._map_source_type(record.get("source_type", "other")),
                artifact_type="source_registry",
                title=f"Telegram intake {record['intake_id'][:8]}",
                summary=f"Source type: {record['source_type']} | Scout: {record.get('assigned_scout','')}",
                status="created",
                tags=["telegram_intake", record["source_type"]],
                what_hermes_should_know=(
                    f"Ray submitted this source via Telegram. "
                    f"Scout: {record.get('assigned_scout','?')}. "
                    f"Next: {record.get('next_action','?')}"
                ),
                next_action=record.get("next_action", ""),
            )
            record["artifact_registry_id"] = art.artifact_id
        except Exception:
            pass

    def _map_source_type(self, st: str) -> str:
        mapping = {
            "youtube_video":          "youtube_video",
            "youtube_channel":        "youtube_channel",
            "github_repo":            "github_repo",
            "trading_strategy":       "trading_strategy",
            "credit_repair_strategy": "credit_repair_strategy",
            "business_funding":       "business_funding",
            "grant":                  "grant",
            "affiliate_program":      "affiliate_program",
            "monetization_idea":      "monetization_idea",
        }
        return mapping.get(st, "other")

    def _try_supabase_write(self, record: dict) -> None:
        """Attempt Supabase write; mark supabase_unavailable if fails."""
        try:
            import os, urllib.request
            url  = os.getenv("SUPABASE_URL", "")
            key  = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY", "")
            if not url or not key:
                record["supabase_id"] = "supabase_unavailable"
                return
            payload = json.dumps({
                "created_at":        record["submitted_at"],
                "submitted_by":      record["submitted_by"],
                "source_type":       record["source_type"],
                "platform":          record["platform"],
                "url":               record.get("url", ""),
                "raw_message":       record.get("raw_message", "")[:500],
                "classification":    record["classification"],
                "assigned_scout":    record.get("assigned_scout", ""),
                "status":            record["status"],
                "priority":          record["priority"],
                "artifact_registry_id": record.get("artifact_registry_id", ""),
                "metadata":          {"intake_id": record["intake_id"]},
            }).encode()
            req = urllib.request.Request(
                f"{url}/rest/v1/nexus_source_intake",
                data=payload,
                headers={
                    "apikey":        key,
                    "Authorization": f"Bearer {key}",
                    "Content-Type":  "application/json",
                    "Prefer":        "return=representation",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                rows = json.loads(r.read())
                if rows and isinstance(rows, list):
                    record["supabase_id"] = rows[0].get("id", "")
        except Exception:
            record["supabase_id"] = "supabase_unavailable"

    def _create_claude_code_handoff_if_needed(self, record: dict) -> None:
        """Create a Claude Code handoff prompt file if the scout can't run directly."""
        source_type = record.get("source_type", "unknown")
        if source_type not in ("youtube_video", "youtube_channel", "github_repo"):
            return
        try:
            handoff_dir = ROOT / "docs" / "reports" / "handoffs"
            handoff_dir.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = handoff_dir / f"claude_code_handoff_{ts}.md"
            prompt = _claude_code_handoff_prompt(record)
            path.write_text(prompt)
            record["claude_code_handoff_path"] = str(path)
        except Exception:
            pass

    def _load_all(self) -> list[dict]:
        if not INTAKE_LOG.exists():
            return []
        records = []
        for line in INTAKE_LOG.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records

    def _update_md_summary(self) -> None:
        try:
            records = self._load_all()
            rows = ""
            for r in reversed(records[-15:]):
                name = r.get("url") or r.get("raw_message", "")[:40]
                rows += (
                    f"| {r.get('intake_id','?')[:12]} | {r.get('source_type','?')} "
                    f"| {name} | {r.get('status','?')} | {r.get('assigned_scout','?')} |\n"
                )
            INTAKE_MD.write_text(
                f"# Telegram Source Intake Queue\n"
                f"*{len(records)} total — updated {_now()}*\n\n"
                f"| ID | Type | Source | Status | Scout |\n"
                f"|---|---|---|---|---|\n"
                f"{rows}"
            )
        except Exception:
            pass


def _claude_code_handoff_prompt(record: dict) -> str:
    source_type = record.get("source_type", "unknown")
    url = record.get("url", "")
    intake_id = record.get("intake_id", "?")
    if source_type in ("youtube_video", "youtube_channel"):
        return f"""# Claude Code Handoff — YouTube Research
*Intake ID: {intake_id}*
*Created: {_now()}*

## Task
Research this YouTube {'video' if source_type == 'youtube_video' else 'channel'} for Nexus.

## Source
URL: {url}

## Required Outputs
1. Register in `lib/youtube_source_registry.py` (source_id, channel_name, video_title)
2. Run quality review via `lib/youtube_quality_reviewer.py`
3. Extract intelligence via `lib/youtube_intelligence_extractor.py`
4. Create 4 artifact files (content, monetization, nexus_improvement, compliance)
5. Create intelligence report MD
6. Register all artifacts in `lib/nexus_artifact_registry.py`
7. Update source registry status to 'active' or 'needs_review'

## Completion Contract
Do NOT mark complete until:
- source_registry.json updated with source_id
- At least 4 artifact files created in docs/reports/youtube/
- nexus_artifact_registry.jsonl updated

## Safety Rules
- Do NOT claim transcript collected unless transcript file exists
- Do NOT claim compliance_safe unless compliance_intelligence artifact is created
- If source is risky (compliance_safety < 4), mark needs_review, do NOT approve

## Write Summary For Hermes
After completing, write a summary to:
  docs/reports/handoffs/claude_code_handoff_{intake_id[:8]}_complete.md
"""
    elif source_type == "github_repo":
        return f"""# Claude Code Handoff — GitHub Repo Research
*Intake ID: {intake_id}*
*Created: {_now()}*

## Task
Evaluate this GitHub repo for Nexus system improvement.

## Source
URL: {url}

## Required Outputs
1. Evaluate repo relevance to Nexus (credit repair, funding, AI, content)
2. Apply shiny-object filter: does it improve an EXISTING Nexus process?
3. Create evaluation report: docs/reports/github_trends/github_repo_eval_{intake_id[:8]}.md
4. Register artifact in nexus_artifact_registry.jsonl

## Completion Contract
Do NOT recommend installation without:
- Evidence it improves an existing Nexus process
- Risk/complexity assessment
- What must be solved before installing

## Write Summary For Hermes
docs/reports/handoffs/claude_code_handoff_{intake_id[:8]}_complete.md
"""
    return f"""# Claude Code Handoff
*Intake ID: {intake_id}*
Source: {url or record.get('raw_message','?')[:100]}
Type: {source_type}
Created: {_now()}

Process this source and register all artifacts in nexus_artifact_registry.jsonl.
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Singleton ─────────────────────────────────────────────────────────────────
_intake = HermesTelegramSourceIntake()


def process_telegram_message(raw_message: str, submitted_by: str = "raymond") -> IntakeRecord:
    return _intake.process(raw_message, submitted_by)


def get_intake_summary() -> str:
    return _intake.intake_summary()


def get_recent_intakes(limit: int = 10) -> list[IntakeRecord]:
    return _intake.get_recent(limit)
