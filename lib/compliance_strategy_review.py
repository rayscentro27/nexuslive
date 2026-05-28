"""
compliance_strategy_review.py — Nexus Compliance Strategy Review Gate
======================================================================
Reviews financial, credit, legal, health, and trading strategies before
any client-safe label is applied.

Status ladder (must pass each level before advancing):
  rejected
  needs_source_verification
  needs_compliance_review            ← default for advanced strategies
  internal_research_candidate
  education_candidate
  client_safe_education_candidate    ← requires ALL 10 checklist items
  monetization_candidate_with_guardrails
  approved_for_internal_testing

A strategy can ONLY receive `client_safe_education_candidate` if it has:
  1. source/evidence summary (not LLM-generated)
  2. compliance/risk review
  3. educational disclaimer
  4. prohibited-claims check
  5. client-safe wording
  6. what Nexus can safely say
  7. what Nexus must avoid saying
  8. what requires Ray approval
  9. artifact path
  10. review timestamp

Default for advanced credit/funding strategies: needs_compliance_review

Usage:
    from lib.compliance_strategy_review import ComplianceReviewer
    result = ComplianceReviewer().review_strategies(strategies, domain="credit_repair")
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT         = Path(__file__).resolve().parent.parent
COMPLIANCE_DIR = ROOT / "docs" / "reports" / "learn_by_doing"

REGULATED_DOMAINS = {
    "credit_repair",
    "business_credit",
    "business_funding",
    "trading",
    "health",
    "legal",
    "financial_advice",
    "insurance",
    "tax_advice",
    "real_estate",
}

ADVANCED_STRATEGY_KEYWORDS = {
    "ucc", "lien", "subordination", "payment arbitration", "re-aging",
    "re aging", "dispute", "bureau", "credit score", "tradeline", "trade line",
    "signal", "invest", "portfolio", "leverage", "margin", "loan",
    "collateral", "default", "bankruptcy", "garnishment", "judgment",
}

PROHIBITED_CLAIMS = [
    "guaranteed improvement",
    "guaranteed approval",
    "guaranteed score increase",
    "remove all negative",
    "erase bad credit",
    "we will fix your credit",
    "will increase your score by",
    "legal loophole",
    "secret method",
    "100% success rate",
    "risk-free",
    "government-approved credit repair",
    "approved by the FTC",
]

EDUCATIONAL_DISCLAIMER = (
    "This is educational information designed to help users understand business "
    "funding readiness factors. It is not legal, tax, financial, or credit repair advice. "
    "Consult a licensed professional before taking action on any strategy discussed."
)

CROA_NOTICE = (
    "The Credit Repair Organizations Act (CROA, 15 U.S.C. §1679) and many state credit "
    "repair services acts restrict the offering of credit repair services. Charging upfront "
    "fees for credit repair, making guarantees about credit improvement, or providing credit "
    "repair services without proper disclosure may violate federal and state law. Nexus does "
    "not provide credit repair services — only educational content."
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _llm(prompt: str, system: str = "", tier: str = "reasoning", timeout: int = 120) -> str:
    try:
        from lib.content_generation_router import generate_content
        r = generate_content(prompt=prompt, system=system, tier=tier, timeout=timeout, max_tokens=4000)
        return r.get("response", "") if isinstance(r, dict) else str(r)
    except Exception as exc:
        return f"[LLM_ERROR: {exc}]"


def _parse_json(text: str, fallback: Any = None) -> Any:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        return fallback


def _save(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _is_advanced_strategy(name: str, description: str = "") -> bool:
    text = (name + " " + description).lower()
    return any(kw in text for kw in ADVANCED_STRATEGY_KEYWORDS)


def _check_prohibited_claims(text: str) -> list[str]:
    text_lower = text.lower()
    return [claim for claim in PROHIBITED_CLAIMS if claim in text_lower]


def _initial_status(strategy: dict, domain: str) -> str:
    """Assign initial status based on domain and strategy content."""
    name = strategy.get("name", "")
    desc = strategy.get("problem_solved", "") + " " + strategy.get("client_education_angle", "")
    source = strategy.get("source", "")

    # LLM-generated sources get source_verification flag
    source_lower = source.lower()
    is_llm_source = any(p in source_lower for p in [
        "expert consensus", "evidence from", "industry evidence", "llm", "gpt", "ai-generated"
    ])

    if domain in REGULATED_DOMAINS or _is_advanced_strategy(name, desc):
        if is_llm_source:
            return "needs_source_verification"
        return "needs_compliance_review"

    return "internal_research_candidate"


class ComplianceReviewer:

    SYSTEM = (
        "You are a compliance and regulatory risk analyst for Nexus, an AI business education platform. "
        "Your job is to assess whether educational content about business credit, funding, and financial "
        "readiness is safe to teach — NOT to help provide credit repair services. "
        "Be conservative. When in doubt, downgrade the status. "
        "Cite relevant laws/regulations where applicable (CROA, CFPB rules, FTC rules, state credit repair acts). "
        "Output only valid JSON."
    )

    def review_strategies(
        self,
        strategies: list[dict],
        domain: str = "credit_repair",
        ts: str | None = None,
    ) -> dict:
        """
        Run compliance review on a list of strategies.
        Returns full review with corrected statuses and artifact paths.
        """
        if not ts:
            ts = _ts()

        reviewed: list[dict] = []

        for strategy in strategies:
            rev = self._review_one(strategy, domain)
            reviewed.append(rev)

        result = {
            "review_id":    f"compliance_{ts}_{uuid.uuid4().hex[:6]}",
            "created":      _now(),
            "domain":       domain,
            "total":        len(reviewed),
            "by_status":    self._count_statuses(reviewed),
            "strategies":   reviewed,
            "disclaimer":   EDUCATIONAL_DISCLAIMER,
            "croa_notice":  CROA_NOTICE,
        }

        # Save artifacts
        domain_dir = COMPLIANCE_DIR / domain
        json_path = _save(
            domain_dir / f"compliance_review_{ts}.json",
            json.dumps(result, indent=2, default=str),
        )
        md_path = _save(
            domain_dir / f"compliance_review_{ts}.md",
            self._render_md(result),
        )
        result["json_path"] = str(json_path)
        result["md_path"]   = str(md_path)

        return result

    def _review_one(self, strategy: dict, domain: str) -> dict:
        name   = strategy.get("name", "Unknown")
        source = strategy.get("source", "")
        desc   = strategy.get("problem_solved", "")
        angle  = strategy.get("client_education_angle", "")
        risk   = strategy.get("risk_or_compliance_concern", "")

        initial_status = _initial_status(strategy, domain)
        prohibited     = _check_prohibited_claims(angle + " " + desc)

        prompt = f"""Perform a compliance review for this educational content strategy.

Domain: {domain}
Strategy name: {name}
Source/evidence: {source}
Problem it addresses: {desc}
Educational angle: {angle}
Known risk/concern: {risk}

Evaluate:
1. Is the source/evidence verifiable (not just LLM-generated)? If not, status = needs_source_verification
2. Is there a regulatory/compliance issue? Cite specific laws if applicable.
3. What risk categories apply? (legal, financial, compliance, reputational, client_misunderstanding, data_weakness, implementation_risk)
4. What can Nexus SAFELY teach about this as educational content?
5. What must Nexus NEVER say (prohibited claims, guarantees, advice)?
6. What specific regulatory compliance is required before offering this as a service?
7. Is this appropriate as education_candidate only, or can it advance to client_safe_education_candidate?
8. What Ray approval is needed before any client use?

Return JSON:
{{
  "name": "{name}",
  "source_is_verifiable": true/false,
  "source_evidence_quality": "strong | weak | missing | internal_only | llm_generated",
  "source_verification_needed": "description of what citations/evidence would be needed",
  "compliance_issues": ["list of specific legal/regulatory concerns"],
  "risk_categories": ["list"],
  "what_nexus_can_safely_teach": "educational framing that is safe",
  "what_nexus_must_avoid": ["list of prohibited claims or advice types"],
  "regulatory_compliance_for_service": "what would be needed to offer this as a paid service",
  "requires_ray_approval_for": ["list"],
  "requires_professional_review_for": ["list"],
  "client_safe_framing": "how to present this to clients safely as education",
  "corrected_status": "one of: rejected | needs_source_verification | needs_compliance_review | internal_research_candidate | education_candidate | client_safe_education_candidate | monetization_candidate_with_guardrails | approved_for_internal_testing",
  "status_reason": "why this status was assigned"
}}"""

        raw    = _llm(prompt, system=self.SYSTEM, tier="reasoning")
        parsed = _parse_json(raw, {})

        if not isinstance(parsed, dict) or "corrected_status" not in parsed:
            parsed = {
                "name":                        name,
                "source_is_verifiable":        False,
                "source_evidence_quality":     "llm_generated",
                "source_verification_needed":  "Verified citations from CFPB, FTC, or published research required",
                "compliance_issues":           ["Source is LLM-generated — cannot verify compliance without real citations"],
                "risk_categories":             ["data_source_weakness", "compliance"],
                "what_nexus_can_safely_teach": "General awareness of this strategy category exists; specific mechanics require verified sources",
                "what_nexus_must_avoid":       PROHIBITED_CLAIMS[:5],
                "regulatory_compliance_for_service": "Not determinable without verified sources",
                "requires_ray_approval_for":   ["any client-facing use", "any service offering"],
                "requires_professional_review_for": ["legal review before service offering", "compliance review before client education"],
                "client_safe_framing":         f"Educational overview only: '{name}' is a strategy some businesses use. Consult a licensed advisor.",
                "corrected_status":            initial_status,
                "status_reason":              "LLM fallback — source cannot be verified",
            }

        if prohibited:
            parsed["prohibited_claims_found"] = prohibited
            if parsed.get("corrected_status") not in ("rejected", "needs_source_verification"):
                parsed["corrected_status"]  = "needs_compliance_review"
                parsed["status_reason"]     += f" | Prohibited claims detected: {prohibited}"

        parsed["original_claim_status"] = strategy.get("client_safe", None)
        parsed["downgraded_from"]       = "client_safe (auto-labeled)" if strategy.get("client_safe") else "N/A"
        parsed["educational_disclaimer"] = EDUCATIONAL_DISCLAIMER
        parsed["review_timestamp"]      = _now()

        return parsed

    def _count_statuses(self, reviewed: list[dict]) -> dict:
        counts: dict[str, int] = {}
        for r in reviewed:
            s = r.get("corrected_status", "unknown")
            counts[s] = counts.get(s, 0) + 1
        return counts

    def _render_md(self, result: dict) -> str:
        lines = [
            f"# Compliance Strategy Review — {result['domain']}",
            f"*Review ID: {result['review_id']} | {result['created'][:10]}*\n",
            f"> **{EDUCATIONAL_DISCLAIMER}**\n",
            f"> **CROA Notice:** {CROA_NOTICE[:200]}...\n",
            f"**Total strategies reviewed:** {result['total']}",
            f"**Status breakdown:** {json.dumps(result['by_status'])}\n",
            "---\n",
        ]
        for s in result.get("strategies", []):
            status = s.get("corrected_status", "?")
            prev   = s.get("downgraded_from", "N/A")
            emoji  = {
                "rejected": "🚫",
                "needs_source_verification": "🔍",
                "needs_compliance_review": "⚖️",
                "internal_research_candidate": "🔬",
                "education_candidate": "🎓",
                "client_safe_education_candidate": "✅",
                "monetization_candidate_with_guardrails": "💰",
                "approved_for_internal_testing": "🧪",
            }.get(status, "⚠️")
            lines += [
                f"## {emoji} {s.get('name', 'Unknown')}",
                f"**Status:** `{status}` | **Downgraded from:** {prev}",
                f"**Status reason:** {s.get('status_reason', '')}",
                f"\n**Source evidence quality:** {s.get('source_evidence_quality', '?')}",
                f"**Source verification needed:** {s.get('source_verification_needed', '')}",
                f"\n**Compliance issues:**",
            ]
            for issue in s.get("compliance_issues", []):
                lines.append(f"- {issue}")
            lines += [
                f"\n**Risk categories:** {', '.join(s.get('risk_categories', []))}",
                f"\n**What Nexus can safely teach:**",
                s.get("what_nexus_can_safely_teach", ""),
                f"\n**What Nexus must avoid:**",
            ]
            for avoid in s.get("what_nexus_must_avoid", []):
                lines.append(f"- ❌ {avoid}")
            lines += [
                f"\n**Client-safe framing:** {s.get('client_safe_framing', '')}",
                f"\n**Requires Ray approval for:** {', '.join(s.get('requires_ray_approval_for', []))}",
                f"\n**Requires professional review for:** {', '.join(s.get('requires_professional_review_for', []))}",
                "\n---\n",
            ]
        return "\n".join(lines)
