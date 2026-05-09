from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
import os
import hashlib


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _safe_select(path: str) -> list[dict]:
    from scripts.prelaunch_utils import rest_select

    try:
        return rest_select(path) or []
    except Exception:
        return []


def _flag(name: str, default: str = "true") -> bool:
    return (os.getenv(name, default) or default).strip().lower() in {"1", "true", "yes", "on"}


def _category_from_row(row: dict) -> str:
    text = " ".join(
        [
            str(row.get("workflow_type") or ""),
            str(row.get("summary") or ""),
            str(row.get("event_type") or ""),
        ]
    ).lower()
    if "funding" in text:
        return "funding"
    if "credit" in text:
        return "credit"
    if "grant" in text:
        return "grants"
    if "trade" in text or "signal" in text:
        return "trading"
    if "crm" in text or "client" in text:
        return "crm_client_success"
    if "workflow" in text:
        return "workflows"
    if "report" in text:
        return "reports"
    return "operations"


def _normalize(row: dict, source_type: str) -> dict[str, Any]:
    summary = str(row.get("summary") or row.get("event_type") or row.get("workflow_type") or "").strip()
    category = row.get("category") or _category_from_row(row)
    created_at = row.get("created_at")
    updated_at = row.get("updated_at") or created_at
    tags = [category, source_type]
    conf = 0.8 if summary else 0.3
    return {
        "source_type": source_type,
        "category": category,
        "created_at": created_at,
        "updated_at": updated_at,
        "confidence_score": conf,
        "relevance_tags": tags,
        "tenant_scope": "global",
        "workflow_id": row.get("id") or row.get("workflow_id"),
        "summary": summary,
        "raw_source_reference": {
            "id": row.get("id"),
            "status": row.get("status"),
            "event_type": row.get("event_type"),
            "workflow_type": row.get("workflow_type"),
        },
    }


def _source_catalog() -> dict[str, str]:
    return {
        "workflow_outputs": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&order=created_at.desc&limit=220",
        "system_events": "system_events?select=id,event_type,status,created_at,updated_at,payload&order=created_at.desc&limit=220",
        "funding_engine_outputs": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*funding*&order=created_at.desc&limit=120",
        "credit_workflow_outputs": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*credit*&order=created_at.desc&limit=120",
        "grants_research": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*grant*&order=created_at.desc&limit=120",
        "trading_research": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*trad*&order=created_at.desc&limit=120",
        "business_opportunities": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*opportunit*&order=created_at.desc&limit=120",
        "operational_memory": "system_events?select=id,event_type,status,created_at,updated_at,payload&event_type=eq.hermes_ops_memory_snapshot&order=created_at.desc&limit=60",
        "stored_reports": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&workflow_type=ilike.*report*&order=created_at.desc&limit=120",
        "ai_generated_summaries": "workflow_outputs?select=id,summary,status,workflow_type,created_at,updated_at&summary=not.is.null&order=created_at.desc&limit=220",
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = f"{row.get('source_type')}|{row.get('category')}|{str(row.get('summary') or '').lower()[:220]}"
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def suppress_duplicate_knowledge(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _dedupe(rows)


def _non_empty(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if str(r.get("summary") or "").strip()]


def _stale(rows: list[dict[str, Any]], days: int = 7) -> list[dict[str, Any]]:
    cutoff = _now() - timedelta(days=days)
    out: list[dict[str, Any]] = []
    for row in rows:
        dt = _parse_iso(row.get("updated_at") or row.get("created_at"))
        if not dt or dt < cutoff:
            out.append(row)
    return out


def detect_stale_knowledge(rows: list[dict[str, Any]], days: int = 7) -> list[dict[str, Any]]:
    if not _flag("KNOWLEDGE_STALE_DETECTION_ENABLED", "true"):
        return []
    return _stale(rows, days=days)


def _source_weight(source_type: str) -> float:
    weights = {
        "funding_engine_outputs": 1.0,
        "credit_workflow_outputs": 1.0,
        "workflow_outputs": 0.9,
        "stored_reports": 0.85,
        "system_events": 0.65,
        "operational_memory": 0.75,
        "ai_generated_summaries": 0.7,
    }
    return float(weights.get(str(source_type or ""), 0.6))


def _recency_weight(row: dict[str, Any]) -> float:
    dt = _parse_iso(str(row.get("updated_at") or row.get("created_at") or ""))
    if not dt:
        return 0.2
    age_days = max(0.0, (_now() - dt).total_seconds() / 86400.0)
    if age_days <= 1:
        return 1.0
    if age_days <= 3:
        return 0.9
    if age_days <= 7:
        return 0.75
    if age_days <= 14:
        return 0.55
    return 0.35


def _category_match_weight(row: dict[str, Any], category: str) -> float:
    return 1.0 if str(row.get("category") or "") == str(category or "") else 0.55


def _workflow_outcome_weight(row: dict[str, Any]) -> float:
    ref = row.get("raw_source_reference") or {}
    status = str(ref.get("status") or "").lower()
    if status in {"completed", "approved", "ready"}:
        return 1.0
    if status in {"failed", "error"}:
        return 0.55
    return 0.8


def rank_knowledge_results(rows: list[dict[str, Any]], category: str = "operations") -> list[dict[str, Any]]:
    if not _flag("KNOWLEDGE_SOURCE_RANKING_ENABLED", "true"):
        return rows
    ranked = []
    for row in rows:
        conf = float(row.get("confidence_score") or 0.0)
        source_w = _source_weight(str(row.get("source_type") or ""))
        recency_w = _recency_weight(row)
        category_w = _category_match_weight(row, category)
        outcome_w = _workflow_outcome_weight(row)
        stale_penalty = 0.75 if detect_stale_knowledge([row], days=10) else 1.0
        relevance_bonus = 1.0
        tags = [str(t).lower() for t in (row.get("relevance_tags") or [])]
        if category and str(category).lower() in tags:
            relevance_bonus = 1.05
        score = (0.35 * conf + 0.20 * source_w + 0.25 * recency_w + 0.10 * category_w + 0.10 * outcome_w)
        score = float(score * stale_penalty * relevance_bonus)
        out = dict(row)
        out["ranking_score"] = round(score, 4)
        ranked.append(out)
    ranked.sort(key=lambda x: float(x.get("ranking_score") or 0.0), reverse=True)
    return ranked


def explain_knowledge_ranking(row: dict[str, Any], category: str = "operations") -> dict[str, Any]:
    return {
        "source_weight": _source_weight(str(row.get("source_type") or "")),
        "recency_weight": _recency_weight(row),
        "confidence_score": float(row.get("confidence_score") or 0.0),
        "category_match_weight": _category_match_weight(row, category),
        "workflow_outcome_weight": _workflow_outcome_weight(row),
        "stale": bool(detect_stale_knowledge([row], days=10)),
    }


def get_top_ranked_knowledge(category: str = "operations", limit: int = 12, fetch_limit: int = 240) -> list[dict[str, Any]]:
    rows = get_recent_knowledge(category, limit=max(40, limit * 4), fetch_limit=fetch_limit)
    rows = suppress_duplicate_knowledge(rows)
    ranked = rank_knowledge_results(rows, category=category)
    return ranked[: max(1, int(limit))]


def build_source_aware_context_pack(category: str = "operations", limit: int = 8) -> dict[str, Any]:
    ranked = get_top_ranked_knowledge(category, limit=limit)
    source_quality: dict[str, int] = {}
    for row in ranked:
        source = str(row.get("source_type") or "unknown")
        source_quality[source] = source_quality.get(source, 0) + 1
    return {
        "category": category,
        "top_ranked": ranked,
        "source_quality_summary": source_quality,
        "stale_warnings": detect_stale_knowledge(ranked, days=10),
    }


def audit_knowledge_sources() -> dict[str, Any]:
    source_rows: dict[str, list[dict]] = {name: _safe_select(path) for name, path in _source_catalog().items()}
    normalized = []
    for source_name, rows in source_rows.items():
        normalized.extend([_normalize(row, source_name) for row in rows])
    normalized_non_empty = _non_empty(normalized)
    deduped = _dedupe(normalized_non_empty)
    categories = {
        "funding", "credit", "grants", "business_setup", "trading",
        "crm_client_success", "operations", "research", "ai_workforce", "reports", "workflows",
    }
    category_counts = {cat: 0 for cat in categories}
    for row in deduped:
        cat = str(row.get("category") or "operations")
        if cat in category_counts:
            category_counts[cat] += 1

    empty_summaries = max(0, len(normalized) - len(normalized_non_empty))
    duplicates = max(0, len(normalized_non_empty) - len(deduped))
    return {
        "knowledge_sources_discovered": [{"source": name, "rows": len(rows)} for name, rows in source_rows.items()],
        "category_counts": category_counts,
        "potential_duplicates": duplicates,
        "stale_candidates": len(_stale(deduped, days=10)),
        "empty_summary_candidates": empty_summaries,
        "normalization_mode": "retrieval_time",
        "notes": [
            "Knowledge is fragmented across workflow_outputs and system_events variants.",
            "Normalization is done at retrieval-time to avoid schema migration risk.",
            "No ingestion pipelines were removed or replaced during audit.",
        ],
    }


def get_recent_knowledge(category: str = "operations", limit: int = 20, fetch_limit: int = 240) -> list[dict[str, Any]]:
    if not _flag("KNOWLEDGE_RETRIEVAL_ENABLED", "true"):
        return []
    fetch = max(20, int(fetch_limit))
    workflow = _safe_select(f"workflow_outputs?select=id,summary,status,workflow_type,created_at&order=created_at.desc&limit={fetch}")
    events = _safe_select(f"system_events?select=id,event_type,status,created_at,payload&order=created_at.desc&limit={fetch}")
    rows = [_normalize(r, "workflow_outputs") for r in workflow] + [_normalize(r, "system_events") for r in events]
    rows = _non_empty(_dedupe(rows))
    filtered = [r for r in rows if str(r.get("category") or "") == category]
    filtered.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return filtered[: max(1, int(limit))]


def search_knowledge(query: str, limit: int = 30) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    merged = []
    for cat in [
        "funding", "credit", "grants", "business_setup", "trading",
        "crm_client_success", "operations", "research", "ai_workforce", "reports", "workflows",
    ]:
        merged.extend(get_recent_knowledge(cat, limit=18))
    out = [r for r in _dedupe(merged) if q in str(r.get("summary") or "").lower() or q in " ".join(r.get("relevance_tags") or []).lower()]
    out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return out[: max(1, int(limit))]


def get_related_workflows(category: str, limit: int = 15) -> list[dict[str, Any]]:
    rows = get_recent_knowledge(category, limit=80)
    out = []
    for row in rows:
        ref = row.get("raw_source_reference") or {}
        out.append(
            {
                "workflow_id": row.get("workflow_id"),
                "workflow_type": ref.get("workflow_type") or "unknown",
                "status": ref.get("status") or "unknown",
                "summary": row.get("summary"),
                "created_at": row.get("created_at"),
            }
        )
    return out[:limit]


def get_recent_recommendations(limit: int = 10) -> list[dict[str, Any]]:
    rows = get_recent_knowledge("operations", limit=80) + get_recent_knowledge("reports", limit=40)
    out = []
    for row in _dedupe(rows):
        summary = str(row.get("summary") or "")
        if any(k in summary.lower() for k in ["recommend", "next step", "priority", "action"]):
            out.append(row)
    return out[:limit]


def get_funding_knowledge(limit: int = 20) -> list[dict[str, Any]]:
    return get_top_ranked_knowledge("funding", limit=limit)


def get_credit_knowledge(limit: int = 20) -> list[dict[str, Any]]:
    return get_top_ranked_knowledge("credit", limit=limit)


def knowledge_dashboard_snapshot() -> dict[str, Any]:
    categories = [
        "funding", "credit", "grants", "business_setup", "trading",
        "crm_client_success", "operations", "research", "ai_workforce", "reports", "workflows",
    ]
    counts = {cat: len(get_recent_knowledge(cat, limit=60)) for cat in categories}
    recent = []
    for cat in categories:
        recent.extend(get_recent_knowledge(cat, limit=3))
    recent.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    stale = _stale(_dedupe(recent), days=7)
    top_ranked: dict[str, list[dict[str, Any]]] = {
        "funding": get_top_ranked_knowledge("funding", limit=5),
        "credit": get_top_ranked_knowledge("credit", limit=5),
        "operations": get_top_ranked_knowledge("operations", limit=5),
    }
    source_quality: dict[str, int] = {}
    for rows in top_ranked.values():
        for row in rows:
            source = str(row.get("source_type") or "unknown")
            source_quality[source] = source_quality.get(source, 0) + 1
    return {
        "categories": categories,
        "category_counts": counts,
        "latest_ingested": recent[:20],
        "stale_warnings": stale[:10],
        "top_operational_recommendations": get_recent_recommendations(limit=8),
        "recent_funding_insights": get_funding_knowledge(limit=6),
        "recent_credit_insights": get_credit_knowledge(limit=6),
        "top_ranked_knowledge": top_ranked,
        "source_quality_summary": source_quality,
    }


def build_hermes_context_pack(category: str = "operations") -> dict[str, Any]:
    """Context pack for planning and recommendation generation."""
    return {
        "recent_knowledge": get_recent_knowledge(category, limit=8),
        "recent_recommendations": get_recent_recommendations(limit=6),
        "funding_insights": get_funding_knowledge(limit=4),
        "credit_insights": get_credit_knowledge(limit=4),
    }


def build_telegram_knowledge_report_context() -> dict[str, Any]:
    funding = get_top_ranked_knowledge("funding", limit=4, fetch_limit=60)
    credit = get_top_ranked_knowledge("credit", limit=4, fetch_limit=60)
    operations = get_top_ranked_knowledge("operations", limit=4, fetch_limit=60)
    recent = suppress_duplicate_knowledge(funding + credit + operations)
    stale = detect_stale_knowledge(recent, days=10)
    return {
        "funding": funding,
        "credit": credit,
        "operations": operations,
        "stale_warnings": stale[:8],
        "source_quality_summary": {
            "workflow_outputs": len([r for r in recent if str(r.get("source_type") or "") == "workflow_outputs"]),
            "system_events": len([r for r in recent if str(r.get("source_type") or "") == "system_events"]),
        },
    }
