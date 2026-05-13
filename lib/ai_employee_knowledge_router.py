"""
Supabase-first knowledge router for all Nexus AI employees.

Response order (mandatory):
  1. knowledge_items (approved internal knowledge)
  2. Domain-specific tables (grants_catalog, strategies_catalog, business_opportunities, user_opportunities)
  3. Prior research_requests (completed tickets)
  4. transcript_queue / operational reports (NotebookLM-derived)
  5. provider_health / analytics_events (live ops context)
  6. General model reasoning (fallback only, clearly labeled)
  7. If confidence < threshold → create research ticket

Never hallucinate. If internal knowledge is insufficient, escalate.
"""

import os
import json
import logging
from typing import Any
from dataclasses import dataclass, field

from .env_loader import get_env

logger = logging.getLogger(__name__)

SUPABASE_URL = get_env("SUPABASE_URL")
SUPABASE_SERVICE_KEY = get_env("SUPABASE_SERVICE_KEY")

# Minimum confidence to answer without escalating (0-100)
CONFIDENCE_THRESHOLD = int(os.getenv("KNOWLEDGE_CONFIDENCE_THRESHOLD", "60"))

ROLE_DOMAIN_MAP: dict[str, list[str]] = {
    "hermes":                ["knowledge_items", "strategies_catalog", "user_opportunities", "provider_health"],
    "trading_analyst":       ["knowledge_items", "strategies_catalog", "provider_health", "analytics_events"],
    "grant_researcher":      ["knowledge_items", "grants_catalog", "user_opportunities"],
    "funding_strategist":    ["knowledge_items", "business_opportunities", "user_opportunities", "grants_catalog"],
    "business_opportunity":  ["knowledge_items", "business_opportunities", "user_opportunities"],
    "credit_coach":          ["knowledge_items", "user_opportunities"],
    "marketing_researcher":  ["knowledge_items", "analytics_events"],
    "system_monitor":        ["knowledge_items", "provider_health", "analytics_events"],
}

# Department label for research ticket routing
ROLE_DEPARTMENT_MAP: dict[str, str] = {
    "hermes":                "operations",
    "trading_analyst":       "trading_intelligence",
    "grant_researcher":      "grants_research",
    "funding_strategist":    "funding_intelligence",
    "business_opportunity":  "business_opportunities",
    "credit_coach":          "credit_research",
    "marketing_researcher":  "marketing_intelligence",
    "system_monitor":        "operations",
}


@dataclass
class KnowledgeResult:
    status: str                         # found | partial | not_found | escalated
    confidence: int                     # 0–100
    sources: list[str] = field(default_factory=list)
    summary: str = ""
    risk_notes: str = ""
    suggested_response: str = ""
    escalation_needed: bool = False
    raw_records: list[dict] = field(default_factory=list)


def _headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def _get(table: str, params: dict) -> list[dict]:
    """PostgREST GET with query params. Returns list of rows."""
    import urllib.request
    import urllib.parse

    qs = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/{table}?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("knowledge_router _get %s failed: %s", table, exc)
        return []


# ── Layer 1: approved internal knowledge ──────────────────────────────────────

def _search_knowledge_items(query: str, domain: str | None = None) -> list[dict]:
    params: dict = {
        "select": "id,domain,title,content,source_type,quality_score,quality_label,freshness_status",
        "or":     f"(title.ilike.*{query}*,content.ilike.*{query}*)",
        "order":  "quality_score.desc",
        "limit":  "5",
    }
    if domain:
        params["domain"] = f"eq.{domain}"
    return _get("knowledge_items", params)


# ── Layer 2: domain-specific tables ───────────────────────────────────────────

def _search_grants_catalog(query: str) -> list[dict]:
    return _get("grants_catalog", {
        "select": "id,grant_name,grant_type,funding_amount,eligibility_summary,application_url",
        "or":     f"(grant_name.ilike.*{query}*,eligibility_summary.ilike.*{query}*)",
        "limit":  "5",
    })


def _search_strategies_catalog(query: str) -> list[dict]:
    return _get("strategies_catalog", {
        "select": "id,strategy_name,description,risk_level,recommended_for",
        "or":     f"(strategy_name.ilike.*{query}*,description.ilike.*{query}*)",
        "limit":  "5",
    })


def _search_business_opportunities(query: str) -> list[dict]:
    return _get("business_opportunities", {
        "select": "id,opportunity_name,category,description,feasibility_notes",
        "or":     f"(opportunity_name.ilike.*{query}*,description.ilike.*{query}*)",
        "limit":  "5",
    })


def _search_user_opportunities(query: str, user_id: str | None = None) -> list[dict]:
    params: dict = {
        "select": "id,opportunity_name,category,feasibility_score,opportunity_score,educational_summary",
        "or":     f"(opportunity_name.ilike.*{query}*,educational_summary.ilike.*{query}*)",
        "limit":  "5",
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    return _get("user_opportunities", params)


# ── Layer 3: prior completed research tickets ─────────────────────────────────

def _search_prior_research(query: str) -> list[dict]:
    return _get("research_requests", {
        "select": "id,topic,research_summary,recommended_action,department,completed_at",
        "status": "eq.completed",
        "or":     f"(topic.ilike.*{query}*,research_summary.ilike.*{query}*)",
        "order":  "completed_at.desc",
        "limit":  "3",
    })


# ── Layer 4: transcript / ops context ─────────────────────────────────────────

def _search_transcript_queue(query: str) -> list[dict]:
    return _get("transcript_queue", {
        "select": "id,source_label,content_summary,extracted_insights,status",
        "status": "eq.processed",
        "or":     f"(content_summary.ilike.*{query}*,extracted_insights.ilike.*{query}*)",
        "limit":  "3",
    })


# ── Layer 5: live ops context ─────────────────────────────────────────────────

def _get_provider_health() -> list[dict]:
    return _get("provider_health", {
        "select": "provider_name,status,latency_ms,last_checked_at",
        "order":  "last_checked_at.desc",
        "limit":  "10",
    })


def _get_recent_analytics(query: str) -> list[dict]:
    return _get("analytics_events", {
        "select": "event_type,event_data,created_at",
        "or":     f"(event_type.ilike.*{query}*)",
        "order":  "created_at.desc",
        "limit":  "5",
    })


# ── Confidence scoring ─────────────────────────────────────────────────────────

def _score_confidence(knowledge: list, domain: list, prior: list, transcripts: list) -> int:
    score = 0
    if knowledge:
        best_quality = max((r.get("quality_score") or 0 for r in knowledge), default=0)
        score += min(50, int(best_quality * 0.5))
        # Freshness bonus
        for r in knowledge:
            if r.get("freshness_status") == "fresh":
                score += 10
                break
    if domain:
        score += min(20, len(domain) * 7)
    if prior:
        score += min(15, len(prior) * 7)
    if transcripts:
        score += 5
    return min(100, score)


# ── Main router ────────────────────────────────────────────────────────────────

def route_query(
    role: str,
    query: str,
    context: dict | None = None,
) -> KnowledgeResult:
    """
    Entry point for all AI employees. Returns a KnowledgeResult.

    Args:
        role:    One of ROLE_DOMAIN_MAP keys
        query:   The user's question or normalized topic
        context: Optional dict with user_id, conversation_id, etc.
    """
    context = context or {}
    user_id: str | None = context.get("user_id")
    domain_hint: str | None = context.get("domain")

    domains = ROLE_DOMAIN_MAP.get(role, ["knowledge_items"])
    sources: list[str] = []
    all_records: list[dict] = []

    # Layer 1 — approved knowledge
    knowledge_hits: list[dict] = []
    if "knowledge_items" in domains:
        knowledge_hits = _search_knowledge_items(query, domain_hint)
        if knowledge_hits:
            sources.append("knowledge_items")
            all_records.extend(knowledge_hits)

    # Layer 2 — domain tables
    domain_hits: list[dict] = []
    if "grants_catalog" in domains:
        rows = _search_grants_catalog(query)
        if rows:
            domain_hits.extend(rows)
            sources.append("grants_catalog")
            all_records.extend(rows)
    if "strategies_catalog" in domains:
        rows = _search_strategies_catalog(query)
        if rows:
            domain_hits.extend(rows)
            sources.append("strategies_catalog")
            all_records.extend(rows)
    if "business_opportunities" in domains:
        rows = _search_business_opportunities(query)
        if rows:
            domain_hits.extend(rows)
            sources.append("business_opportunities")
            all_records.extend(rows)
    if "user_opportunities" in domains:
        rows = _search_user_opportunities(query, user_id)
        if rows:
            domain_hits.extend(rows)
            sources.append("user_opportunities")
            all_records.extend(rows)

    # Layer 3 — completed research tickets
    prior_hits: list[dict] = []
    prior_hits = _search_prior_research(query)
    if prior_hits:
        sources.append("research_requests(completed)")
        all_records.extend(prior_hits)

    # Layer 4 — transcripts
    transcript_hits: list[dict] = []
    transcript_hits = _search_transcript_queue(query)
    if transcript_hits:
        sources.append("transcript_queue")
        all_records.extend(transcript_hits)

    # Layer 5 — live ops (role-gated)
    if "provider_health" in domains:
        ph = _get_provider_health()
        if ph:
            sources.append("provider_health")

    confidence = _score_confidence(knowledge_hits, domain_hits, prior_hits, transcript_hits)

    escalation_needed = confidence < CONFIDENCE_THRESHOLD
    status = "found" if confidence >= CONFIDENCE_THRESHOLD else ("partial" if all_records else "not_found")

    # Build summary from best records
    summary_parts: list[str] = []
    for rec in (knowledge_hits + domain_hits)[:3]:
        snippet = (
            rec.get("content") or
            rec.get("educational_summary") or
            rec.get("research_summary") or
            rec.get("description") or
            rec.get("eligibility_summary") or ""
        )
        if snippet:
            title = rec.get("title") or rec.get("opportunity_name") or rec.get("grant_name") or rec.get("strategy_name") or ""
            summary_parts.append(f"[{title}] {snippet[:300]}")

    summary = "\n\n".join(summary_parts) if summary_parts else ""

    # Risk notes from knowledge records
    risk_parts: list[str] = []
    for rec in knowledge_hits:
        label = rec.get("quality_label") or ""
        freshness = rec.get("freshness_status") or ""
        if freshness == "stale":
            risk_parts.append(f"⚠️ Source '{rec.get('title')}' may be outdated.")
        if label == "unverified":
            risk_parts.append(f"⚠️ Source '{rec.get('title')}' is unverified — use with caution.")
    risk_notes = " ".join(risk_parts)

    # Suggested response
    if status == "found" and summary:
        suggested_response = summary
    elif escalation_needed:
        suggested_response = (
            "Nexus does not have a vetted answer for that yet. "
            "I can submit it to the research team and notify you when the analysis is complete."
        )
    else:
        suggested_response = summary or "I found limited information on that topic. Escalating for deeper research."

    return KnowledgeResult(
        status=status,
        confidence=confidence,
        sources=sources,
        summary=summary,
        risk_notes=risk_notes,
        suggested_response=suggested_response,
        escalation_needed=escalation_needed,
        raw_records=all_records,
    )
