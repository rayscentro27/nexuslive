"""
ceo_auto_router.py — CEO auto-routing engine for Nexus AI.

Classifies an incoming task payload and recommends which AI employee role
should handle it. Activated ONLY when payload contains:
    { "use_ceo_auto_routing": true }

All other jobs are completely unaffected.

Public API:
    classify_task(payload)               → dict  (JSON classification)
    build_ceo_routing_prompt(payload)    → str   (LLM prompt for deeper analysis)
    route_to_role(classification)        → str   (role name string)
    build_child_job_payload(orig, cls)   → dict  (ready-to-enqueue child job)

Supported roles:
    credit_analyst            credit_repair_letter_agent   business_formation
    funding_strategist        grant_researcher              opportunity_agent
    trading_education         marketing_strategist          content_creator
    ad_copy_agent             compliance_reviewer           hermes_ops
    research_analyst          unknown
"""
from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger("CeoAutoRouter")

# ── Routing keyword table ──────────────────────────────────────────────────────
# Each entry: (keywords_list, role_name, task_type_label)
# Order matters when confidence is equal — earlier entries win ties.

_RULES: list[tuple[list[str], str, str]] = [
    (
        ["dispute letter", "certified mail", "docupost", "goodwill letter",
         "pay for delete", "cease and desist", "credit repair letter"],
        "credit_repair_letter_agent",
        "credit_repair_letter",
    ),
    (
        ["credit report", "negative item", "derogatory", "collections",
         "late payment", "charge off", "credit utilization", "fico", "vantage",
         "credit score", "credit mix", "hard inquiry", "soft pull"],
        "credit_analyst",
        "credit_analysis",
    ),
    (
        ["llc", "ein", "duns number", "business address", "registered agent",
         "naics code", "business phone", "business website", "business formation",
         "incorporate", "articles of organization", "operating agreement"],
        "business_formation",
        "business_foundation",
    ),
    (
        ["tier 1", "0% interest", "0% business credit", "business credit card",
         "sba loan", "funding roadmap", "funding strategy", "tier 2",
         "business credit", "net 30", "vendor credit", "trade line"],
        "funding_strategist",
        "funding_strategy",
    ),
    (
        ["grant", "sbir", "sttr", "grant funding", "grant application",
         "federal grant", "state grant", "small business grant", "micro grant"],
        "grant_researcher",
        "grant_research",
    ),
    (
        ["business idea", "business opportunity", "lead generation",
         "side hustle", "online business", "offline business", "niche",
         "passive income", "dropshipping", "ecommerce idea"],
        "opportunity_agent",
        "opportunity_research",
    ),
    (
        ["stocks", "forex", "options", "crypto", "cryptocurrency",
         "trading strategy", "candlestick", "chart pattern", "technical analysis",
         "trading education", "risk management trading", "position sizing"],
        "trading_education",
        "trading_education",
    ),
    (
        ["campaign strategy", "marketing funnel", "audience targeting",
         "email marketing", "marketing strategy", "lead magnet",
         "customer avatar", "brand positioning", "growth strategy"],
        "marketing_strategist",
        "marketing_strategy",
    ),
    (
        ["tiktok", "instagram reel", "youtube short", "short form video",
         "video script", "content script", "caption", "social content",
         "content creator", "educational content", "content calendar",
         "tiktok script", "instagram script", "reel script", "script"],
        "content_creator",
        "short_form_content",
    ),
    (
        ["ad copy", "facebook ad", "google ad", "paid ad", "headline",
         "landing page copy", "call to action", "cta button", "ad creative",
         "ad campaign copy", "meta ad"],
        "ad_copy_agent",
        "ad_copy",
    ),
    (
        ["compliance review", "compliance check", "approve content",
         "guarantee claim", "misleading", "ftc", "disclaimer needed",
         "review for compliance", "flag claims", "compliance",
         "guarantee", "guaranteed", "false claim", "review this ad"],
        "compliance_reviewer",
        "compliance_review",
    ),
    (
        ["system status", "worker status", "gateway", "restart worker",
         "terminal command", "operations check", "hermes status",
         "process health", "server status", "worker health"],
        "hermes_ops",
        "operations",
    ),
    (
        ["research", "summarize", "collect data", "youtube transcript",
         "analyze content", "extract insights", "research report",
         "data collection", "market research", "competitive analysis"],
        "research_analyst",
        "research",
    ),
]

# Roles that should always get a compliance review flag
_COMPLIANCE_FLAGGED_ROLES = {"content_creator", "ad_copy_agent", "funding_strategist"}

# Roles that should route through the Nexus Super Prompt
_SUPER_PROMPT_ROLES = {
    "credit_analyst", "credit_repair_letter_agent", "business_formation",
    "funding_strategist", "grant_researcher", "opportunity_agent",
    "trading_education", "marketing_strategist", "content_creator",
    "ad_copy_agent", "compliance_reviewer", "research_analyst",
}

# High-stakes roles that need human review before execution
_HUMAN_REVIEW_ROLES = {"credit_repair_letter_agent", "compliance_reviewer"}


def _extract_text(payload: dict) -> str:
    """Pull the most relevant text from a job payload for classification."""
    candidates = [
        payload.get("message", ""),
        payload.get("task_description", ""),
        payload.get("description", ""),
        payload.get("prompt", ""),
        payload.get("content", ""),
    ]
    return " ".join(c for c in candidates if c).lower()


def _score(text: str) -> list[tuple[int, str, str]]:
    """Score each role by keyword hits. Returns sorted (score, role, task_type) list."""
    scores: list[tuple[int, str, str]] = []
    for keywords, role, task_type in _RULES:
        hits = sum(1 for kw in keywords if kw in text)
        if hits:
            scores.append((hits, role, task_type))
    return sorted(scores, key=lambda x: -x[0])


def _confidence(hits: int, total_keywords: int) -> float:
    """Rough confidence from keyword hit ratio."""
    if hits == 0:
        return 0.0
    if hits >= 3:
        return 0.90
    if hits == 2:
        return 0.70
    return 0.45


def classify_task(task_payload: dict) -> dict:
    """
    Classify a task payload and return a routing decision dict.

    The payload SHOULD contain use_ceo_auto_routing: true, but this function
    can be called standalone for testing or manual classification.

    Returns:
        {
            "recommended_role":           str,
            "confidence":                 float (0.0–1.0),
            "reason":                     str,
            "task_type":                  str,
            "requires_human_review":      bool,
            "requires_compliance_review": bool,
            "use_nexus_super_prompt":     bool,
        }
    """
    text = _extract_text(task_payload)

    if not text.strip():
        logger.warning("classify_task: empty payload text — returning unknown")
        return _unknown_result("No task text found in payload")

    scored = _score(text)

    if not scored:
        logger.info("classify_task: no keyword matches — unknown")
        return _unknown_result("No matching keywords in task text")

    top_hits, top_role, top_task_type = scored[0]

    # Find total keywords for this role (for confidence calc)
    total_kw = next(
        len(kws) for kws, r, _ in _RULES if r == top_role
    )
    confidence = _confidence(top_hits, total_kw)

    # Second-place check — if close, lower confidence
    if len(scored) > 1 and scored[1][0] >= top_hits - 1:
        confidence = max(0.35, confidence - 0.15)

    result = {
        "recommended_role":           top_role,
        "confidence":                 round(confidence, 2),
        "reason":                     f"Matched {top_hits} keyword(s) for '{top_role}'",
        "task_type":                  top_task_type,
        "requires_human_review":      top_role in _HUMAN_REVIEW_ROLES,
        "requires_compliance_review": top_role in _COMPLIANCE_FLAGGED_ROLES,
        "use_nexus_super_prompt":     top_role in _SUPER_PROMPT_ROLES,
    }

    logger.info(
        "CEO routing: role=%s confidence=%.2f reason=%s",
        top_role, confidence, result["reason"],
    )
    return result


def _unknown_result(reason: str) -> dict:
    return {
        "recommended_role":           "unknown",
        "confidence":                 0.0,
        "reason":                     reason,
        "task_type":                  "unclassified",
        "requires_human_review":      True,
        "requires_compliance_review": False,
        "use_nexus_super_prompt":     False,
    }


def build_ceo_routing_prompt(task_payload: dict) -> str:
    """
    Build a CEO Super Prompt asking for routing classification.
    Use this when you want LLM-level judgment instead of keyword matching
    (higher quality, higher cost, requires an LLM call).

    The returned prompt is ready to send to any LLM via model_router or
    ollama_fallback. Parse the response with route_to_role().
    """
    text = _extract_text(task_payload)
    source = task_payload.get("source", "unknown")
    channel = task_payload.get("channel", "unknown")

    supported = ", ".join(r for _, r, _ in _RULES) + ", unknown"

    return f"""You are the CEO of Nexus, an AI-powered business funding platform.
Your job is to read an incoming task and decide which AI employee should handle it.

JOURNEY: Unfunded → Fundable → Funded → Scaled

SUPPORTED ROLES:
{supported}

ROLE GUIDE:
- credit_analyst: credit scores, negative items, utilization, FICO
- credit_repair_letter_agent: dispute letters, Docupost, certified mail
- business_formation: LLC, EIN, DUNS, business address, NAICS
- funding_strategist: Tier 1/2 funding, SBA, 0% business credit
- grant_researcher: grants, SBIR, federal/state programs
- opportunity_agent: business ideas, leads, income opportunities
- trading_education: forex, stocks, options, chart analysis
- marketing_strategist: campaigns, funnels, audience, email
- content_creator: TikTok, Instagram, YouTube scripts, captions
- ad_copy_agent: paid ad headlines, copy, CTAs
- compliance_reviewer: content compliance, FTC, misleading claims
- hermes_ops: system status, worker health, operations
- research_analyst: summarize, collect data, transcripts
- unknown: cannot classify with confidence

TASK TO CLASSIFY:
Source: {source}
Channel: {channel}
Message: {text[:600]}

Return ONLY valid JSON — no prose, no markdown:
{{
  "recommended_role": "",
  "confidence": 0.0,
  "reason": "",
  "task_type": "",
  "requires_human_review": false,
  "requires_compliance_review": false,
  "use_nexus_super_prompt": true
}}"""


def route_to_role(classification: dict) -> str:
    """
    Extract the recommended role string from a classification dict.
    Safe to call on LLM JSON responses too — handles raw JSON strings.
    """
    if isinstance(classification, str):
        try:
            classification = json.loads(classification)
        except Exception:
            # Try to extract JSON object from raw LLM response
            match = re.search(r'\{.*\}', classification, re.DOTALL)
            if match:
                try:
                    classification = json.loads(match.group())
                except Exception:
                    return "unknown"
            else:
                return "unknown"

    role = (classification.get("recommended_role") or "unknown").strip().lower()
    known = {r for _, r, _ in _RULES} | {"unknown"}
    return role if role in known else "unknown"


def build_child_job_payload(
    original_payload: dict,
    classification: dict,
    parent_job_id: Optional[str] = None,
) -> dict:
    """
    Build the child job payload that should be enqueued for the routed role.

    This function builds the payload only — it does NOT write to Supabase.
    Enqueue via your existing job_queue or system_events writer.

    Child payload structure preserves the original payload under "original_payload"
    and adds routing metadata at the top level.
    """
    role = route_to_role(classification)

    # Sanitize: never log API keys or private user data beyond task summary
    safe_original = {
        k: v for k, v in original_payload.items()
        if k not in {
            "api_key", "token", "password", "secret",
            "ssn", "dob", "credit_card",
        }
    }

    child = {
        "parent_job_id":         parent_job_id,
        "routed_by":             "ceo_agent",
        "recommended_role":      role,
        "routing_confidence":    classification.get("confidence", 0.0),
        "routing_reason":        classification.get("reason", ""),
        "task_type":             classification.get("task_type", ""),
        "requires_human_review": classification.get("requires_human_review", False),
        "use_nexus_super_prompt": classification.get("use_nexus_super_prompt", True),
        "original_payload":      safe_original,
    }

    # Carry forward the task text so the routed worker can act immediately
    task_text = _extract_text(original_payload)
    if task_text:
        child["task_description"] = task_text[:800]

    logger.info(
        "Built child job: role=%s confidence=%.2f parent=%s",
        role,
        classification.get("confidence", 0.0),
        parent_job_id or "none",
    )
    return child


# ── CLI / manual test ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sample = {
        "use_ceo_auto_routing": True,
        "use_nexus_super_prompt": True,
        "message": sys.argv[1] if len(sys.argv) > 1 else (
            "Create a TikTok script explaining why entrepreneurs should become "
            "fundable before applying for business credit."
        ),
        "source": "admin_portal",
        "channel": "portal",
        "created_from": "manual_test",
    }

    cls = classify_task(sample)
    print("\nClassification:")
    print(json.dumps(cls, indent=2))
    print()
    child = build_child_job_payload(sample, cls, parent_job_id="manual_test_001")
    print("Child job payload:")
    print(json.dumps(child, indent=2))
