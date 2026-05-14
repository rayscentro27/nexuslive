"""
Research ticket creation service for Nexus AI employees.

When an AI employee's confidence is below threshold, this service:
  1. Deduplicates against open tickets for the same topic
  2. Routes to the correct department
  3. Sets priority based on confidence_gap
  4. Writes to research_requests via service role
  5. Returns a client-friendly fallback response

Safety: write-gated by RESEARCH_REQUEST_WRITES_ENABLED.
DRY_RUN does NOT block this — research tickets are safe analytics.
"""

import os
import json
import logging
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

from .env_loader import load_nexus_env
from .ai_employee_knowledge_router import ROLE_DEPARTMENT_MAP, KnowledgeResult

load_nexus_env()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

WRITES_ENABLED = os.getenv("RESEARCH_REQUEST_WRITES_ENABLED", "false").lower() == "true"
RECENT_QUERY_COOLDOWN_MINUTES = int(os.getenv("RESEARCH_QUERY_COOLDOWN_MINUTES", "30") or "30")
MAX_RESEARCH_NOTIFICATIONS_PER_HOUR = int(os.getenv("MAX_RESEARCH_NOTIFICATIONS_PER_HOUR", "6") or "6")

# Hours estimates by department
DEPT_COMPLETION_HOURS: dict[str, int] = {
    "trading_intelligence":  4,
    "grants_research":       8,
    "funding_intelligence":  6,
    "business_opportunities": 6,
    "credit_research":       4,
    "marketing_intelligence": 8,
    "operations":            2,
}

# Client-facing fallback templates by department
FALLBACK_TEMPLATES: dict[str, str] = {
    "trading_intelligence": (
        "Nexus does not have a vetted trading analysis for that yet. "
        "I've submitted a research ticket to the Trading Intelligence team. "
        "They'll review market data and return a verified summary. You'll be notified when it's ready."
    ),
    "grants_research": (
        "Nexus doesn't have a confirmed grant match for that question yet. "
        "I've submitted a research ticket to the Grants Research team. "
        "They'll audit active grant programs and update your dashboard when complete."
    ),
    "funding_intelligence": (
        "Nexus doesn't have a vetted funding option for that scenario yet. "
        "I've escalated to the Funding Intelligence team. "
        "They'll evaluate lenders, terms, and eligibility and report back to you."
    ),
    "business_opportunities": (
        "Nexus doesn't have a verified business opportunity analysis for that yet. "
        "I've submitted a research ticket to the Business Opportunities team. "
        "You'll be notified when the feasibility review is complete."
    ),
    "credit_research": (
        "Nexus doesn't have a verified credit strategy for that scenario yet. "
        "I've submitted a research ticket to the Credit Research team. "
        "They'll review current products and return tailored recommendations."
    ),
    "marketing_intelligence": (
        "Nexus doesn't have a vetted marketing analysis for that yet. "
        "I've submitted a research ticket to the Marketing Intelligence team. "
        "You'll receive a strategy brief when the research is complete."
    ),
    "operations": (
        "Nexus does not have a vetted answer for that yet. "
        "I can submit it to the research team and notify you when the analysis is complete."
    ),
}


def _headers() -> dict:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _topic_hash(topic: str, department: str) -> str:
    """Stable hash for deduplication."""
    return hashlib.sha256(f"{department}::{topic.lower().strip()}".encode()).hexdigest()[:16]


def _find_open_ticket(topic: str, department: str, user_id: str | None) -> dict | None:
    """Return an open ticket for same department+topic if exists."""
    params: dict = {
        "select":     "id,status,created_at,client_visible_status",
        "department": f"eq.{department}",
        "topic":      f"ilike.*{topic[:50]}*",
        "status":     "in.(submitted,queued,researching,needs_review)",
        "limit":      "1",
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"

    qs = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/research_requests?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            rows = json.loads(resp.read())
            return rows[0] if rows else None
    except Exception as exc:
        logger.warning("research_request_service dedup check failed: %s", exc)
        return None


def _find_recent_ticket_by_normalized_query(query: str, department: str, user_id: str | None) -> dict | None:
    if not SUPABASE_URL:
        return None
    cutoff_iso = (datetime.now(timezone.utc) - timedelta(minutes=max(1, RECENT_QUERY_COOLDOWN_MINUTES))).isoformat()
    params: dict = {
        "select": "id,status,created_at,normalized_query",
        "department": f"eq.{department}",
        "normalized_query": f"eq.{query[:500]}",
        "status": "in.(submitted,queued,researching,needs_review)",
        "created_at": f"gte.{cutoff_iso}",
        "order": "created_at.desc",
        "limit": "1",
    }
    if user_id:
        params["user_id"] = f"eq.{user_id}"
    qs = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/research_requests?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            rows = json.loads(resp.read())
            return rows[0] if rows else None
    except Exception as exc:
        logger.warning("research_request_service recent dedup check failed: %s", exc)
        return None


def _priority_from_gap(confidence: int) -> str:
    gap = 100 - confidence
    if gap >= 80:
        return "urgent"
    if gap >= 60:
        return "high"
    if gap >= 40:
        return "normal"
    return "low"


def _risk_from_department(department: str) -> str:
    high_risk = {"trading_intelligence", "funding_intelligence"}
    medium_risk = {"grants_research", "credit_research", "business_opportunities"}
    if department in high_risk:
        return "medium"
    if department in medium_risk:
        return "low"
    return "low"


def create_research_ticket(
    role: str,
    query: str,
    original_question: str,
    result: KnowledgeResult,
    user_id: str | None = None,
    conversation_id: str | None = None,
    request_type: str = "knowledge_gap",
) -> dict:
    """
    Create a research_requests ticket. Returns a dict with:
      - ticket_id (or None if duplicate/dry)
      - status: created | duplicate | dry_run
      - client_response: str (always safe to display)
      - department: str
      - priority: str
    """
    department = ROLE_DEPARTMENT_MAP.get(role, "operations")
    priority = _priority_from_gap(result.confidence)
    risk_level = _risk_from_department(department)
    est_hours = DEPT_COMPLETION_HOURS.get(department, 6)
    client_response = FALLBACK_TEMPLATES.get(department, FALLBACK_TEMPLATES["operations"])

    if not WRITES_ENABLED:
        logger.info("[DRY] research ticket would be created: dept=%s topic=%s priority=%s", department, query[:60], priority)
        return {
            "ticket_id": None,
            "status": "dry_run",
            "client_response": client_response,
            "department": department,
            "priority": priority,
        }

    # Deduplication
    existing = _find_recent_ticket_by_normalized_query(query, department, user_id) or _find_open_ticket(query, department, user_id)
    if existing:
        logger.info("research ticket already open: %s", existing.get("id"))
        return {
            "ticket_id": existing["id"],
            "status": "duplicate",
            "client_response": client_response,
            "department": department,
            "priority": priority,
        }

    source_context = {
        "employee_role":          role,
        "conversation_id":        conversation_id,
        "prior_sources_checked":  result.sources,
        "confidence_at_submission": result.confidence,
    }

    payload = {
        "user_id":                   user_id,
        "department":                department,
        "request_type":              request_type,
        "priority":                  priority,
        "topic":                     query[:500],
        "original_question":         original_question[:2000],
        "normalized_query":          query[:500],
        "source_context":            source_context,
        "status":                    "submitted",
        "confidence_gap":            100 - result.confidence,
        "estimated_completion_hours": est_hours,
        "risk_level":                risk_level,
        "client_visible_status":     "researching",
        "notify_user_when_ready":    True,
    }

    data = json.dumps(payload).encode()
    url = f"{SUPABASE_URL}/rest/v1/research_requests"
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read())
            ticket_id = rows[0]["id"] if rows else None
            logger.info("research ticket created: id=%s dept=%s priority=%s", ticket_id, department, priority)
            return {
                "ticket_id": ticket_id,
                "status": "created",
                "client_response": client_response,
                "department": department,
                "priority": priority,
            }
    except Exception as exc:
        logger.error("research ticket write failed: %s", exc)
        return {
            "ticket_id": None,
            "status": "error",
            "client_response": client_response,
            "department": department,
            "priority": priority,
        }


def handle_employee_query(
    role: str,
    query: str,
    original_question: str | None = None,
    context: dict | None = None,
) -> dict:
    """
    Full pipeline: route → escalate if needed.
    Returns dict with: suggested_response, sources, confidence, ticket (if created).
    """
    from .ai_employee_knowledge_router import route_query

    original_question = original_question or query
    context = context or {}

    result = route_query(role=role, query=query, context=context)

    ticket = None
    supportive_sources = {"transcript_queue", "knowledge_items", "research_requests(completed)", "user_opportunities", "strategies_catalog"}
    has_supportive_context = any(src in supportive_sources for src in (result.sources or []))
    should_escalate = result.escalation_needed and not has_supportive_context

    if should_escalate:
        ticket = create_research_ticket(
            role=role,
            query=query,
            original_question=original_question,
            result=result,
            user_id=context.get("user_id"),
            conversation_id=context.get("conversation_id"),
        )

    return {
        "suggested_response": result.suggested_response,
        "sources":            result.sources,
        "confidence":         result.confidence,
        "status":             result.status,
        "risk_notes":         result.risk_notes,
        "escalation_needed":  should_escalate,
        "ticket":             ticket,
    }
