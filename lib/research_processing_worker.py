"""
Research Processing Worker — Hermes Knowledge Loop.

Lifecycle:
  submitted → queued → researching → needs_review → completed → archived
                                                   ↘ rejected (with reason)

For each open research ticket:
  1. Pull related internal knowledge (ai_employee_knowledge_router)
  2. Pull completed prior tickets on same topic
  3. Pull transcript_queue excerpts
  4. Synthesize with nexus_model_caller (cheap tier)
  5. Write research_summary + recommended_action to ticket (status: needs_review)
  6. Propose reusable knowledge_items record (status: proposed)
     — admin must approve before it becomes searchable

Safety:
  RESEARCH_PROCESSING_WRITES_ENABLED=true required for all writes.
  NEXUS_DRY_RUN=true does NOT block this (research is safe analytics).
  Never auto-publishes to users. Never auto-approves knowledge.
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone

from .env_loader import load_nexus_env
from .ai_employee_knowledge_router import route_query, ROLE_DEPARTMENT_MAP

load_nexus_env()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

WRITES_ENABLED = os.getenv("RESEARCH_PROCESSING_WRITES_ENABLED", "false").lower() == "true"
MAX_TICKETS_PER_RUN = int(os.getenv("RESEARCH_MAX_TICKETS_PER_RUN", "10"))

DEPT_TO_ROLE: dict[str, str] = {v: k for k, v in ROLE_DEPARTMENT_MAP.items()}
DEPT_TO_KNOWLEDGE_DOMAIN: dict[str, str] = {
    "trading_intelligence":   "trading",
    "grants_research":        "grants",
    "funding_intelligence":   "funding",
    "business_opportunities": "business",
    "credit_research":        "credit",
    "marketing_intelligence": "marketing",
    "operations":             "platform",
}


def _headers(prefer: str = "") -> dict:
    h = {
        "apikey":        SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type":  "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _get(table: str, params: dict) -> list[dict]:
    qs = urllib.parse.urlencode(params)
    url = f"{SUPABASE_URL}/rest/v1/{table}?{qs}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("_get %s failed: %s", table, exc)
        return []


def _patch(table: str, ticket_id: str, payload: dict) -> bool:
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{ticket_id}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_headers("return=minimal"), method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except Exception as exc:
        logger.error("_patch %s/%s failed: %s", table, ticket_id, exc)
        return False


def _post(table: str, payload: dict) -> dict | None:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=_headers("return=representation"), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read())
            return rows[0] if rows else None
    except Exception as exc:
        logger.error("_post %s failed: %s", table, exc)
        return None


# ── Ticket fetching ───────────────────────────────────────────────────────────

def _fetch_open_tickets() -> list[dict]:
    """Fetch open tickets ordered by priority then age."""
    priority_order = "urgent,high,normal,low"
    rows = _get("research_requests", {
        "select": "id,department,request_type,priority,topic,original_question,normalized_query,source_context,status,confidence_gap,risk_level,created_at",
        "status": "in.(submitted,queued)",
        "order":  "created_at.asc",
        "limit":  str(MAX_TICKETS_PER_RUN),
    })
    # Sort urgent/high first
    order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
    return sorted(rows, key=lambda r: order.get(r.get("priority", "normal"), 2))


# ── Internal knowledge gathering ──────────────────────────────────────────────

def _gather_context(ticket: dict) -> dict:
    """Pull related knowledge from all internal layers."""
    dept = ticket.get("department", "operations")
    role = DEPT_TO_ROLE.get(dept, "hermes")
    query = ticket.get("normalized_query") or ticket.get("topic", "")

    result = route_query(role=role, query=query, context={"domain": DEPT_TO_KNOWLEDGE_DOMAIN.get(dept)})

    # Also pull prior completed tickets on same topic
    prior = _get("research_requests", {
        "select": "topic,research_summary,recommended_action,completed_at",
        "status": "eq.completed",
        "or":     f"(topic.ilike.*{query[:40]}*)",
        "order":  "completed_at.desc",
        "limit":  "3",
    })

    # Transcript excerpts
    transcripts = _get("transcript_queue", {
        "select": "source_label,content_summary,extracted_insights",
        "status": "eq.processed",
        "or":     f"(content_summary.ilike.*{query[:40]}*,extracted_insights.ilike.*{query[:40]}*)",
        "limit":  "3",
    })

    return {
        "role":        role,
        "query":       query,
        "knowledge":   result.raw_records[:5],
        "confidence":  result.confidence,
        "sources":     result.sources,
        "prior":       prior,
        "transcripts": transcripts,
        "internal_summary": result.summary,
        "risk_notes":       result.risk_notes,
    }


# ── Research synthesis ────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a Nexus Research Analyst. You synthesize internal business intelligence into safe, educational summaries for small business owners.

Rules:
- Only make claims supported by the provided context
- Label all speculative content as "Nexus perspective (unverified)"
- Always include risk notes for financial/trading topics
- Never promise returns, approval odds, or guaranteed outcomes
- Recommend professional consultation for legal/financial decisions
- Keep summaries under 400 words"""


def _synthesize(ticket: dict, ctx: dict) -> dict:
    """Use nexus_model_caller to generate research_summary + recommended_action."""
    topic = ticket.get("topic", "")
    question = ticket.get("original_question", topic)
    dept = ticket.get("department", "operations")
    risk = ticket.get("risk_level", "unknown")

    # Build context block
    context_lines: list[str] = []

    if ctx["internal_summary"]:
        context_lines.append(f"=== Internal Knowledge ===\n{ctx['internal_summary']}")

    for rec in ctx["knowledge"][:3]:
        snippet = (
            rec.get("content") or rec.get("description") or
            rec.get("educational_summary") or rec.get("research_summary") or ""
        )
        if snippet:
            title = (rec.get("title") or rec.get("opportunity_name") or rec.get("grant_name") or
                     rec.get("strategy_name") or rec.get("name") or "")
            context_lines.append(f"[{title}]: {snippet[:300]}")

    for pr in ctx["prior"][:2]:
        if pr.get("research_summary"):
            context_lines.append(f"[Prior Research — {pr['topic']}]: {pr['research_summary'][:200]}")

    for tr in ctx["transcripts"][:2]:
        insights = tr.get("extracted_insights") or tr.get("content_summary") or ""
        if insights:
            context_lines.append(f"[Transcript — {tr.get('source_label','')}]: {insights[:200]}")

    context_block = "\n\n".join(context_lines) if context_lines else "No internal knowledge found for this topic."

    prompt = f"""Research Topic: {topic}
Original Question: {question}
Department: {dept}
Risk Level: {risk}
Confidence Gap: {ticket.get('confidence_gap', 'unknown')}%

Available Internal Context:
{context_block}

Generate a structured Nexus Research Summary with:
1. SUMMARY (2–3 sentences: what Nexus knows about this topic)
2. KEY FINDINGS (bullet points from internal knowledge only)
3. NEXUS PERSPECTIVE (educational framing — label if speculative)
4. RISK NOTES (what users should know before acting)
5. RECOMMENDED ACTION (what Nexus should do next: approve as knowledge, research further, flag as high-risk, etc.)

Be concise, factual, and safe."""

    try:
        from .nexus_model_caller import call
        result = call(prompt, task_type="cheap", system=_SYSTEM_PROMPT, timeout=60, max_tokens=800)
        if result.get("success"):
            response = result["response"]
            # Split summary from recommended action heuristically
            lines = response.strip().split("\n")
            rec_action = ""
            summary_lines = []
            in_rec = False
            for line in lines:
                if "RECOMMENDED ACTION" in line.upper():
                    in_rec = True
                    continue
                if in_rec:
                    rec_action += line + " "
                else:
                    summary_lines.append(line)

            return {
                "research_summary":    "\n".join(summary_lines).strip()[:3000],
                "recommended_action":  rec_action.strip()[:500] or "Escalate to senior review.",
                "model_used":          result.get("provider", "unknown"),
            }
    except Exception as exc:
        logger.error("synthesis model call failed: %s", exc)

    # Fallback: use internal knowledge only
    fallback = ctx.get("internal_summary") or f"No vetted Nexus knowledge found for: {topic}"
    return {
        "research_summary":   fallback[:3000],
        "recommended_action": "Escalate to senior review — no model synthesis available.",
        "model_used":         "fallback_internal",
    }


# ── Knowledge record proposal ─────────────────────────────────────────────────

def _propose_knowledge(ticket: dict, synthesis: dict) -> str | None:
    """
    Create a knowledge_items record with status='proposed'.
    Admin must change to 'approved' before it becomes searchable.
    """
    if not WRITES_ENABLED:
        logger.info("[DRY] would propose knowledge for ticket %s", ticket["id"])
        return None

    summary = synthesis.get("research_summary", "")
    if not summary or len(summary) < 50:
        return None

    dept = ticket.get("department", "operations")
    domain = DEPT_TO_KNOWLEDGE_DOMAIN.get(dept, "platform")
    topic = ticket.get("topic", "")

    payload = {
        "domain":          domain,
        "title":           f"[Proposed] {topic[:200]}",
        "content":         summary,
        "source_type":     "research_ticket",
        "quality_score":   40,
        "quality_label":   "proposed",
        "freshness_status":"fresh",
        "stale_after_days": 90,
        "status":          "proposed",
        "review_notes":    f"Auto-generated from research_request {ticket['id']}. Requires admin review before activation.",
        "dry_run":         False,
        "metadata": {
            "research_ticket_id": ticket["id"],
            "department":         dept,
            "model_used":         synthesis.get("model_used", "unknown"),
            "confidence_gap":     ticket.get("confidence_gap"),
            "recommended_action": synthesis.get("recommended_action", ""),
        },
    }

    row = _post("knowledge_items", payload)
    if row:
        logger.info("proposed knowledge_items record: %s", row.get("id"))
        return row.get("id")
    return None


# ── Ticket lifecycle transitions ──────────────────────────────────────────────

def _advance_to_researching(ticket_id: str) -> bool:
    if not WRITES_ENABLED:
        return True
    return _patch("research_requests", ticket_id, {
        "status": "researching",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def _complete_ticket(ticket_id: str, synthesis: dict, knowledge_id: str | None) -> bool:
    if not WRITES_ENABLED:
        logger.info("[DRY] would complete ticket %s", ticket_id)
        return True

    payload: dict = {
        "status":               "needs_review",
        "client_visible_status":"under_review",
        "research_summary":     synthesis.get("research_summary", ""),
        "recommended_action":   synthesis.get("recommended_action", ""),
        "updated_at":           datetime.now(timezone.utc).isoformat(),
    }
    if knowledge_id:
        payload["knowledge_record_id"] = knowledge_id

    return _patch("research_requests", ticket_id, payload)


def _reject_ticket(ticket_id: str, reason: str) -> bool:
    if not WRITES_ENABLED:
        return True
    return _patch("research_requests", ticket_id, {
        "status":         "rejected",
        "review_notes":   reason,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    })


# ── Main processing loop ──────────────────────────────────────────────────────

def process_ticket(ticket: dict) -> dict:
    """Process a single research ticket end-to-end."""
    ticket_id = ticket["id"]
    topic = ticket.get("topic", "unknown")
    logger.info("processing ticket %s: %s", ticket_id, topic[:60])

    result = {
        "ticket_id":    ticket_id,
        "topic":        topic,
        "status":       "skipped",
        "knowledge_id": None,
        "error":        None,
    }

    # Mark researching
    _advance_to_researching(ticket_id)

    try:
        # Gather internal knowledge
        ctx = _gather_context(ticket)
        logger.info("ticket %s: confidence=%d sources=%s", ticket_id, ctx["confidence"], ctx["sources"])

        # Synthesize
        synthesis = _synthesize(ticket, ctx)
        logger.info("ticket %s: synthesis complete (%d chars)", ticket_id, len(synthesis.get("research_summary", "")))

        # Propose knowledge
        knowledge_id = _propose_knowledge(ticket, synthesis)

        # Advance ticket to needs_review
        _complete_ticket(ticket_id, synthesis, knowledge_id)

        result.update({
            "status":       "needs_review",
            "knowledge_id": knowledge_id,
            "confidence":   ctx["confidence"],
            "sources":      ctx["sources"],
        })

    except Exception as exc:
        logger.error("ticket %s processing error: %s", ticket_id, exc)
        _reject_ticket(ticket_id, f"Processing error: {exc}")
        result["status"] = "error"
        result["error"] = str(exc)

    return result


def run_processing_loop() -> dict:
    """
    Main entry point. Fetch open tickets, process each.
    Returns a summary dict suitable for CEO digest / Telegram alert.
    """
    logger.info("research_processing_worker starting. WRITES_ENABLED=%s", WRITES_ENABLED)

    tickets = _fetch_open_tickets()
    logger.info("found %d open tickets", len(tickets))

    results: list[dict] = []
    for ticket in tickets:
        res = process_ticket(ticket)
        results.append(res)

    processed = [r for r in results if r["status"] in ("needs_review", "error")]
    knowledge_proposed = [r for r in results if r.get("knowledge_id")]

    summary = {
        "tickets_found":      len(tickets),
        "tickets_processed":  len(processed),
        "knowledge_proposed": len(knowledge_proposed),
        "needs_review":       [r["ticket_id"] for r in results if r["status"] == "needs_review"],
        "errors":             [r for r in results if r["status"] == "error"],
        "writes_enabled":     WRITES_ENABLED,
    }

    logger.info(
        "loop complete: processed=%d knowledge_proposed=%d errors=%d",
        len(processed), len(knowledge_proposed), len(summary["errors"]),
    )
    return summary


# ── Hermes intake digest ──────────────────────────────────────────────────────

def hermes_intake_digest() -> dict:
    """
    Returns a structured view of pending research work for Hermes.
    Read-only — no writes.
    """
    open_tickets = _get("research_requests", {
        "select": "id,department,priority,topic,status,confidence_gap,created_at",
        "status": "in.(submitted,queued,researching,needs_review)",
        "order":  "created_at.asc",
        "limit":  "50",
    })

    now = datetime.now(timezone.utc)
    overdue: list[dict] = []
    by_dept: dict[str, int] = {}
    by_priority: dict[str, int] = {}

    for t in open_tickets:
        dept = t.get("department", "unknown")
        pri = t.get("priority", "normal")
        by_dept[dept] = by_dept.get(dept, 0) + 1
        by_priority[pri] = by_priority.get(pri, 0) + 1
        created = t.get("created_at", "")
        if created:
            age_h = (now - datetime.fromisoformat(created.replace("Z", "+00:00"))).total_seconds() / 3600
            if age_h > 24:
                overdue.append({**t, "age_hours": round(age_h, 1)})

    recent_completed = _get("research_requests", {
        "select": "id,department,topic,research_summary,completed_at",
        "status": "eq.needs_review",
        "order":  "updated_at.desc",
        "limit":  "5",
    })

    return {
        "open_total":        len(open_tickets),
        "overdue":           overdue,
        "by_department":     by_dept,
        "by_priority":       by_priority,
        "needs_review":      recent_completed,
        "top_priority_dept": max(by_dept, key=lambda d: by_dept[d]) if by_dept else None,
        "generated_at":      now.isoformat(),
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    summary = run_processing_loop()
    print(json.dumps(summary, indent=2, default=str))
