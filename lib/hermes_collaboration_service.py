"""
hermes_collaboration_service.py — Hermes Communication / Collaboration API
===========================================================================
Supports Ray's natural-language commands to Hermes about ongoing research,
risky opportunities, monetization, mistakes, and credit/funding strategies.

Every command:
  1. Loads the latest relevant artifact (or says artifact_missing)
  2. Answers from artifacts first — never fabricates
  3. Saves Ray's feedback if provided
  4. Updates research/improvement queue when appropriate

Usage:
    from lib.hermes_collaboration_service import HermesCollaboration
    hermes = HermesCollaboration()
    response = hermes.handle("what can make money in 30 days?")
    print(response["answer"])
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT         = Path(__file__).resolve().parent.parent
REPORTS_DIR  = ROOT / "docs" / "reports"
FEEDBACK_DIR = REPORTS_DIR / "ceo_review"

# Evidence gating — NO ARTIFACT = NO CLAIM
try:
    from lib.hermes_evidence_mode import (
        HermesEvidenceMode as _EvMode,
        is_fake_trading_claim as _is_fake_trading,
        has_theatrical_language as _has_theatrical,
        verified_status_block as _verified_status_block,
    )
    _ev = _EvMode()
    _EVIDENCE_GATING = True
except ImportError:
    _ev = None  # type: ignore[assignment]
    _EVIDENCE_GATING = False
    def _is_fake_trading(t: str) -> bool: return False  # type: ignore[misc]
    def _has_theatrical(t: str) -> bool: return False  # type: ignore[misc]
    def _verified_status_block() -> str: return ""  # type: ignore[misc]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _latest(glob_pattern: str, base: Path = REPORTS_DIR) -> Path | None:
    """Find the most recently modified file matching a glob pattern."""
    files = list(base.glob(glob_pattern))
    if not files:
        return None
    return max(files, key=lambda f: f.stat().st_mtime)


def _read_artifact(path: Path | None, max_chars: int = 3000) -> str:
    if not path or not path.exists():
        return "artifact_missing"
    try:
        text = path.read_text()
        return text[:max_chars] + ("\n...[truncated]" if len(text) > max_chars else "")
    except Exception as exc:
        return f"artifact_read_error: {exc}"


def _llm(prompt: str, system: str = "", tier: str = "lightweight", timeout: int = 60) -> str:
    try:
        from lib.content_generation_router import generate_content
        r = generate_content(prompt=prompt, system=system, tier=tier, timeout=timeout, max_tokens=1200)
        return r.get("response", "") if isinstance(r, dict) else str(r)
    except Exception as exc:
        return f"[LLM unavailable: {exc}]"


def _save_feedback(command: str, answer: str, feedback: str = "") -> Path:
    ts   = _ts()
    path = FEEDBACK_DIR / f"ray_feedback_{ts}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"# Ray Feedback Log\n*{_now()}*\n\n**Command:** {command}\n\n**Hermes answer:** {answer[:500]}\n\n**Ray feedback:** {feedback or '(none provided)'}\n"
    path.write_text(content)
    return path


COMMAND_MAP = {
    # CEO Packet
    "show me the latest ceo":             "ceo_packet",
    "summarize what nexus produced":      "ceo_packet",
    "what finished products":             "ceo_packet",
    "what should i critique":             "ceo_critique",
    # Risk
    "what made this opportunity risky":   "risky_opportunity",
    "what can we safely take":            "risky_opportunity",
    "what risky ideas should we avoid":   "risky_log",
    "risky idea.*reframe":                "risky_opportunity",
    # Learning
    "what did you learn from":            "ceo_packet",
    "what did you learn about credit":    "credit_repair",
    "what.*learn.*credit":                "credit_repair",
    "what mistake are you repeating":     "mistake_memory",
    "what did you downgrade":             "compliance_review",
    "what failed":                        "ceo_critique",
    # Monetization
    "make money in.*30":                  "30_day_plan",
    "fastest.*monetization":              "monetization_report",
    "which content should we create":     "content_pipeline",
    "what offer should we test":          "monetization_report",
    # Credit/Funding
    "find a new credit repair":           "credit_repair_discovery",
    "validate.*funding":                  "compliance_review",
    "what can nexus safely teach":        "compliance_review",
    "what requires compliance":           "compliance_review",
    # GitHub/System
    "run weekly github":                  "github_trends",
    "github repo.*improve nexus":         "github_recommendations",
    "shiny object":                       "github_filter",
    # Research
    "continue research":                  "continued_research",
    "build the next research queue":      "continued_research",
    "what should you research overnight": "continued_research",
    # ── Strategic conversation (Telegram inbound) ──────────────────────────────
    "catch me up":                        "ceo_packet",
    "where are we":                       "ceo_packet",
    "are we on track":                    "ceo_packet",
    "what.*nexus.*doing":                 "ceo_packet",
    "what happened.*since":               "ceo_packet",
    "what did nexus produce":             "ceo_packet",
    "show.*handoff":                      "handoffs",
    "pending.*action":                    "handoffs",
    "what.*need.*approv":                 "handoffs",
    "what.*waiting.*on me":               "handoffs",
    "what.*approv.*on":                   "handoffs",
    "show.*decision.*log":                "decision_log",
    "what.*hermes.*decid":                "decision_log",
    "what.*decid.*own":                   "decision_log",
    "oanda.*demo":                        "demo_exec",
    "demo.*order":                        "demo_exec",
    "last.*trade":                        "demo_exec",
    "beehiiv.*alternative":               "premium_blockers",
    "premium.*blocker":                   "premium_blockers",
    "replace.*beehiiv":                   "premium_blockers",
    "record lesson":                      "ray_feedback",
    "remember this":                      "ray_feedback",
    "save.*feedback":                     "ray_feedback",
    "show.*recent.*notification":         "notifications",
    "what.*telegram.*sent":               "notifications",
}

ARTIFACT_RESOLVERS = {
    "ceo_packet":           lambda: _latest("ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md", REPORTS_DIR),
    "ceo_critique":         lambda: _latest("ceo_review/NEXUS_CEO_CRITIQUE_*.md", REPORTS_DIR),
    "risky_opportunity":    lambda: _latest("risky_opportunities/risky_opportunity_analysis_*.md", REPORTS_DIR),
    "risky_log":            lambda: REPORTS_DIR / "risky_opportunities" / "risk_learning_log.json",
    "mistake_memory":       lambda: ROOT / "docs" / "reports" / "hermes_mistake_memory.json",
    "compliance_review":    lambda: _latest("learn_by_doing/credit_repair/compliance_review_*.md", REPORTS_DIR),
    "30_day_plan":          lambda: _latest("monetization/30_day_revenue_plan_*.md", REPORTS_DIR),
    "monetization_report":  lambda: _latest("monetization/monetization_operating_report_*.md", REPORTS_DIR),
    "content_pipeline":     lambda: _latest("ceo_review/NEXUS_MONETIZATION_CEO_PACKET_*.md", REPORTS_DIR),
    "credit_repair_discovery": lambda: _latest("learn_by_doing/credit_repair/new_strategy_discovery_*.md", REPORTS_DIR),
    "github_trends":        lambda: _latest("github_trends/github_trending_research_*.md", REPORTS_DIR),
    "github_recommendations": lambda: _latest("github_trends/github_trending_recommendations_*.md", REPORTS_DIR),
    "github_filter":        lambda: _latest("github_trends/github_trend_ceo_filter_*.md", REPORTS_DIR),
    "continued_research":   lambda: _latest("ceo_review/NEXUS_CONTINUED_RESEARCH_PACKET_*.md", REPORTS_DIR),
    # Strategic conversation routes
    "handoffs":             lambda: _latest("hermes_handoffs/handoff_*.md", REPORTS_DIR),
    "decision_log":         lambda: ROOT / "docs" / "reports" / "hermes_decisions" / "hermes_decision_log.jsonl",
    "demo_exec":            lambda: _latest("../integrations/oanda_demo/reports/demo_execution_packet_*.json", REPORTS_DIR),
    "premium_blockers":     lambda: _latest("premium_blockers/blocker_resolution_*.md", REPORTS_DIR),
    "ray_feedback":         lambda: _latest("ray_feedback/ray_feedback_*.json", REPORTS_DIR),
    "notifications":        lambda: ROOT / "docs" / "reports" / "hermes_proactive_notifications.jsonl",
}


class HermesCollaboration:

    SYSTEM = (
        "You are Hermes, the Nexus AI operator. "
        "You answer questions by reading from actual saved artifacts. "
        "If an artifact is missing, say so — never fabricate. "
        "CRITICAL RULES — violating these is a hard failure:\n"
        "  • NEVER use theatrical or roleplay phrases (taps tablet, sharp inhale, "
        "tracking live, already pulling up, leans forward, grins, nods, etc).\n"
        "  • NEVER claim an operation completed without citing the artifact path or ID.\n"
        "  • NEVER report trade execution (trade placed, scalp active, order confirmed, "
        "pips gained, entering long/short) without a verified broker order ID.\n"
        "  • If evidence is missing say exactly: 'I do not have verified evidence for that yet.'\n"
        "Keep answers concise (under 300 words unless required). "
        "Always end with what the next artifact or action should be."
    )

    def handle(self, command: str, feedback: str = "") -> dict:
        """
        Handle a natural-language command from Ray.
        Returns dict with: answer, artifact_path, artifact_status, feedback_path.
        """
        # ── Evidence gate: block fake trading execution claims ─────────────────
        if _is_fake_trading(command):
            return {
                "command":         command,
                "artifact_key":    "blocked_fake_trading",
                "artifact_path":   "none",
                "artifact_status": "blocked",
                "answer": (
                    "I cannot report trade execution claims without a verified broker artifact. "
                    "No order was placed or confirmed without a real OANDA demo order ID.\n\n"
                    "To check real demo status: 'show me oanda demo status'"
                ),
                "feedback_path":   None,
                "timestamp":       _now(),
            }

        command_lower = command.lower().strip()
        artifact_key  = self._route(command_lower)
        artifact_path = ARTIFACT_RESOLVERS[artifact_key]() if artifact_key in ARTIFACT_RESOLVERS else None
        artifact_text = _read_artifact(artifact_path)

        if artifact_text == "artifact_missing":
            # Use evidence mode's formatted response when available
            if _EVIDENCE_GATING and _ev is not None:
                ev_result = _ev.require_evidence_for_claim(
                    self._artifact_key_to_claim_type(artifact_key), command
                )
                answer = _ev.format_missing_evidence_response(ev_result)
            else:
                answer = (
                    f"I do not have verified evidence for that yet.\n\n"
                    f"**Missing:** {artifact_key.replace('_', ' ')} artifact\n\n"
                    f"**Next safe action:** Run the relevant operating cycle:\n"
                    f"`python scripts/run_nexus_monetization_operating_cycle.py --mode validation --cost free "
                    f"--focus {self._suggest_focus(artifact_key)} --require-artifacts true`"
                )
        else:
            answer = self._synthesize(command, artifact_text)
            # For nexus status queries, attach the verified status block
            if artifact_key in ("ceo_packet",) and _EVIDENCE_GATING:
                try:
                    status_block = _verified_status_block()
                    if status_block:
                        answer = answer + "\n\n---\n" + status_block
                except Exception:
                    pass
            # Post-synthesis evidence attachment
            if _EVIDENCE_GATING and _ev is not None:
                ev_result = _ev.find_evidence(command)
                answer = _ev.attach_evidence_to_response(answer, ev_result)

        feedback_path = None
        if feedback:
            feedback_path = _save_feedback(command, answer, feedback)

        return {
            "command":        command,
            "artifact_key":   artifact_key or "none",
            "artifact_path":  str(artifact_path) if artifact_path else "none",
            "artifact_status": "present" if artifact_text != "artifact_missing" else "artifact_missing",
            "answer":         answer,
            "feedback_path":  str(feedback_path) if feedback_path else None,
            "timestamp":      _now(),
        }

    def _route(self, command: str) -> str | None:
        for pattern, key in COMMAND_MAP.items():
            if re.search(pattern, command):
                return key
        # Fallback: try to match intent
        if any(w in command for w in ["ceo", "packet", "review"]):
            return "ceo_packet"
        if any(w in command for w in ["risky", "risk", "dangerous"]):
            return "risky_opportunity"
        if any(w in command for w in ["mistake", "wrong", "error", "fail"]):
            return "mistake_memory"
        if any(w in command for w in ["money", "revenue", "monetize"]) or " earn" in command:
            return "30_day_plan"
        if any(w in command for w in ["credit", "funding", "compliance"]):
            return "compliance_review"
        if any(w in command for w in ["decide", "decided", "decision", "approv"]):
            return "decision_log"
        if any(w in command for w in ["github", "repo", "tool"]):
            return "github_recommendations"
        if any(w in command for w in ["research", "next", "queue"]):
            return "continued_research"
        if any(w in command for w in ["handoff", "pending", "approve", "waiting"]):
            return "handoffs"
        if any(w in command for w in ["oanda", "demo", "trade", "broker"]):
            return "demo_exec"
        if any(w in command for w in ["blocker", "beehiiv", "alternative"]):
            return "premium_blockers"
        if any(w in command for w in ["notification", "telegram sent", "notif"]):
            return "notifications"
        return "ceo_packet"

    def _synthesize(self, command: str, artifact_text: str) -> str:
        if "[LLM" in artifact_text or len(artifact_text) < 10:
            return f"artifact_read_error — {artifact_text[:200]}"
        prompt = f"""Ray asked: "{command}"

Here is the relevant Nexus artifact:
---
{artifact_text[:2000]}
---

Answer Ray's question directly from the artifact. Be specific, cite the artifact. Under 250 words.
If the artifact doesn't fully answer the question, say what's missing and what artifact would."""
        return _llm(prompt, system=self.SYSTEM, tier="lightweight")

    def _artifact_key_to_claim_type(self, artifact_key: str) -> str:
        mapping = {
            "ceo_packet":       "ceo_packet",
            "handoffs":         "approval_queue",
            "decision_log":     "decisions_made",
            "demo_exec":        "oanda_demo",
            "premium_blockers": "premium_blocker",
            "notifications":    "notifications",
            "30_day_plan":      "monetization_packet",
            "compliance_review": "compliance_review",
            "github_trends":    "github_trends",
            "continued_research": "research_completed",
        }
        return mapping.get(artifact_key, "research_completed")

    def _suggest_focus(self, artifact_key: str) -> str:
        focus_map = {
            "compliance_review":      "credit_repair",
            "30_day_plan":            "monetization",
            "monetization_report":    "monetization",
            "github_trends":          "system_improvement",
            "github_recommendations": "system_improvement",
            "continued_research":     "monetization,learning,system_improvement,credit_repair",
            "risky_opportunity":      "learning",
            "handoffs":               "monetization,learning,system_improvement,credit_repair",
            "demo_exec":              "monetization",
            "premium_blockers":       "system_improvement",
        }
        return focus_map.get(artifact_key, "monetization,learning,system_improvement,credit_repair")

    def list_available_artifacts(self) -> dict:
        """Return status of all known artifact types."""
        status: dict[str, str] = {}
        for key, resolver in ARTIFACT_RESOLVERS.items():
            path = resolver()
            status[key] = str(path) if path and path.exists() else "artifact_missing"
        return status
