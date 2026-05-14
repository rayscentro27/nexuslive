"""
hermes_supabase_first.py — Supabase-first knowledge layer for Hermes Telegram.

Called between try_internal_first() and the OpenRouter LLM fallback.
Intercepts Nexus-relevant questions and routes them through the approved
knowledge router + research ticket system.

Returns:
  str  — conversational Nexus-sourced response (use directly)
  None — not a Nexus knowledge question; let LLM handle

Never:
  - Says "I don't have live data"
  - Says "Run Nexus search"
  - Hallucinates answers
  - Creates duplicate tickets
"""
from __future__ import annotations

import logging
import os
from collections import Counter

from .env_loader import load_nexus_env
from .nexus_semantic_concepts import expand_query, detect_hype, get_related_concepts

load_nexus_env()

logger = logging.getLogger(__name__)

RESEARCH_WRITES_ENABLED = os.getenv("RESEARCH_REQUEST_WRITES_ENABLED", "false").lower() == "true"

# ── Trigger detection ─────────────────────────────────────────────────────────

# Questions that should always go through the Supabase-first router
_KNOWLEDGE_TRIGGERS: list[str] = [
    # Direct knowledge queries
    "nexus know", "nexus has", "has nexus", "what nexus", "nexus research",
    "nexus find", "nexus review", "nexus approved", "approved knowledge",
    "internal knowledge", "nexus intelligence", "recently approved",
    "what research", "what knowledge", "what trading research", "what grant",
    "what funding", "what opportunities", "nexus validated",
    # Research/ticket actions
    "can nexus", "submit for research", "research ticket", "in the queue",
    "in the research", "research status", "research queue",
    # Domain topics — these should always check Supabase
    "ict silver bullet", "silver bullet strategy",
    "affiliate automation", "ai affiliate",
    "hello alice", "sba grant", "cdfi microloan",
    "funding path", "funding for startup", "startup lender",
    "business credit",
    # Opportunity/grant queries
    "validated opportunit", "validated grant", "nexus opportunit",
    "ingested knowledge", "new knowledge was ingested", "trading videos", "transcript sources", "nitrotrades email", "nitrotrades",
    "pending review", "pending knowledge", "ingestion status", "highest quality sources", "trending internally",
]

# Topics that map to AI employee roles
_ROLE_KEYWORDS: dict[str, list[str]] = {
    "trading_analyst": [
        "trading", "strategy", "strategies", "ict", "silver bullet", "indicator",
        "session", "breakout", "momentum", "paper trade", "forex", "spy",
        "backtest", "entry", "signal", "risk reward", "lot size",
    ],
    "grant_researcher": [
        "grant", "grants", "hello alice", "sba grant", "community grant",
        "small business grant", "ai education", "grant program",
    ],
    "funding_strategist": [
        "funding", "lender", "loan", "microloan", "cdfi", "sba loan",
        "line of credit", "capital", "investor", "revenue based", "startup funding",
        "low revenue", "pre-revenue", "fundable",
    ],
    "business_opportunity": [
        "opportunity", "opportunities", "affiliate", "automation", "side hustle",
        "business idea", "business model", "income stream", "validated opportunit",
        "business opportunit",
    ],
    "credit_coach": [
        "credit score", "business credit", "credit builder", "credit building",
        "credit profile", "credit utilization", "tradeline",
    ],
    "marketing_researcher": [
        "marketing", "content strategy", "social media", "audience", "funnel",
        "lead generation", "brand",
    ],
    "system_monitor": [
        "provider", "worker status", "system status", "uptime", "provider health",
    ],
}


def _should_intercept(text: str) -> bool:
    t = text.lower()
    return any(trigger in t for trigger in _KNOWLEDGE_TRIGGERS)


def _detect_role(text: str) -> str:
    t = text.lower()
    for role, keywords in _ROLE_KEYWORDS.items():
        if any(k in t for k in keywords):
            return role
    return "hermes"


# ── Response formatters ───────────────────────────────────────────────────────

_DEPT_LABELS = {
    "trading_intelligence":   "Trading Intelligence",
    "grants_research":        "Grant Research",
    "funding_intelligence":   "Funding Intelligence",
    "business_opportunities": "Business Opportunities",
    "credit_research":        "Credit Research",
    "marketing_intelligence": "Marketing Intelligence",
    "operations":             "Operations",
}


def _format_found(result: dict, role: str) -> str:
    summary = (result.get("summary") or result.get("suggested_response") or "").strip()
    sources = result.get("sources") or []
    src_str = ", ".join(sources[:3]) if sources else "internal knowledge"
    risk = result.get("risk_notes") or ""

    lines = [f"Nexus has this in approved knowledge (source: {src_str})."]
    if summary:
        lines.append(summary[:400])
    if risk:
        lines.append(f"⚠️ {risk}")
    return "\n\n".join(lines)


def _format_partial(result: dict, role: str) -> str:
    summary = (result.get("summary") or "").strip()
    sources = result.get("sources") or []
    src_str = ", ".join(sources[:3]) if sources else "internal data"
    confidence = result.get("confidence", 0)

    lines = [f"Nexus has partial internal data on this ({src_str}, confidence: {confidence}%)."]
    if summary:
        lines.append(summary[:300])
    lines.append("If you need a deeper analysis, I can submit this for research review.")
    return "\n\n".join(lines)


def _format_ticket_created(ticket: dict, query: str) -> str:
    dept = _DEPT_LABELS.get(ticket.get("department", ""), ticket.get("department", "the research team"))
    priority = ticket.get("priority", "normal")
    return (
        f"I submitted this to {dept} for research (priority: {priority}). "
        f"You'll see it in the Tickets tab under Admin → AI Team. "
        f"Once the research team reviews and approves it, it becomes reusable Nexus knowledge. "
        f"I'll send a notification when it's ready."
    )


def _format_ticket_duplicate(ticket: dict, query: str) -> str:
    dept = _DEPT_LABELS.get(ticket.get("department", ""), "the research team")
    return (
        f"That research request is already in the queue for {dept}. "
        f"Current status: researching. "
        f"I'll notify you when it moves to review."
    )


def _format_ticket_dry_run(ticket: dict, query: str) -> str:
    dept = _DEPT_LABELS.get(ticket.get("department", ""), "the research team")
    return (
        f"Nexus doesn't have a vetted answer for that yet. "
        f"This would be submitted to {dept} for research. "
        f"Enable RESEARCH_REQUEST_WRITES_ENABLED=true to activate ticket creation."
    )


# ── Query normalization ───────────────────────────────────────────────────────

_QUERY_PREFIXES = [
    "can nexus research ", "can nexus find ", "can nexus review ", "can nexus help with ",
    "what does nexus know about ", "what nexus knows about ",
    "has nexus researched ", "has nexus reviewed ",
    "nexus research ", "nexus find ", "nexus review ",
    "what nexus knows ", "does nexus have ",
    "tell me what nexus knows about ",
]

def _normalize_query(text: str) -> str:
    """Strip question preamble to get the core research topic."""
    t = text.strip()
    tl = t.lower()
    for prefix in _QUERY_PREFIXES:
        if tl.startswith(prefix):
            core = t[len(prefix):]
            # Strip trailing punctuation
            return core.rstrip("?.!").strip()
    return t


# ── Retrieval handlers (no ticket creation) ───────────────────────────────────

def _supabase_get(table: str, params: dict) -> list[dict]:
    import json, urllib.request, urllib.parse
    supa_url = os.getenv("SUPABASE_URL", "")
    supa_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    qs = urllib.parse.urlencode(params)
    url = f"{supa_url}/rest/v1/{table}?{qs}"
    req = urllib.request.Request(url, headers={
        "apikey": supa_key,
        "Authorization": f"Bearer {supa_key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except Exception as exc:
        logger.warning("hermes_supabase_first _get %s: %s", table, exc)
        return []


def summarize_recent_ingestions(domain: str | None = None, limit: int = 10) -> str:
    params = {
        "select": "title,source_url,status,domain,created_at,metadata",
        "order": "created_at.desc",
        "limit": str(limit),
    }
    if domain:
        params["domain"] = f"eq.{domain}"
    rows = _supabase_get("transcript_queue", params)
    if not rows:
        return "No recent transcript ingestions found."
    lines = [f"• {r.get('title') or r.get('source_url') or 'source'} ({r.get('status','unknown')})" for r in rows[:limit]]
    return "Recent ingested transcript sources:\n" + "\n".join(lines)


def summarize_ingestion_operations(limit: int = 40) -> str:
    from .knowledge_ingestion_ops import build_ingestion_snapshot

    t_rows = _supabase_get("transcript_queue", {
        "select": "source_url,source_type,status,created_at",
        "order": "created_at.desc",
        "limit": str(limit),
    })
    k_rows = _supabase_get("knowledge_items", {
        "select": "source_url,status,created_at",
        "order": "created_at.desc",
        "limit": str(limit),
    })
    snap = build_ingestion_snapshot(t_rows, k_rows)
    return (
        "Ingestion operations snapshot:\n"
        f"• queue={snap.get('transcript_queue_total', 0)} | proposed={snap.get('proposed_count', 0)} | approved={snap.get('approved_count', 0)} | rejected={snap.get('rejected_count', 0)}\n"
        f"• transcripts ready={snap.get('transcript_available_count', 0)} | failures={snap.get('ingestion_failure_count', 0)}"
    )


def summarize_transcript_topics(domain: str = "trading", limit: int = 20) -> str:
    rows = _supabase_get("transcript_queue", {
        "select": "title,cleaned_content,source_url,status,metadata",
        "domain": f"eq.{domain}",
        "order": "created_at.desc",
        "limit": str(limit),
    })
    if not rows:
        return "No transcript themes available yet."
    lexicon = {
        "session timing": ["session", "london", "new york", "timing", "overlap"],
        "entries": ["entry", "entries", "trigger", "setup"],
        "risk management": ["risk", "stop", "drawdown", "position size", "rr"],
        "momentum": ["momentum", "continuation", "breakout"],
    }
    counts = Counter()
    for r in rows:
        text = f"{r.get('title','')} {r.get('cleaned_content','')}".lower()
        for theme, keys in lexicon.items():
            if any(k in text for k in keys):
                counts[theme] += 1
    if not counts:
        return "Transcript themes are still sparse; source ingestion is present but thematic extraction is limited."
    ordered = [f"• {k} ({v} source{'s' if v != 1 else ''})" for k, v in counts.most_common(4)]
    return "Transcript themes detected:\n" + "\n".join(ordered)


def summarize_pending_trading_research(limit: int = 5) -> str:
    rows = _supabase_get("research_requests", {
        "select": "topic,status,priority,updated_at",
        "department": "eq.trading_intelligence",
        "status": "in.(submitted,queued,researching,needs_review,completed)",
        "order": "updated_at.desc",
        "limit": str(limit),
    })
    if not rows:
        return "No trading research tickets found."
    lines = [f"• {r.get('topic','topic')} ({r.get('status','unknown')}, {r.get('priority','normal')})" for r in rows]
    return "Trading research pipeline:\n" + "\n".join(lines)


def summarize_recent_approved_knowledge(domain: str = "trading", limit: int = 5) -> str:
    rows = _supabase_get("knowledge_items", {
        "select": "title,domain,quality_score,approved_at,status",
        "domain": f"eq.{domain}",
        "status": "eq.approved",
        "order": "approved_at.desc",
        "limit": str(limit),
    })
    if not rows:
        return "No approved knowledge found yet for this domain."
    lines = [f"• {r.get('title','')} (score {r.get('quality_score',0)})" for r in rows]
    return "Approved knowledge:\n" + "\n".join(lines)


def _handle_retrieval_query(text: str) -> str | None:
    """
    Handle pure-retrieval queries that should return existing data without creating tickets.
    Returns a formatted response string or None if not a retrieval pattern.
    """
    t = text.lower()

    # "What opportunities are Nexus validated?" / "What opportunities has Nexus researched?"
    if "opportunit" in t and any(k in t for k in ["validated", "researched", "nexus", "internal"]):
        rows = _supabase_get("user_opportunities", {
            "select": "opportunity_name,category,feasibility_score,opportunity_score,nexus_status",
            "nexus_status": "eq.validated",
            "order": "opportunity_score.desc",
            "limit": "5",
        })
        if rows:
            items = []
            for r in rows:
                name = r.get("opportunity_name", "")
                cat = r.get("category", "")
                opp_score = r.get("opportunity_score", 0)
                items.append(f"• {name} ({cat}) — score {opp_score}/100")
            return "Nexus validated opportunities:\n" + "\n".join(items)
        return "No Nexus validated opportunities found yet. Run the opportunity worker to score your profile."

    # "What grant opportunities has Nexus researched?" / "What grant research is available?"
    if "grant" in t and any(k in t for k in ["researched", "available", "internal", "what"]):
        # Check completed research tickets for grants
        rows = _supabase_get("research_requests", {
            "select": "topic,research_summary,status,completed_at",
            "department": "eq.grants_research",
            "status": "in.(completed,needs_review)",
            "order": "updated_at.desc",
            "limit": "5",
        })
        if rows:
            items = [f"• {r['topic']} ({r['status']})" for r in rows]
            return "Nexus grant research tickets:\n" + "\n".join(items)
        # Fall back to grants_catalog
        catalog = _supabase_get("grants_catalog", {
            "select": "title,grantor,amount_max,is_verified",
            "is_verified": "eq.true",
            "limit": "5",
        })
        if catalog:
            items = [f"• {r['title']} — {r.get('grantor','')}" for r in catalog]
            return "Nexus grants catalog (verified):\n" + "\n".join(items)
        return "No completed grant research yet. Ask me to find grants for a specific type of business and I'll submit it for research."

    # "What new knowledge was recently approved?"
    if any(k in t for k in ["recently approved", "new knowledge", "what knowledge", "approved knowledge"]) and "ingested" not in t and "pending" not in t and "review" not in t:
        rows = _supabase_get("knowledge_items", {
            "select": "domain,title,quality_score,approved_at",
            "status": "eq.approved",
            "order": "approved_at.desc",
            "limit": "5",
        })
        if rows:
            items = [f"• [{r.get('domain','')}] {r.get('title','')} (score: {r.get('quality_score',0)})" for r in rows]
            return "Recently approved Nexus knowledge:\n" + "\n".join(items)
        return "No approved knowledge records yet. Review the 5 proposed records in the Admin → Tickets board to activate the knowledge base."

    if "new knowledge" in t and "ingested" in t:
        rows = _supabase_get("knowledge_items", {
            "select": "title,domain,status,created_at,source_url",
            "status": "eq.proposed",
            "order": "created_at.desc",
            "limit": "8",
        })
        if rows:
            items = [f"• [{r.get('domain','general')}] {r.get('title','')}" for r in rows]
            return "Newest ingested knowledge (proposed):\n" + "\n".join(items)
        return "No newly ingested proposed knowledge found yet."

    # "What trading research is available internally?"
    if "trading videos" in t and any(k in t for k in ["ready", "review", "recently ingested", "ingested"]):
        rows = _supabase_get("transcript_queue", {
            "select": "title,source_url,status,domain,created_at,metadata",
            "domain": "eq.trading",
            "status": "in.(ready,needs_review,needs_transcript,processed)",
            "order": "created_at.desc",
            "limit": "10",
        })
        if rows:
            return "Trading video ingestion status:\n" + "\n".join(
                [f"• {r.get('title','source')} ({r.get('status','unknown')})" for r in rows]
            )
        return "No trading video transcript rows found yet."

    if "what trading videos were recently ingested" in t:
        return summarize_recent_ingestions(domain="trading", limit=10)

    if "trading" in t and any(k in t for k in ["research", "available", "internal", "what"]) and "videos" not in t:
        rows = _supabase_get("strategies_catalog", {
            "select": "name,asset_class,risk_level,ai_confidence,edge_health",
            "is_active": "eq.true",
            "order": "ai_confidence.desc",
            "limit": "5",
        })
        tickets = _supabase_get("research_requests", {
            "select": "topic,status",
            "department": "eq.trading_intelligence",
            "status": "in.(needs_review,completed)",
            "limit": "5",
        })
        lines = []
        if rows:
            strats = [f"• {r['name']} ({r.get('asset_class','')} · risk: {r.get('risk_level','')} · confidence: {r.get('ai_confidence',0)}%)" for r in rows]
            lines.append("Active strategies:\n" + "\n".join(strats))
        if tickets:
            t_items = [f"• {r['topic']} ({r['status']})" for r in tickets]
            lines.append("Trading research tickets:\n" + "\n".join(t_items))
        lines.append(summarize_transcript_topics("trading", limit=20))
        lines.append(summarize_recent_approved_knowledge("trading", limit=5))
        if lines:
            return "\n\n".join(lines)
        return "No trading strategies or research tickets in the system yet. Strategies populate as paper trading runs accumulate data."

    if "ict silver bullet" in t and any(k in t for k in ["what does nexus know", "concept", "know about", "what nexus"]):
        parts = [
            "Nexus has partial internal intelligence on ICT silver bullet concepts.",
            summarize_transcript_topics("trading", limit=20),
            summarize_pending_trading_research(limit=5),
            summarize_recent_approved_knowledge("trading", limit=5),
            "Some related research remains under review before becoming approved Nexus guidance.",
        ]
        return "\n\n".join(parts)

    if "transcript sources" in t and "pending" in t:
        rows = _supabase_get("transcript_queue", {
            "select": "title,source_url,status,created_at",
            "status": "in.(needs_transcript,failed,pending)",
            "order": "created_at.desc",
            "limit": "10",
        })
        if rows:
            return "Transcript sources pending:\n" + "\n".join(
                [f"• {r.get('title','source')} ({r.get('status','pending')})" for r in rows]
            )
        return "No pending transcript sources right now."

    if any(k in t for k in ["pending review", "pending knowledge", "knowledge is pending review"]):
        rows = _supabase_get("knowledge_items", {
            "select": "title,domain,status,quality_score",
            "status": "eq.proposed",
            "order": "created_at.desc",
            "limit": "8",
        })
        if rows:
            return "Knowledge pending review:\n" + "\n".join(
                [f"• [{r.get('domain','general')}] {r.get('title','item')} (score: {r.get('quality_score',0)})" for r in rows]
            )
        return "No proposed knowledge rows are pending review right now."

    if any(k in t for k in ["trending internally", "trending concepts", "concepts are trending"]):
        return summarize_transcript_topics("trading", limit=25)

    if any(k in t for k in ["highest quality", "highest-quality", "best sources"]):
        rows = _supabase_get("knowledge_items", {
            "select": "title,domain,quality_score,source_url,status",
            "status": "in.(approved,proposed)",
            "order": "quality_score.desc",
            "limit": "6",
        })
        if rows:
            return "Highest quality internal sources:\n" + "\n".join(
                [f"• {r.get('title','source')} ({r.get('domain','general')}, score {r.get('quality_score',0)})" for r in rows]
            )
        return "No quality-ranked sources found yet."

    if any(k in t for k in ["opportunity research is nexus validating", "opportunity research nexus validating", "validating opportunities"]):
        rows = _supabase_get("research_requests", {
            "select": "topic,status,department,priority",
            "department": "eq.business_opportunities",
            "status": "in.(submitted,queued,researching,needs_review)",
            "order": "updated_at.desc",
            "limit": "6",
        })
        if rows:
            return "Opportunity research Nexus is validating:\n" + "\n".join(
                [f"• {r.get('topic','topic')} ({r.get('status','unknown')}, {r.get('priority','normal')})" for r in rows]
            )
        return "No active opportunity validation tickets found."

    if "ingestion operations" in t or "ingestion status" in t:
        return summarize_ingestion_operations(limit=50)

    if "nitrotrades" in t and any(k in t for k in ["process", "processed", "email"]):
        rows = _supabase_get("transcript_queue", {
            "select": "title,source_url,status,created_at,metadata",
            "or": "(title.ilike.*nitrotrades*,source_url.ilike.*nitrotrades*)",
            "order": "created_at.desc",
            "limit": "10",
        })
        if rows:
            return "Nexus processed NitroTrades sources:\n" + "\n".join(
                [f"• {r.get('source_url','')} ({r.get('status','unknown')})" for r in rows]
            )
        try:
            import json
            from pathlib import Path

            state_file = Path(__file__).resolve().parent.parent / ".email_pipeline_state.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                ids = state.get("processed_message_ids") or []
                if ids:
                    return "Nexus processed knowledge emails recently, but no NitroTrades-tagged transcript row is present yet."
        except Exception:
            pass
        return "No NitroTrades ingestion rows found yet in transcript_queue."

    return None


# ── Main entry point ──────────────────────────────────────────────────────────

def nexus_knowledge_reply(text: str, user_id: str | None = None) -> str | None:
    """
    Try to answer a Telegram message from Supabase-first Nexus intelligence.

    Returns:
        str  — conversational Nexus-sourced reply (safe to send directly)
        None — not a Nexus knowledge question; caller should use LLM fallback
    """
    if not _should_intercept(text):
        return None

    # Try pure-retrieval patterns first (no ticket creation)
    retrieval = _handle_retrieval_query(text)
    if retrieval is not None:
        logger.info("hermes_supabase_first: retrieval match text=%s...", text[:60])
        return retrieval

    # Hype/scam detection — never route these through research tickets
    if detect_hype(text):
        return ("That question touches on content that Nexus flags as potentially misleading "
                "or hype-driven. Nexus only works with vetted, evidence-based intelligence. "
                "I can submit a research request to validate the claim if you'd like.")

    # Normalize: extract core research topic (strip preamble)
    core_query = _normalize_query(text)
    role = _detect_role(text)

    # Expand query with semantic synonyms (improves knowledge search recall)
    domain_for_expansion = {
        "trading_analyst": "trading",
        "grant_researcher": "grants",
        "funding_strategist": "funding",
        "business_opportunity": "business",
        "credit_coach": "credit",
    }.get(role, "")
    expanded_terms = expand_query(core_query, domain=domain_for_expansion)
    related_concepts = get_related_concepts(core_query, domain=domain_for_expansion)

    logger.info("hermes_supabase_first: role=%s core=%s expanded=%d related=%s",
                role, core_query[:50], len(expanded_terms), related_concepts[:3])

    try:
        from .research_request_service import handle_employee_query
        result = handle_employee_query(
            role=role,
            query=core_query,           # use normalized topic for dedup + knowledge search
            original_question=text,     # preserve full original for ticket record
            context={"user_id": user_id, "expanded_terms": expanded_terms[:6], "related_concepts": related_concepts},
        )
    except Exception as exc:
        logger.error("hermes_supabase_first router error: %s", exc)
        return None

    status = result.get("status", "not_found")
    confidence = result.get("confidence", 0)
    ticket = result.get("ticket")

    # High confidence — answer from internal knowledge
    if status == "found" and confidence >= 60:
        return _format_found(result, role)

    # Ticket was created or deduplicated
    if ticket:
        t_status = ticket.get("status", "")
        if t_status == "created":
            return _format_ticket_created(ticket, text)
        if t_status == "duplicate":
            return _format_ticket_duplicate(ticket, text)
        if t_status == "dry_run":
            return _format_ticket_dry_run(ticket, text)

    # Partial knowledge — share what we have with caveat
    if status == "partial" and result.get("summary"):
        return _format_partial(result, role)

    # Escalation response from handle_employee_query (suggested_response is the fallback template)
    suggested = result.get("suggested_response") or ""
    if suggested and "Nexus does not have a vetted" in suggested:
        # The router built a fallback response — use it (ticket write may have been dry-run)
        return suggested

    return None
