"""
Unified research recommendation packet engine.

Turns scored business opportunities and trading proposals into structured
recommendation packets that Hermes can review or that downstream workers can
consume after operator approval.

Outputs land in `research_recommendations`.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

logger = logging.getLogger("RecommendationPacketEngine")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

LLM_BASE_URL = (
    os.getenv("NEXUS_LLM_BASE_URL")
    or os.getenv("OPENROUTER_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or "https://openrouter.ai/api/v1"
).rstrip("/")
LLM_API_KEY = (
    os.getenv("NEXUS_LLM_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or ""
)
LLM_MODEL = (
    os.getenv("NEXUS_LLM_MODEL")
    or os.getenv("OPENROUTER_MODEL")
    or os.getenv("OPENAI_MODEL")
    or "meta-llama/llama-3.3-70b-instruct"
)
RESEARCH_PACKET_TIMEOUT = int(os.getenv("RESEARCH_PACKET_TIMEOUT", "20"))
BUSINESS_MIN_SCORE = int(os.getenv("RESEARCH_MIN_BUSINESS_SCORE", "60"))
TRADING_MIN_CONFIDENCE = float(os.getenv("RESEARCH_MIN_TRADING_CONFIDENCE", "0.65"))
DEFAULT_LIMIT = int(os.getenv("RESEARCH_PACKET_LIMIT", "10"))


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read())


def _sb_upsert(table: str, rows: List[dict], on_conflict: str) -> List[dict]:
    deduped = list({str(row.get(on_conflict)): row for row in rows}.values())
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}",
        data=json.dumps(deduped).encode(),
        headers=_headers("resolution=merge-duplicates,return=representation"),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _chat_completions_url(base_url: str) -> str:
    if base_url.endswith("/v1") or base_url.endswith("/api/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def _safe_json_loads(text: str) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return None
    return None


def _llm_packet(prompt: str) -> Optional[dict]:
    if not LLM_API_KEY:
        return None
    body = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You convert research candidates into structured recommendation packets. "
                    "Return valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 900,
    }
    req = urllib.request.Request(
        _chat_completions_url(LLM_BASE_URL),
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=RESEARCH_PACKET_TIMEOUT) as response:
            data = json.loads(response.read())
            content = data["choices"][0]["message"]["content"]
            return _safe_json_loads(content)
    except Exception as exc:
        logger.warning("llm_packet_failed: %s", exc)
        return None


def _maybe_uuid(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        return None


def _fetch_business_candidates(limit: int) -> List[dict]:
    path = (
        "business_opportunities"
        f"?status=eq.new&score=gte.{BUSINESS_MIN_SCORE}"
        "&select=id,title,opportunity_type,niche,description,evidence_summary,monetization_hint,urgency,confidence,score,source,trace_id"
        f"&order=score.desc&limit={limit}"
    )
    try:
        rows = _sb_get(path)
        if rows:
            return rows
    except Exception as exc:
        logger.warning("business_candidate_fetch_failed: %s", exc)
    return _fetch_business_artifact_candidates(limit)


def _fetch_trading_candidates(limit: int) -> List[dict]:
    try:
        proposals = _sb_get(
            "reviewed_signal_proposals"
            "?select=id,symbol,side,timeframe,strategy_id,asset_type,entry_price,stop_loss,take_profit,ai_confidence,market_context,research_context,risk_notes,recommendation,trace_id,status"
            f"&order=created_at.desc&limit={limit * 4}"
        )
    except Exception as exc:
        logger.warning("trading_candidate_fetch_failed: %s", exc)
        return _fetch_trading_artifact_candidates(limit)

    try:
        decisions = _sb_get(
            "risk_decisions"
            "?select=proposal_id,decision,risk_score,risk_flags,rejection_reason,rr_ratio,created_at"
            "&order=created_at.desc&limit=200"
        )
    except Exception:
        decisions = []

    try:
        replay_results = _sb_get(
            "replay_results"
            "?select=proposal_id,replay_outcome,pnl_r,pnl_pct,created_at"
            "&order=created_at.desc&limit=200"
        )
    except Exception:
        replay_results = []

    latest_decision: Dict[str, dict] = {}
    for row in decisions:
        latest_decision.setdefault(str(row.get("proposal_id")), row)

    replay_by_proposal: Dict[str, List[dict]] = {}
    for row in replay_results:
        replay_by_proposal.setdefault(str(row.get("proposal_id")), []).append(row)

    candidates: List[dict] = []
    for proposal in proposals:
        confidence = float(proposal.get("ai_confidence") or 0)
        if confidence < TRADING_MIN_CONFIDENCE:
            continue
        proposal_id = str(proposal.get("id"))
        decision = latest_decision.get(proposal_id)
        if decision and decision.get("decision") == "blocked":
            continue
        proposal["risk_decision"] = decision or {}
        proposal["recent_replays"] = replay_by_proposal.get(proposal_id, [])[:5]
        candidates.append(proposal)
        if len(candidates) >= limit:
            break
    return candidates or _fetch_trading_artifact_candidates(limit)


def _artifact_score(artifact: dict) -> int:
    score = 20
    summary = str(artifact.get("summary") or "")
    content = str(artifact.get("content") or "")
    key_points = artifact.get("key_points") or []
    action_items = artifact.get("action_items") or []
    risk_warnings = artifact.get("risk_warnings") or []

    if len(summary.split()) >= 60:
        score += 20
    elif len(summary.split()) >= 25:
        score += 10
    if len(content.split()) >= 250:
        score += 15
    if len(key_points) >= 3:
        score += 20
    elif len(key_points) >= 1:
        score += 10
    if len(action_items) >= 2:
        score += 15
    elif len(action_items) >= 1:
        score += 8
    if len(risk_warnings) >= 1:
        score += 10
    return max(0, min(100, score))


def _sanitize_research_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"Kind:\s*captions\s*Language:\s*[a-z-]+\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" -:;,.")
    return value


def _is_artifact_noise(text: str) -> bool:
    lower = _sanitize_research_text(text).lower()
    if not lower:
        return True
    return any(
        marker in lower
        for marker in (
            "you have hit your chatgpt usage limit",
            "try again in",
            "usage limit",
        )
    )


def _first_sentence(text: str, fallback: str) -> str:
    text = _sanitize_research_text(text)
    if not text:
        return fallback
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    for part in parts:
        cleaned = part.strip()
        if len(cleaned) > 20:
            return cleaned[:220]
    return fallback


def _find_phrase(text: str, keywords: List[str], fallback: str) -> str:
    text = _sanitize_research_text(text)
    lower = text.lower()
    for keyword in keywords:
        idx = lower.find(keyword)
        if idx != -1:
            snippet = text[idx: idx + 180].strip()
            return _first_sentence(snippet, fallback)
    return fallback


def _clean_phrase(text: str, fallback: str) -> str:
    value = _sanitize_research_text(text)
    if not value:
        return fallback
    if len(value) > 220:
        value = value[:217].rstrip() + "..."
    return value


def _contains_any(text: str, keywords: List[str]) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def _dedupe_strings(values: List[str], limit: int = 4) -> List[str]:
    results: List[str] = []
    seen = set()
    for value in values:
        cleaned = _clean_phrase(value, "")
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        results.append(cleaned)
        if len(results) >= limit:
            break
    return results


def _strip_leading_article(text: str) -> str:
    value = _sanitize_research_text(text or "")
    return re.sub(r"^(a|an|the)\s+", "", value, flags=re.IGNORECASE)


def _hero_copy(profile: dict) -> dict:
    icp = _sanitize_research_text(profile.get("icp") or "Growth-focused operators").rstrip(".")
    offer = _sanitize_research_text(profile.get("offer") or "a focused growth offer").rstrip(".")
    offer_no_article = _strip_leading_article(offer).rstrip(".")
    pain_points = [_sanitize_research_text(x).rstrip(".") for x in (profile.get("pain_points") or []) if x]
    primary_pain = pain_points[0] if pain_points else "manual follow-up and inconsistent conversion"
    acquisition = _sanitize_research_text(profile.get("acquisition_channel") or "one repeatable acquisition channel").rstrip(".")
    headline = "Turn missed follow-up into booked calls"
    subheadline = (
        f"For {icp.lower()}, this offer fixes slow follow-up, missed leads, and messy conversion handoffs."
    )
    positioning = (
        f"A productized {offer_no_article.lower()} for {icp.lower()}, packaged to win clients and supported by {acquisition.lower()}."
    )
    return {
        "headline": _clean_phrase(headline, "Turn attention into qualified pipeline."),
        "subheadline": _clean_phrase(subheadline, "A clearer path from demand to revenue."),
        "positioning": _clean_phrase(positioning, "A focused offer with a clear ROI story."),
    }


def _extract_business_profile(row: dict) -> dict:
    summary = _sanitize_research_text(str(row.get("summary") or ""))
    content = _sanitize_research_text(str(row.get("content") or ""))
    notes = [_sanitize_research_text(x) for x in (row.get("opportunity_notes") or []) if not _is_artifact_noise(str(x))]
    points = [_sanitize_research_text(x) for x in (row.get("key_points") or []) if not _is_artifact_noise(str(x))]
    text = "\n".join([summary, content, *notes, *points])
    niche = row.get("subtheme") or row.get("topic") or "business"
    niche_label = str(niche).replace("_", " ")
    lower = text.lower()

    if _contains_any(lower, ["agency", "agencies"]):
        icp = "Small agencies and service teams that need faster lead follow-up and better CRM visibility."
    elif _contains_any(lower, ["coach", "consultant", "creator"]):
        icp = "Coaches, consultants, and creators selling high-value offers without a reliable follow-up system."
    elif _contains_any(lower, ["local business", "contractor", "med spa", "dentist"]):
        icp = "Local operators with inbound leads that are being lost because follow-up is manual or inconsistent."
    elif _contains_any(lower, ["startup", "saas", "founder"]):
        icp = "Founders with early traction who need a lean acquisition and CRM stack before hiring a full sales team."
    else:
        icp = f"Operators in the {niche_label} space who need faster growth and clearer systems."

    if _contains_any(lower, ["crm", "pipeline", "follow-up", "lead", "appointment"]):
        offer = "A done-for-you CRM automation and lead follow-up system that captures, qualifies, and nurtures inbound prospects."
    elif _contains_any(lower, ["funnel", "landing page", "sales page"]):
        offer = "A productized funnel build that pairs landing pages, automation, and conversion tracking into one launch package."
    elif _contains_any(lower, ["content", "youtube", "newsletter"]):
        offer = "A content-to-lead system that turns educational content into qualified inbound demand."
    else:
        offer = f"A focused {niche_label} offer with a clear ROI story."

    if _contains_any(lower, ["$120k", "high ticket", "premium", "retainer"]):
        pricing = "Start with a premium setup fee plus monthly optimization retainer tied to measurable pipeline growth."
    elif _contains_any(lower, ["subscription", "monthly", "recurring"]):
        pricing = "Use a monthly recurring subscription with a clear service scope and optional implementation upsell."
    else:
        pricing = "Start with a productized setup package, then add a monthly retainer for ongoing optimization and reporting."

    if _contains_any(lower, ["youtube", "content"]):
        acquisition = "Repurpose educational content into short-form clips, lead magnets, and direct outreach follow-up."
    elif _contains_any(lower, ["cold email", "outreach", "linkedin"]):
        acquisition = "Use direct outbound outreach with a concise ROI angle and a simple audit or teardown offer."
    elif _contains_any(lower, ["ads", "paid traffic"]):
        acquisition = "Launch one paid acquisition channel with tight tracking, then retarget interested visitors into booked calls."
    else:
        acquisition = "Use direct outreach plus one content-led acquisition channel to find early customers."

    proof = _dedupe_strings(
        [*points[:4], *notes[:3], _first_sentence(summary, "Research suggests there is buyer interest in this problem.")],
        limit=4,
    )

    if _contains_any(lower, ["retainer", "recurring", "subscription"]):
        profitability = "Profitability comes from charging setup fees up front, keeping delivery templated, and retaining clients on recurring optimization."
    elif _contains_any(lower, ["automation", "crm", "funnel"]):
        profitability = "Profitability improves when one implementation template can be reused across clients, reducing labor while preserving premium pricing."
    else:
        profitability = "Profitability comes from packaging a repeatable service, keeping delivery lean, and upselling follow-on work."

    pain_points = []
    if _contains_any(lower, ["crm", "lead", "follow-up"]):
        pain_points.extend([
            "Leads are arriving, but follow-up is slow or inconsistent.",
            "Prospects fall through the cracks because the CRM is underused or disorganized.",
        ])
    if _contains_any(lower, ["funnel", "conversion", "landing page"]):
        pain_points.extend([
            "Traffic does not convert because the funnel and offer are not tightly aligned.",
            "There is no clear visibility into where prospects drop off before booking or buying.",
        ])
    if _contains_any(lower, ["manual", "time", "hours", "team"]):
        pain_points.append("Too much manual work is being handled by the owner or a small team.")
    if not pain_points:
        pain_points = [
            "Growth depends on inconsistent manual processes.",
            "The current offer is not packaged clearly enough to convert quickly.",
            "There is no simple system for turning interest into booked calls or sales.",
        ]

    revenue_model = "Productized service revenue from setup fees plus recurring retainers."
    if _contains_any(lower, ["subscription", "saas"]):
        revenue_model = "Recurring subscription revenue with implementation or onboarding upsells."

    hero = _hero_copy(
        {
            "icp": icp,
            "offer": offer,
            "pain_points": pain_points,
            "acquisition_channel": acquisition,
        }
    )

    return {
        "icp": _clean_phrase(icp, f"Operators in the {niche_label} space."),
        "offer": _clean_phrase(offer, f"A focused {niche_label} offer."),
        "pricing_signal": _clean_phrase(pricing, "Simple productized pricing."),
        "acquisition_channel": _clean_phrase(acquisition, "Direct outreach."),
        "proof_points": proof,
        "profitability_driver": _clean_phrase(profitability, "Lean delivery plus repeatable revenue."),
        "pain_points": _dedupe_strings(pain_points, limit=4),
        "revenue_model": revenue_model,
        "headline": hero["headline"],
        "subheadline": hero["subheadline"],
        "positioning": hero["positioning"],
    }


def _fetch_business_artifact_candidates(limit: int) -> List[dict]:
    try:
        rows = _sb_get(
            "research_artifacts"
            "?select=id,title,topic,subtheme,summary,content,key_points,action_items,risk_warnings,opportunity_notes,source,trace_id,created_at"
            "&topic=in.(business_opportunities,crm_automation,general_business_intelligence)"
            f"&order=created_at.desc&limit={limit * 3}"
        )
    except Exception as exc:
        logger.warning("business_artifact_fetch_failed: %s", exc)
        return []

    candidates: List[dict] = []
    for row in rows:
        if _is_artifact_noise(row.get("summary") or ""):
            continue
        row["summary"] = _sanitize_research_text(row.get("summary") or "")
        row["key_points"] = [
            _sanitize_research_text(x)
            for x in (row.get("key_points") or [])
            if not _is_artifact_noise(str(x))
        ]
        row["opportunity_notes"] = [
            _sanitize_research_text(x)
            for x in (row.get("opportunity_notes") or [])
            if not _is_artifact_noise(str(x))
        ]
        score = _artifact_score(row)
        if score < BUSINESS_MIN_SCORE:
            continue
        candidates.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "opportunity_type": row.get("subtheme") or "other",
                "niche": row.get("subtheme") or row.get("topic"),
                "description": row.get("summary"),
                "evidence_summary": "; ".join((row.get("key_points") or [])[:3]),
                "monetization_hint": "; ".join((row.get("opportunity_notes") or [])[:2]) or "Service or product monetization",
                "urgency": "medium",
                "confidence": round(score / 100, 3),
                "score": score,
                "source": row.get("source"),
                "trace_id": row.get("trace_id"),
                "business_profile": _extract_business_profile(row),
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def _fetch_trading_artifact_candidates(limit: int) -> List[dict]:
    try:
        rows = _sb_get(
            "research_artifacts"
            "?select=id,title,topic,subtheme,summary,content,key_points,action_items,risk_warnings,opportunity_notes,source,trace_id,created_at"
            "&topic=eq.trading"
            f"&order=created_at.desc&limit={limit * 3}"
        )
    except Exception as exc:
        logger.warning("trading_artifact_fetch_failed: %s", exc)
        return []

    candidates: List[dict] = []
    for row in rows:
        if _is_artifact_noise(row.get("summary") or ""):
            continue
        row["summary"] = _sanitize_research_text(row.get("summary") or "")
        row["key_points"] = [
            _sanitize_research_text(x)
            for x in (row.get("key_points") or [])
            if not _is_artifact_noise(str(x))
        ]
        row["risk_warnings"] = [
            _sanitize_research_text(x)
            for x in (row.get("risk_warnings") or [])
            if not _is_artifact_noise(str(x))
        ]
        score = _artifact_score(row)
        confidence = round(score / 100, 3)
        if confidence < TRADING_MIN_CONFIDENCE:
            continue
        candidates.append(
            {
                "id": row.get("id"),
                "symbol": row.get("subtheme") or "research_candidate",
                "side": "research",
                "timeframe": "multi",
                "strategy_id": row.get("title"),
                "asset_type": row.get("subtheme") or "trading",
                "ai_confidence": confidence,
                "market_context": row.get("summary"),
                "research_context": row.get("content"),
                "risk_notes": "; ".join((row.get("risk_warnings") or [])[:3]),
                "trace_id": row.get("trace_id"),
                "risk_decision": {
                    "decision": "review",
                    "risk_score": score,
                    "risk_flags": row.get("risk_warnings") or [],
                },
                "recent_replays": [],
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def _business_prompt(candidate: dict) -> str:
    profile = candidate.get("business_profile") or {}
    return (
        "Convert this business opportunity into a structured recommendation packet.\n\n"
        f"Title: {candidate.get('title')}\n"
        f"Type: {candidate.get('opportunity_type')}\n"
        f"Niche: {candidate.get('niche')}\n"
        f"Score: {candidate.get('score')}/100\n"
        f"Confidence: {candidate.get('confidence')}\n"
        f"Urgency: {candidate.get('urgency')}\n"
        f"Description: {candidate.get('description')}\n"
        f"Evidence: {candidate.get('evidence_summary')}\n"
        f"Monetization: {candidate.get('monetization_hint')}\n\n"
        f"ICP: {profile.get('icp')}\n"
        f"Offer: {profile.get('offer')}\n"
        f"Pricing Signal: {profile.get('pricing_signal')}\n"
        f"Acquisition Channel: {profile.get('acquisition_channel')}\n"
        f"Proof Points: {json.dumps(profile.get('proof_points') or [], ensure_ascii=True)}\n\n"
        "Return JSON with keys: recommendation, summary, thesis, execution_plan, "
        "profitability_path, backend_handoff, icp, offer, pricing_model, acquisition_channel, proof_points, pain_points, revenue_model, headline, subheadline, positioning."
    )


def _trading_prompt(candidate: dict) -> str:
    return (
        "Convert this trading idea into a structured recommendation packet.\n\n"
        f"Symbol: {candidate.get('symbol')}\n"
        f"Side: {candidate.get('side')}\n"
        f"Timeframe: {candidate.get('timeframe')}\n"
        f"Asset Type: {candidate.get('asset_type')}\n"
        f"Strategy ID: {candidate.get('strategy_id')}\n"
        f"AI Confidence: {candidate.get('ai_confidence')}\n"
        f"Market Context: {candidate.get('market_context')}\n"
        f"Research Context: {candidate.get('research_context')}\n"
        f"Risk Notes: {candidate.get('risk_notes')}\n"
        f"Risk Decision: {json.dumps(candidate.get('risk_decision') or {}, ensure_ascii=True)}\n"
        f"Replay Results: {json.dumps(candidate.get('recent_replays') or [], ensure_ascii=True)}\n\n"
        "Return JSON with keys: recommendation, summary, thesis, execution_plan, "
        "profitability_path, backend_handoff."
    )


def _fallback_business_packet(candidate: dict) -> dict:
    score = int(candidate.get("score") or 0)
    rec = "approve" if score >= 80 else ("review" if score >= 60 else "reject")
    niche = candidate.get("niche") or "general market"
    monetization = candidate.get("monetization_hint") or "customer revenue"
    profile = candidate.get("business_profile") or {}
    icp = profile.get("icp") or f"Operators in the {str(niche).replace('_', ' ')} market."
    offer = profile.get("offer") or f"A productized {str(niche).replace('_', ' ')} service."
    pricing = profile.get("pricing_signal") or "A simple monthly retainer or fixed implementation package."
    acquisition = profile.get("acquisition_channel") or "Direct outreach plus one repeatable content channel."
    proof_points = profile.get("proof_points") or [candidate.get("evidence_summary") or "Research indicates buyer demand."]
    pain_points = profile.get("pain_points") or [
        "Growth depends on inconsistent manual processes.",
        "Leads are not being converted through a clear system.",
        "The current offer is too vague to scale predictably.",
    ]
    revenue_model = profile.get("revenue_model") or "Productized service revenue with recurring retainers."
    headline = profile.get("headline") or "Turn attention into qualified pipeline."
    subheadline = profile.get("subheadline") or "A cleaner offer and follow-up system can convert more demand into revenue."
    positioning = profile.get("positioning") or "A focused service offer with clearer positioning and stronger conversion mechanics."
    profitability = profile.get("profitability_driver") or (
        "Profitability improves by standardizing delivery, charging for implementation, and keeping one repeatable acquisition channel active."
    )
    return {
        "recommendation": rec,
        "summary": (
            f"{headline}. {subheadline}"
        ),
        "thesis": (
            f"{positioning} It is most compelling for {icp.lower()} and monetizes through {revenue_model.lower()}"
        ),
        "execution_plan": [
            f"Interview 5-10 prospects who match this ICP: {icp}",
            f"Package the offer as: {offer}",
            f"Test a pricing structure such as: {pricing}",
            f"Launch with this first channel: {acquisition}",
        ],
        "profitability_path": profitability,
        "backend_handoff": [
            f"Create landing page copy for this offer: {offer}",
            f"Add proof sections from these points: {'; '.join(proof_points[:3])}",
            f"Connect lead capture to support this channel: {acquisition}",
        ],
        "icp": icp,
        "offer": offer,
        "pricing_model": pricing,
        "acquisition_channel": acquisition,
        "proof_points": proof_points[:4],
        "pain_points": pain_points[:4],
        "revenue_model": revenue_model,
        "headline": headline,
        "subheadline": subheadline,
        "positioning": positioning,
    }


def _fallback_trading_packet(candidate: dict) -> dict:
    confidence = float(candidate.get("ai_confidence") or 0)
    risk_decision = (candidate.get("risk_decision") or {}).get("decision") or "review"
    replay_count = len(candidate.get("recent_replays") or [])
    rec = "approve" if risk_decision == "approved" and confidence >= 0.8 else "review"
    return {
        "recommendation": rec,
        "summary": (
            f"{candidate.get('symbol')} {candidate.get('side')} on {candidate.get('timeframe')} has confidence {confidence:.2f} "
            f"with risk state {risk_decision} and {replay_count} replay datapoint(s)."
        ),
        "thesis": (
            "The setup is strongest when analyst confidence, risk review, and replay evidence point in the same direction."
        ),
        "execution_plan": [
            "Confirm the latest risk decision and replay evidence.",
            "Check paper-trading readiness before promotion.",
            "Promote only if replay-backed and not manually blocked.",
        ],
        "profitability_path": (
            "Profitability depends on repeatable paper-trading results, risk discipline, and only promoting setups that stay calibrated in replay."
        ),
        "backend_handoff": [
            "Create paper-trader submission payload.",
            "Attach risk and replay evidence to the execution record.",
            "Queue for scheduler or manual operator approval.",
        ],
    }


def _build_packet(domain: str, candidate: dict) -> dict:
    llm_result: Optional[dict]
    if domain == "business":
        llm_result = _llm_packet(_business_prompt(candidate))
        fallback = _fallback_business_packet(candidate)
    else:
        llm_result = _llm_packet(_trading_prompt(candidate))
        fallback = _fallback_trading_packet(candidate)

    packet = llm_result if isinstance(llm_result, dict) else fallback
    packet.setdefault("recommendation", fallback["recommendation"])
    packet.setdefault("summary", fallback["summary"])
    packet.setdefault("thesis", fallback["thesis"])
    packet.setdefault("execution_plan", fallback["execution_plan"])
    packet.setdefault("profitability_path", fallback["profitability_path"])
    packet.setdefault("backend_handoff", fallback["backend_handoff"])
    return packet


def _candidate_to_row(domain: str, candidate: dict) -> dict:
    packet = _build_packet(domain, candidate)
    raw_source_id = candidate.get("id")
    source_id = _maybe_uuid(raw_source_id)
    title = candidate.get("title") or f"{candidate.get('symbol')} {candidate.get('side')}"
    category = candidate.get("opportunity_type") if domain == "business" else candidate.get("asset_type")
    metadata = {
        "original_source_id": raw_source_id,
        "source": candidate.get("source"),
        "niche": candidate.get("niche"),
        "strategy_id": candidate.get("strategy_id"),
        "risk_decision": candidate.get("risk_decision"),
        "recent_replays": candidate.get("recent_replays"),
        "icp": packet.get("icp") or (candidate.get("business_profile") or {}).get("icp"),
        "offer": packet.get("offer") or (candidate.get("business_profile") or {}).get("offer"),
        "pricing_model": packet.get("pricing_model") or (candidate.get("business_profile") or {}).get("pricing_signal"),
        "acquisition_channel": packet.get("acquisition_channel") or (candidate.get("business_profile") or {}).get("acquisition_channel"),
        "proof_points": packet.get("proof_points") or (candidate.get("business_profile") or {}).get("proof_points"),
        "pain_points": packet.get("pain_points") or (candidate.get("business_profile") or {}).get("pain_points"),
        "revenue_model": packet.get("revenue_model") or (candidate.get("business_profile") or {}).get("revenue_model"),
        "headline": packet.get("headline") or (candidate.get("business_profile") or {}).get("headline"),
        "subheadline": packet.get("subheadline") or (candidate.get("business_profile") or {}).get("subheadline"),
        "positioning": packet.get("positioning") or (candidate.get("business_profile") or {}).get("positioning"),
    }
    deterministic_source = source_id or str(raw_source_id) or title
    return {
        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{domain}:{deterministic_source}")),
        "source_table": "business_opportunities" if domain == "business" else "reviewed_signal_proposals",
        "source_id": source_id,
        "domain": domain,
        "category": category,
        "title": title,
        "score": candidate.get("score") or (candidate.get("risk_decision") or {}).get("risk_score"),
        "confidence": candidate.get("confidence") or candidate.get("ai_confidence"),
        "recommendation": packet["recommendation"],
        "summary": packet["summary"],
        "thesis": packet["thesis"],
        "execution_plan": packet["execution_plan"],
        "profitability_path": packet["profitability_path"],
        "backend_handoff": packet["backend_handoff"],
        "approval_status": "pending",
        "metadata": metadata,
        "trace_id": candidate.get("trace_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def run(limit: int = DEFAULT_LIMIT, domains: Optional[List[str]] = None) -> Dict[str, Any]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    domains = domains or ["business", "trading"]
    rows: List[dict] = []

    if "business" in domains:
        for candidate in _fetch_business_candidates(limit):
            rows.append(_candidate_to_row("business", candidate))

    if "trading" in domains:
        for candidate in _fetch_trading_candidates(limit):
            rows.append(_candidate_to_row("trading", candidate))

    if not rows:
        return {"inserted": 0, "domains": domains, "message": "No qualifying candidates found."}

    inserted = _sb_upsert("research_recommendations", rows, "id")
    return {
        "inserted": len(inserted),
        "domains": domains,
        "titles": [row.get("title") for row in inserted[:10]],
    }


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--domain", action="append", choices=["business", "trading"])
    args = parser.parse_args()
    print(json.dumps(run(limit=args.limit, domains=args.domain), indent=2))
