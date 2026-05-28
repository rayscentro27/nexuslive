"""
Hermes Evidence Mode
====================
Hermes may not claim operational facts without verified artifacts.
NO ARTIFACT = NO CLAIM.

Every blocked claim type requires at least one of:
  Supabase row ID | workflow_output ID | artifact file path |
  JSON/Markdown report | broker order ID | decision log entry |
  approval queue item | YouTube source record | transcript artifact
"""
from __future__ import annotations

import glob
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "docs" / "reports"

# ── Theatrical/roleplay phrases to block ──────────────────────────────────────
THEATRICAL_PHRASES: list[str] = [
    "taps tablet", "sharp inhale", "slides sticky note", "holding queue position",
    "hammering liquidity scans", "quietly", "points to", "already pulling up",
    "tracking live", "leans forward", "pulls up the data", "scanning now",
    "typing rapidly", "checking feeds", "grins", "nods", "sighs", "chuckles",
    "whispers", "mutters", "steeples fingers", "clears throat",
]

# ── Operational verbs that require evidence ───────────────────────────────────
EVIDENCE_REQUIRED_VERBS: list[str] = [
    "processed", "researched", "reviewed", "summarized", "analyzed",
    "approved", "executed", "completed", "pushed", "traded", "queued",
    "decided", "sent", "delivered", "backtested", "extracted",
    "rejected", "ready",
]

# ── Fake trading claim phrases ────────────────────────────────────────────────
BLOCKED_TRADING_PHRASES: list[str] = [
    "executing scalp", "scalp active", "trade placed", "target hit",
    "stop moved", "tracking live", "order confirmed", "pushing to live instance",
    "live instance updated", "scalp active", "entering long", "entering short",
    "position open", "filled at", "pips gained", "pips lost",
]

# ── Claim type → evidence search patterns ────────────────────────────────────
CLAIM_EVIDENCE_MAP: dict[str, list[str]] = {
    "approval_queue":       ["hermes_handoffs/handoff_*.json", "hermes_handoffs/handoff_*.md"],
    "decisions_made":       ["hermes_decisions/hermes_decision_log.jsonl"],
    "research_completed":   ["ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md",
                             "ceo_review/NEXUS_CONTINUED_RESEARCH_PACKET_*.md"],
    "youtube_processed":    ["youtube/source_registry.json",
                             "youtube/youtube_intelligence_report_*.md",
                             "youtube/youtube_source_reconciliation_*.md"],
    "youtube_transcript":   ["youtube/source_registry.json"],
    "trading_backtest":     ["../integrations/vibe_trading/results/*.json",
                             "../integrations/vibe_trading/reports/*.md"],
    "oanda_demo":           ["../integrations/oanda_demo/reports/demo_execution_packet_*.json",
                             "../integrations/oanda_demo/reports/demo_orders_*.jsonl"],
    "premium_blocker":      ["blockers/blocker_resolution_beehiiv_*.md",
                             "blockers/blocker_resolution_*.md"],
    "github_trends":        ["github_trends/github_trending_recommendations_*.md"],
    "content_generated":    ["content/approval_packets/*.json",
                             "content/youtube_scripts/*.md",
                             "content/newsletters/*.md"],
    "ceo_packet":           ["ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md"],
    "monetization_packet":  ["monetization/30_day_revenue_plan_*.md"],
    "compliance_review":    ["learn_by_doing/credit_repair/compliance_review_*.md"],
    "notifications":        ["hermes_proactive_notifications.jsonl"],
    "provider_status":      ["hermes_decisions/hermes_decision_log.jsonl"],
    "strategy_validation":  ["learn_by_doing/credit_repair/new_strategy_discovery_*.md"],
}

# ── Beehiiv intent normalization ──────────────────────────────────────────────
BEEHIIV_ALIASES: list[str] = [
    "beehiiv", "beehive", "bee hive", "bee-hive", "behive", "behiiv",
    "newsletter alternative", "email platform alternative", "newsletter platform",
    "newsletter tool alternative",
]


class EvidenceResult:
    def __init__(self, found: bool, paths: list[str], claim_type: str, query: str):
        self.found = found
        self.paths = paths
        self.claim_type = claim_type
        self.query = query

    def to_dict(self) -> dict:
        return {
            "found": self.found,
            "claim_type": self.claim_type,
            "query": self.query,
            "artifact_paths": self.paths,
            "checked_at": datetime.utcnow().isoformat() + "Z",
        }


class HermesEvidenceMode:

    # ── Public API ─────────────────────────────────────────────────────────────

    def require_evidence_for_claim(self, claim_type: str, query_context: str) -> EvidenceResult:
        patterns = CLAIM_EVIDENCE_MAP.get(claim_type, [])
        paths = self._search_patterns(patterns)
        return EvidenceResult(bool(paths), paths, claim_type, query_context)

    def find_evidence(self, query_context: str) -> EvidenceResult:
        query_lower = query_context.lower()
        claim_type = self._detect_claim_type(query_lower)
        return self.require_evidence_for_claim(claim_type, query_context)

    def format_evidence_response(self, evidence: EvidenceResult) -> str:
        if not evidence.found:
            return self.format_missing_evidence_response(evidence)
        path_lines = "\n".join(f"  • {p}" for p in evidence.paths[:5])
        return (
            f"**Evidence found** ({evidence.claim_type}):\n"
            f"{path_lines}\n\n"
            f"*(Showing up to 5 most recent artifacts)*"
        )

    def format_missing_evidence_response(self, evidence: EvidenceResult | str) -> str:
        if isinstance(evidence, str):
            query = evidence
            claim_type = self._detect_claim_type(query.lower())
        else:
            query = evidence.query
            claim_type = evidence.claim_type
        action = self._suggest_next_action(claim_type)
        return (
            f"I do not have verified evidence for that yet.\n\n"
            f"**Missing:** {claim_type.replace('_', ' ')} artifact\n\n"
            f"**Next safe action:** {action}"
        )

    def block_unverified_operational_claim(self, response_text: str) -> tuple[bool, list[str]]:
        blocked_phrases = []
        lower = response_text.lower()
        for phrase in THEATRICAL_PHRASES:
            if phrase in lower:
                blocked_phrases.append(f"theatrical: '{phrase}'")
        for phrase in BLOCKED_TRADING_PHRASES:
            if phrase in lower:
                blocked_phrases.append(f"fake_trade: '{phrase}'")
        return bool(blocked_phrases), blocked_phrases

    def extract_claims_from_response(self, response_text: str) -> list[dict[str, str]]:
        claims = []
        lower = response_text.lower()
        for verb in EVIDENCE_REQUIRED_VERBS:
            pattern = rf"\b{verb}\b"
            matches = re.findall(pattern, lower)
            if matches:
                claims.append({"verb": verb, "count": len(matches), "requires_evidence": True})
        return claims

    def attach_evidence_to_response(self, response_text: str, evidence: EvidenceResult) -> str:
        if not evidence.found:
            return (
                response_text
                + f"\n\n---\n⚠️ **Evidence check:** No verified artifacts found "
                f"for `{evidence.claim_type}`. Run the relevant cycle to create them."
            )
        path_line = " | ".join(Path(p).name for p in evidence.paths[:3])
        return (
            response_text
            + f"\n\n---\n✅ **Evidence:** `{path_line}`"
        )

    def normalize_beehiiv_intent(self, text: str) -> bool:
        lower = text.lower()
        return any(alias in lower for alias in BEEHIIV_ALIASES)

    def is_fake_trading_claim(self, text: str) -> bool:
        lower = text.lower()
        return any(phrase in lower for phrase in BLOCKED_TRADING_PHRASES)

    def has_theatrical_language(self, text: str) -> bool:
        lower = text.lower()
        return any(phrase in lower for phrase in THEATRICAL_PHRASES)

    def verified_status_block(self) -> str:
        """Build a full NEXUS VERIFIED STATUS block from available artifacts."""
        sections: list[str] = ["## NEXUS VERIFIED STATUS\n"]
        missing: list[str] = []

        checks = [
            ("CEO packet",          "ceo_packet"),
            ("Decision log",        "decisions_made"),
            ("Pending approvals",   "approval_queue"),
            ("Monetization report", "monetization_packet"),
            ("GitHub trends",       "github_trends"),
            ("YouTube sources",     "youtube_processed"),
            ("Content generated",   "content_generated"),
            ("Notifications",       "notifications"),
        ]
        for label, claim_type in checks:
            ev = self.require_evidence_for_claim(claim_type, label)
            if ev.found:
                latest = Path(ev.paths[-1]).name
                sections.append(f"- **{label}:** `{latest}`")
            else:
                sections.append(f"- **{label}:** ⚠️ no artifact")
                missing.append(label)

        if missing:
            sections.append(f"\n**Missing evidence:** {', '.join(missing)}")
            sections.append(
                "\n**Recommended next action:** "
                "`python scripts/run_nexus_monetization_operating_cycle.py "
                "--mode validation --cost free --require-artifacts true`"
            )
        return "\n".join(sections)

    # ── Internals ──────────────────────────────────────────────────────────────

    def _search_patterns(self, patterns: list[str]) -> list[str]:
        found = []
        for pattern in patterns:
            full = str(REPORTS / pattern)
            matches = sorted(glob.glob(full))
            found.extend(matches[-3:])  # latest 3 per pattern
        return found

    def _detect_claim_type(self, query_lower: str) -> str:
        mapping = [
            (["approval", "approve", "handoff", "waiting on me"],       "approval_queue"),
            (["decided", "decision", "hermes decide"],                   "decisions_made"),
            (["youtube", "channel", "video", "transcript"],              "youtube_processed"),
            (["backtest", "vibe", "paper trade"],                        "trading_backtest"),
            (["oanda", "demo order", "demo trade"],                      "oanda_demo"),
            (["beehiiv", "beehive", "newsletter", "premium blocker"],    "premium_blocker"),
            (["github", "trend", "repo"],                                "github_trends"),
            (["content", "script", "hook", "newsletter"],                "content_generated"),
            (["ceo", "packet", "catch me up", "where are we"],           "ceo_packet"),
            (["monetiz", "revenue", "30 day"],                           "monetization_packet"),
            (["compliance", "credit repair", "strategy"],                "compliance_review"),
            (["notification", "telegram sent"],                          "notifications"),
            (["scalp", "trade", "position", "order"],                    "trading_backtest"),
        ]
        for keywords, claim_type in mapping:
            if any(kw in query_lower for kw in keywords):
                return claim_type
        return "research_completed"

    def _suggest_next_action(self, claim_type: str) -> str:
        actions = {
            "approval_queue":
                "Run the operating cycle to generate new handoffs, or check "
                "`docs/reports/hermes_handoffs/` manually.",
            "decisions_made":
                "Decision log is created at `docs/reports/hermes_decisions/hermes_decision_log.jsonl` "
                "when Hermes classifies actions.",
            "youtube_processed":
                "Run `python scripts/run_youtube_source_reconciliation.py` to build the source registry.",
            "trading_backtest":
                "Run `python integrations/vibe_trading/backtest.py` (paper mode only).",
            "oanda_demo":
                "Run `python scripts/test_oanda_demo_execution_loop.py --dry-run` "
                "(requires OANDA_DEMO_ENABLED=true — Ray approval).",
            "premium_blocker":
                "Run `python scripts/run_nexus_monetization_operating_cycle.py "
                "--mode validation --resolve-premium-blockers`.",
            "github_trends":
                "Run `python scripts/run_weekly_github_trend_research.py`.",
            "content_generated":
                "Run `python scripts/run_content_pipeline.py --topic '...' --platforms youtube newsletter`.",
            "ceo_packet":
                "Run `python scripts/run_nexus_monetization_operating_cycle.py "
                "--mode validation --cost free --require-artifacts true`.",
            "monetization_packet":
                "Run `python scripts/run_nexus_monetization_operating_cycle.py "
                "--mode validation --cost free --focus monetization`.",
            "compliance_review":
                "Run `python scripts/run_nexus_learn_by_doing_cycle.py --domain credit_repair`.",
        }
        return actions.get(claim_type, "Run the operating cycle: "
                           "`python scripts/run_nexus_monetization_operating_cycle.py "
                           "--mode validation --cost free --require-artifacts true`")


# ── Singleton ──────────────────────────────────────────────────────────────────
_evidence = HermesEvidenceMode()


def find_evidence(query: str) -> EvidenceResult:
    return _evidence.find_evidence(query)


def require_evidence(claim_type: str, context: str = "") -> EvidenceResult:
    return _evidence.require_evidence_for_claim(claim_type, context)


def verified_status_block() -> str:
    return _evidence.verified_status_block()


def is_beehiiv_query(text: str) -> bool:
    return _evidence.normalize_beehiiv_intent(text)


def is_fake_trading_claim(text: str) -> bool:
    return _evidence.is_fake_trading_claim(text)


def has_theatrical_language(text: str) -> bool:
    return _evidence.has_theatrical_language(text)


def format_missing(query: str) -> str:
    return _evidence.format_missing_evidence_response(query)
