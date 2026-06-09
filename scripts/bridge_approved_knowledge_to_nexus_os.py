#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.prelaunch_utils import rest_select, supabase_request


BRIDGE_ACTOR = "bridge_approved_knowledge_to_nexus_os"
ALLOWED_SOURCE_TYPES = {"transcript", "article", "video", "document", "session_notes", "url", "audio"}
AFFILIATE_CAMPAIGNS = {"Nav", "LegalZoom", "Newsletter Platform (Beehiiv TBD)"}

CAMPAIGN_RULES: dict[str, dict[str, Any]] = {
    "Nav": {
        "keywords": [
            "nav", "business credit monitoring", "business financing marketplace",
            "funding prep", "funding readiness", "credit profile", "business credit",
        ],
        "aliases": ["nav"],
        "default_content": ["linkedin_post", "newsletter"],
    },
    "LegalZoom": {
        "keywords": [
            "legalzoom", "llc", "business formation", "registered agent",
            "legal docs", "formation service", "ein setup",
        ],
        "aliases": ["legalzoom"],
        "default_content": ["linkedin_post", "landing_page_copy"],
    },
    "Newsletter Platform (Beehiiv TBD)": {
        "keywords": [
            "newsletter", "beehiiv", "email list", "subscribers", "email audience",
            "newsletter platform", "creator newsletter",
        ],
        "aliases": ["newsletter", "beehiiv", "newsletter/beehiiv"],
        "default_content": ["newsletter", "landing_page_copy"],
    },
    "Business Credit Builder": {
        "keywords": [
            "business credit", "funding prep", "credit profile", "tier 1",
            "tradelines", "vendor credit", "net 30", "business funding readiness",
        ],
        "aliases": ["business credit builder", "business credit"],
        "default_content": ["linkedin_post", "youtube_short"],
    },
    "Paydex Education": {
        "keywords": [
            "paydex", "d&b", "dun & bradstreet", "vendor credit",
            "vendor accounts", "trade lines", "business credit score",
        ],
        "aliases": ["paydex education", "paydex", "d&b"],
        "default_content": ["linkedin_post", "youtube_short"],
    },
}

CONTENT_TYPE_SPECS: dict[str, dict[str, Any]] = {
    "linkedin_post": {
        "type": "linkedin_post",
        "label": "LinkedIn post",
        "platform_targets": ["LinkedIn"],
    },
    "youtube_short": {
        "type": "youtube_short",
        "label": "YouTube Short / Reel script",
        "platform_targets": ["YouTube Shorts", "Instagram Reels"],
    },
    "newsletter": {
        "type": "newsletter",
        "label": "Newsletter blurb",
        "platform_targets": ["Newsletter"],
    },
    "landing_page_copy": {
        "type": "landing_page_copy",
        "label": "Landing page CTA",
        "platform_targets": ["Landing Page"],
    },
}


@dataclass
class CampaignMatch:
    campaign_name: str | None
    confidence: str
    score: int
    reasons: list[str]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return cleaned[:64] or "insight"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _cap(text: str, size: int) -> str:
    s = (text or "").strip()
    return s if len(s) <= size else s[: size - 1].rstrip() + "…"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=True)


def _json_array(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _metadata(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _tags_from_row(row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    md = _metadata(row.get("metadata"))
    for bucket in (row.get("tags"), md.get("searchable_tags"), md.get("tags")):
        if isinstance(bucket, list):
            for item in bucket:
                if isinstance(item, str) and item.strip():
                    t = item.strip().lower()
                    if t not in tags:
                        tags.append(t)
    structured = _metadata(md.get("structured_review"))
    for bucket in (structured.get("classifications"), structured.get("tools_or_products")):
        if isinstance(bucket, list):
            for item in bucket:
                if isinstance(item, str) and item.strip():
                    t = item.strip().lower()
                    if t not in tags:
                        tags.append(t)
    return tags[:16]


def _source_excerpt(row: dict[str, Any], source_table: str) -> str:
    parts: list[str] = []
    if source_table == "knowledge_items":
        md = _metadata(row.get("metadata"))
        structured = _metadata(md.get("structured_review"))
        parts.extend(
            [
                _safe_text(row.get("content")),
                _safe_text(row.get("summary")),
                _safe_text(row.get("title")),
                _safe_text(structured.get("summary")),
                " ".join(str(x) for x in _json_array(structured.get("key_insights"))),
                " ".join(str(x) for x in _json_array(structured.get("classifications"))),
                " ".join(str(x) for x in _json_array(structured.get("content_ideas"))),
                " ".join(str(x) for x in _json_array(structured.get("tools_or_products"))),
                _safe_text(structured.get("monetization_angle")),
            ]
        )
    elif source_table == "source_extractions":
        parts.extend(
            [
                _safe_text(row.get("summary")),
                _safe_text(row.get("video_title")),
                " ".join(str(t) for t in _json_array(row.get("tags"))),
            ]
        )
    return " ".join(p for p in parts if p).strip()


def _source_title(row: dict[str, Any], source_table: str) -> str:
    if source_table == "knowledge_items":
        return _safe_text(row.get("title")) or "Approved knowledge insight"
    return _safe_text(row.get("video_title")) or _safe_text(row.get("source_id")) or "Source extraction insight"


def _source_summary(row: dict[str, Any], source_table: str) -> str:
    if source_table == "knowledge_items":
        base = _safe_text(row.get("content")) or _safe_text(row.get("title"))
    else:
        base = _safe_text(row.get("summary")) or _safe_text(row.get("video_title"))
    return _cap(re.sub(r"\s+", " ", base), 420)


def _bridge_key(source_table: str, row_id: str) -> str:
    return f"{source_table}:{row_id}"


def _source_type_for_nexus_os(row: dict[str, Any], source_table: str) -> tuple[str, str]:
    md = _metadata(row.get("metadata"))
    source_url = _safe_text(row.get("source_url"))
    source_type = _norm(_safe_text(row.get("source_type")))
    transcript_status = _norm(_safe_text(md.get("transcript_status") or md.get("transcript_state")))

    if source_table == "source_extractions":
        return "video", "youtube_insight"
    if source_type in {"youtube", "video"} and transcript_status in {"ready", "processed"}:
        return "transcript", "transcript_insight"
    if source_type == "notebooklm" or _safe_text(row.get("source_notebook")):
        return "document", "notebooklm_note"
    if source_type == "report":
        return "document", "approved_knowledge"
    if source_url.startswith("http"):
        return ("video" if "youtube." in source_url or "youtu.be" in source_url else "article"), "approved_knowledge"
    return "session_notes", "approved_knowledge"


def _entity_type(row: dict[str, Any], source_table: str, subtype: str) -> str:
    if source_table == "source_extractions":
        return "artifact"
    if subtype == "transcript_insight":
        return "transcript"
    if subtype == "notebooklm_note":
        return "lesson"
    return "source"


def _confidence(row: dict[str, Any], source_table: str) -> float | None:
    if source_table == "knowledge_items":
        raw = row.get("quality_score")
        try:
            score = float(raw)
            return round(max(0.0, min(score / 100.0, 1.0)), 3)
        except Exception:
            return None
    raw = row.get("confidence_score")
    try:
        score = float(raw)
        if score > 1.0:
            score = score / 100.0
        return round(max(0.0, min(score, 1.0)), 3)
    except Exception:
        return None


def _campaign_match(row: dict[str, Any], source_table: str) -> CampaignMatch:
    if source_table == "knowledge_items":
        md = _metadata(row.get("metadata"))
        structured = _metadata(md.get("structured_review"))
        explicit = _json_array(structured.get("classifications"))
        for label in explicit:
            if isinstance(label, str):
                exact = _campaign_alias_to_name(label)
                if exact:
                    return CampaignMatch(campaign_name=exact, confidence="high", score=99, reasons=[f"explicit_classification:{label}"])

    haystack_parts = [
        _source_title(row, source_table),
        _source_summary(row, source_table),
        _source_excerpt(row, source_table),
        " ".join(_tags_from_row(row)),
        _safe_text(row.get("source_url")),
    ]
    haystack = _norm(" ".join(haystack_parts))

    best_name: str | None = None
    best_score = 0
    reasons: list[str] = []
    for name, rule in CAMPAIGN_RULES.items():
        hits = [kw for kw in rule["keywords"] if kw in haystack]
        if len(hits) > best_score:
            best_name = name
            best_score = len(hits)
            reasons = hits[:5]

    if not best_name or best_score == 0:
        return CampaignMatch(campaign_name=None, confidence="low", score=0, reasons=[])
    if best_score >= 3:
        level = "high"
    elif best_score == 2:
        level = "medium"
    else:
        level = "low"
    return CampaignMatch(campaign_name=best_name, confidence=level, score=best_score, reasons=reasons)


def _campaign_alias_to_name(value: str | None) -> str | None:
    if not value:
        return None
    needle = _norm(value)
    for name, rule in CAMPAIGN_RULES.items():
        if _norm(name) == needle:
            return name
        for alias in rule["aliases"]:
            if _norm(alias) == needle:
                return name
    return None


def _disclosure_text(campaign_name: str | None) -> str:
    if campaign_name not in AFFILIATE_CAMPAIGNS:
        return ""
    return "Disclosure: Nexus may earn a referral commission if a reader uses an approved partner link. Educational content only."


def _content_drafts_for_campaign(campaign_name: str, source_title: str, summary: str) -> list[dict[str, Any]]:
    kinds = CAMPAIGN_RULES[campaign_name]["default_content"]
    drafts: list[dict[str, Any]] = []
    disclosure = _disclosure_text(campaign_name)
    for kind in kinds:
        spec = CONTENT_TYPE_SPECS[kind]
        title = f"{campaign_name} — {_cap(source_title, 72)} ({spec['label']})"
        body = (
            f"Source insight: {_cap(summary, 240)}\n\n"
            f"Angle: Turn this insight into a compliance-safe {spec['label'].lower()} for {campaign_name}.\n"
            f"Educational framing only. No guarantees, no earnings claims, and no approval claims.\n"
        )
        if disclosure:
            body += f"\n{disclosure}"
        drafts.append(
            {
                "title": title,
                "type": spec["type"],
                "content_type": spec["type"],
                "status": "draft",
                "platform_targets": spec["platform_targets"],
                "global_draft": body.strip(),
                "disclosure_required": bool(disclosure),
                "disclosure_added": bool(disclosure),
                "no_earnings_claims": True,
                "no_guarantees": True,
                "compliance_status": "not_reviewed",
                "approval_status": "not_required",
                "priority": "medium",
            }
        )
    return drafts


def _select_knowledge_items(limit: int, since: str | None, row_id: str | None) -> list[dict[str, Any]]:
    filters = [
        "select=id,domain,title,content,source_url,source_notebook,source_type,quality_score,quality_label,freshness_status,status,approved_at,metadata,created_at,updated_at",
        "status=eq.approved",
        "order=updated_at.desc",
        f"limit={limit}",
    ]
    if row_id:
        filters.append(f"id=eq.{row_id}")
    if since:
        filters.append(f"updated_at=gte.{since}T00:00:00Z")
    return rest_select(f"knowledge_items?{'&'.join(filters)}") or []


def _select_source_extractions(limit: int, since: str | None, row_id: str | None) -> list[dict[str, Any]]:
    filters = [
        "select=id,source_id,division,scout_id,video_id,video_title,source_url,publish_date,tier,summary,confidence_score,tags,created_at",
        "order=created_at.desc",
        f"limit={limit}",
    ]
    if row_id:
        filters.append(f"id=eq.{row_id}")
    if since:
        filters.append(f"created_at=gte.{since}T00:00:00Z")
    return rest_select(f"source_extractions?{'&'.join(filters)}") or []


def _select_campaigns() -> list[dict[str, Any]]:
    return rest_select(
        "nexus_os_revenue_campaigns?"
        "select=id,program_name,niche,priority,application_status,next_action,archived"
        "&archived=eq.false&limit=50"
    ) or []


def _select_entities_for_source_table(source_table: str) -> list[dict[str, Any]]:
    return rest_select(
        f"nexus_os_entities?select=id,name,source_table,source_id,metadata"
        f"&source_table=eq.{source_table}&limit=500"
    ) or []


def _select_campaign_entities() -> list[dict[str, Any]]:
    return rest_select(
        "nexus_os_entities?select=id,name,title,source_table,source_id"
        "&source_table=eq.nexus_os_revenue_campaigns&limit=50"
    ) or []


def _select_existing_source_rows(limit: int = 200) -> list[dict[str, Any]]:
    return rest_select(
        f"nexus_os_sources?select=id,title,content_url,summary,raw_text,created_at,updated_at&limit={limit}"
    ) or []


def _select_existing_content_rows(limit: int = 400) -> list[dict[str, Any]]:
    return rest_select(
        "nexus_os_content_items?"
        "select=id,title,related_campaign_id,source_artifact_id,content_type,status"
        f"&limit={limit}"
    ) or []


def _insert_row(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    body, _ = supabase_request(table, method="POST", body=payload, prefer="return=representation", timeout=20)
    if isinstance(body, list):
        return body[0] if body else {}
    return body or {}


def _upsert_relationship(payload: dict[str, Any]) -> dict[str, Any] | None:
    body, _ = supabase_request(
        "nexus_os_relationships?on_conflict=from_entity_id,to_entity_id,relationship",
        method="POST",
        body=payload,
        prefer="return=representation,resolution=merge-duplicates",
        timeout=20,
    )
    if isinstance(body, list):
        return body[0] if body else None
    return body or None


def _content_duplicate_key(item: dict[str, Any]) -> str:
    return f"{item.get('related_campaign_id')}|{item.get('source_artifact_id')}|{_norm(_safe_text(item.get('title')))}"


def _source_duplicate_key(item: dict[str, Any]) -> str:
    content_url = _safe_text(item.get("content_url"))
    title = _norm(_safe_text(item.get("title")))
    return f"{content_url}|{title}"


def _entity_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        st = _safe_text(row.get("source_table"))
        sid = _safe_text(row.get("source_id"))
        if st and sid:
            out[_bridge_key(st, sid)] = row
    return out


def _campaign_entity_maps(
    campaigns: list[dict[str, Any]],
    campaign_entities: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_name = {row["program_name"]: row for row in campaigns if row.get("program_name")}
    entity_by_campaign_name: dict[str, dict[str, Any]] = {}
    for ent in campaign_entities:
        sid = _safe_text(ent.get("source_id"))
        for campaign in campaigns:
            if campaign.get("id") == sid:
                entity_by_campaign_name[campaign["program_name"]] = ent
                break
    return by_name, entity_by_campaign_name


def build_bridge_plan(
    *,
    rows: list[dict[str, Any]],
    source_table: str,
    campaign_filter: str | None,
    create_content: bool,
    campaigns: list[dict[str, Any]],
    campaign_entities: list[dict[str, Any]],
    existing_source_entities: list[dict[str, Any]],
    existing_source_rows: list[dict[str, Any]],
    existing_content_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    campaign_by_name, entity_by_campaign_name = _campaign_entity_maps(campaigns, campaign_entities)
    source_entity_map = _entity_map(existing_source_entities)
    source_row_keys = {_source_duplicate_key(r) for r in existing_source_rows}
    content_keys = {_content_duplicate_key(r) for r in existing_content_rows}

    report: dict[str, Any] = {
        "source_table": source_table,
        "records_scanned": len(rows),
        "eligible_records": 0,
        "sources_to_create": [],
        "entities_to_create": [],
        "relationships_to_create": [],
        "content_to_create": [],
        "duplicates_skipped": [],
        "manual_review_needed": [],
        "failures": [],
    }

    for row in rows:
        row_id = _safe_text(row.get("id"))
        if not row_id:
            report["manual_review_needed"].append({"reason": "missing_row_id", "row": row})
            continue

        match = _campaign_match(row, source_table)
        if campaign_filter and match.campaign_name != campaign_filter:
            report["manual_review_needed"].append(
                {
                    "bridge_key": _bridge_key(source_table, row_id),
                    "title": _source_title(row, source_table),
                    "reason": "campaign_filter_mismatch",
                    "detected_campaign": match.campaign_name,
                }
            )
            continue

        bridge_key = _bridge_key(source_table, row_id)
        if bridge_key in source_entity_map:
            report["duplicates_skipped"].append(
                {
                    "bridge_key": bridge_key,
                    "reason": "existing_entity_for_original_row",
                    "entity_id": source_entity_map[bridge_key].get("id"),
                }
            )
            continue

        title = _source_title(row, source_table)
        summary = _source_summary(row, source_table)
        nexus_type, subtype = _source_type_for_nexus_os(row, source_table)
        entity_type = _entity_type(row, source_table, subtype)
        conf = _confidence(row, source_table)
        tags = _tags_from_row(row)
        md = _metadata(row.get("metadata"))
        campaign = campaign_by_name.get(match.campaign_name or "")
        campaign_entity = entity_by_campaign_name.get(match.campaign_name or "")

        source_payload = {
            "title": title,
            "type": nexus_type if nexus_type in ALLOWED_SOURCE_TYPES else "session_notes",
            "status": "summarized",
            "content_url": _safe_text(row.get("source_url")) or None,
            "raw_text": (
                f"[bridge_ref] {bridge_key}\n"
                f"[bridge_subtype] {subtype}\n"
                f"{_cap(_source_excerpt(row, source_table), 1800)}"
            ).strip(),
            "summary": summary,
            "ideas": [],
            "tags": list(dict.fromkeys(tags + [subtype, source_table, _safe_text(row.get('domain') or row.get('division'))])),
            "created_by": BRIDGE_ACTOR,
        }

        source_key = _source_duplicate_key(source_payload)
        if source_key in source_row_keys:
            report["duplicates_skipped"].append(
                {
                    "bridge_key": bridge_key,
                    "reason": "matching_source_row_exists",
                    "title": title,
                }
            )
            continue

        entity_metadata = {
            "bridge_key": bridge_key,
            "original_table": source_table,
            "original_id": row_id,
            "original_source_type": _safe_text(row.get("source_type")),
            "bridge_source_subtype": subtype,
            "source_url": _safe_text(row.get("source_url")) or None,
            "searchable_tags": tags,
            "campaign_match": {
                "campaign_name": match.campaign_name,
                "confidence": match.confidence,
                "score": match.score,
                "reasons": match.reasons,
            },
            "source_context": {
                "domain": _safe_text(row.get("domain") or md.get("ingestion_category")),
                "division": _safe_text(row.get("division")),
                "source_notebook": _safe_text(row.get("source_notebook")),
                "approved_at": _safe_text(row.get("approved_at")),
            },
        }

        entity_payload = {
            "name": title,
            "title": title,
            "type": entity_type,
            "description": summary,
            "summary": summary,
            "source_table": source_table,
            "source_id": row_id,
            "status": "active",
            "confidence": conf,
            "tags": list(dict.fromkeys(tags + [subtype])),
            "metadata": entity_metadata,
            "archived": False,
        }

        rel_payloads: list[dict[str, Any]] = []
        if campaign and campaign_entity and match.confidence in {"high", "medium"}:
            rel_payloads.append(
                {
                    "relationship": "supports",
                    "target_campaign_name": campaign["program_name"],
                    "target_campaign_id": campaign["id"],
                    "target_campaign_entity_id": campaign_entity["id"],
                    "evidence_summary": f"{title} supports {campaign['program_name']} based on matched themes: {', '.join(match.reasons[:3])}.",
                }
            )
        elif match.campaign_name and match.confidence == "low":
            report["manual_review_needed"].append(
                {
                    "bridge_key": bridge_key,
                    "title": title,
                    "reason": "low_confidence_campaign_match",
                    "detected_campaign": match.campaign_name,
                    "match_reasons": match.reasons,
                }
            )

        content_payloads: list[dict[str, Any]] = []
        if create_content and campaign and match.confidence in {"high", "medium"}:
            for draft in _content_drafts_for_campaign(campaign["program_name"], title, summary):
                payload = {
                    **draft,
                    "source_artifact_id": "__TO_FILL__",
                    "source_type": subtype,
                    "source_url": _safe_text(row.get("source_url")) or None,
                    "related_campaign_id": campaign["id"],
                    "platform_variations": [],
                    "notes": f"Bridge source: {bridge_key}",
                    "archived": False,
                    "lesson_stored": False,
                    "created_by_agent": BRIDGE_ACTOR,
                }
                if _content_duplicate_key(payload) in content_keys:
                    report["duplicates_skipped"].append(
                        {
                            "bridge_key": bridge_key,
                            "reason": "matching_content_row_exists",
                            "title": payload["title"],
                        }
                    )
                    continue
                content_payloads.append(payload)

        report["eligible_records"] += 1
        report["sources_to_create"].append({"bridge_key": bridge_key, "payload": source_payload})
        report["entities_to_create"].append({"bridge_key": bridge_key, "payload": entity_payload})
        report["relationships_to_create"].extend(
            [{"bridge_key": bridge_key, "payload": payload} for payload in rel_payloads]
        )
        report["content_to_create"].extend(
            [{"bridge_key": bridge_key, "payload": payload} for payload in content_payloads]
        )

    return report


def apply_bridge_plan(plan: dict[str, Any]) -> dict[str, Any]:
    created_sources: list[dict[str, Any]] = []
    created_entities: list[dict[str, Any]] = []
    created_relationships: list[dict[str, Any]] = []
    created_content: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    entity_id_by_bridge_key: dict[str, str] = {}
    source_id_by_bridge_key: dict[str, str] = {}

    for source_item, entity_item in zip(plan["sources_to_create"], plan["entities_to_create"]):
        bridge_key = source_item["bridge_key"]
        try:
            source_row = _insert_row("nexus_os_sources", source_item["payload"])
            source_id = _safe_text(source_row.get("id"))
            created_sources.append({"bridge_key": bridge_key, "id": source_id, "title": source_row.get("title")})
            source_id_by_bridge_key[bridge_key] = source_id

            entity_payload = dict(entity_item["payload"])
            metadata = dict(entity_payload.get("metadata") or {})
            metadata["nexus_os_source_id"] = source_id
            entity_payload["metadata"] = metadata
            entity_row = _insert_row("nexus_os_entities", entity_payload)
            entity_id = _safe_text(entity_row.get("id"))
            created_entities.append({"bridge_key": bridge_key, "id": entity_id, "name": entity_row.get("name")})
            entity_id_by_bridge_key[bridge_key] = entity_id
        except Exception as exc:
            failures.append({"bridge_key": bridge_key, "stage": "source_or_entity_create", "error": str(exc)})

    for rel_item in plan["relationships_to_create"]:
        bridge_key = rel_item["bridge_key"]
        source_entity_id = entity_id_by_bridge_key.get(bridge_key)
        target_entity_id = _safe_text(rel_item["payload"].get("target_campaign_entity_id"))
        if not source_entity_id or not target_entity_id:
            continue
        try:
            row = _upsert_relationship(
                {
                    "from_entity_id": source_entity_id,
                    "to_entity_id": target_entity_id,
                    "relationship": rel_item["payload"]["relationship"],
                    "weight": 1.0,
                    "evidence_summary": rel_item["payload"]["evidence_summary"],
                    "source_table": plan["source_table"],
                    "source_id": bridge_key.split(":", 1)[1],
                    "metadata": {"bridge_key": bridge_key},
                }
            )
            if row:
                created_relationships.append({"bridge_key": bridge_key, "id": row.get("id"), "relationship": row.get("relationship")})
        except Exception as exc:
            failures.append({"bridge_key": bridge_key, "stage": "relationship_create", "error": str(exc)})

    for content_item in plan["content_to_create"]:
        bridge_key = content_item["bridge_key"]
        source_artifact_id = source_id_by_bridge_key.get(bridge_key)
        related = next(
            (r for r in plan["relationships_to_create"] if r["bridge_key"] == bridge_key and r["payload"].get("target_campaign_id")),
            None,
        )
        if not source_artifact_id:
            continue
        payload = dict(content_item["payload"])
        payload["source_artifact_id"] = source_artifact_id
        try:
            row = _insert_row("nexus_os_content_items", payload)
            content_id = _safe_text(row.get("id"))
            created_content.append({"bridge_key": bridge_key, "id": content_id, "title": row.get("title")})

            content_entity = _insert_row(
                "nexus_os_entities",
                {
                    "name": _safe_text(row.get("title")),
                    "title": _safe_text(row.get("title")),
                    "type": "content_item",
                    "description": _cap(_safe_text(row.get("global_draft")), 400),
                    "summary": _cap(_safe_text(row.get("global_draft")), 400),
                    "source_table": "nexus_os_content_items",
                    "source_id": content_id,
                    "status": _safe_text(row.get("status")) or "draft",
                    "confidence": None,
                    "tags": [],
                    "metadata": {"bridge_key": bridge_key, "created_by": BRIDGE_ACTOR},
                    "archived": False,
                },
            )
            content_entity_id = _safe_text(content_entity.get("id"))
            if content_entity_id:
                _upsert_relationship(
                    {
                        "from_entity_id": content_entity_id,
                        "to_entity_id": entity_id_by_bridge_key[bridge_key],
                        "relationship": "generated_from_source",
                        "weight": 1.0,
                        "evidence_summary": f"Content was suggested from bridge source {bridge_key}.",
                        "source_table": "nexus_os_content_items",
                        "source_id": content_id,
                        "metadata": {"bridge_key": bridge_key},
                    }
                )
                if related and related["payload"].get("target_campaign_entity_id"):
                    _upsert_relationship(
                        {
                            "from_entity_id": content_entity_id,
                            "to_entity_id": related["payload"]["target_campaign_entity_id"],
                            "relationship": "belongs_to_campaign",
                            "weight": 1.0,
                            "evidence_summary": "Content linked to matched campaign during bridge.",
                            "source_table": "nexus_os_content_items",
                            "source_id": content_id,
                            "metadata": {"bridge_key": bridge_key},
                        }
                    )
        except Exception as exc:
            failures.append({"bridge_key": bridge_key, "stage": "content_create", "error": str(exc)})

    return {
        "created_sources": created_sources,
        "created_entities": created_entities,
        "created_relationships": created_relationships,
        "created_content": created_content,
        "failures": failures,
    }


def _print_report(plan: dict[str, Any], applied: dict[str, Any] | None) -> None:
    out = {
        "mode": "apply" if applied is not None else "dry-run",
        "source_table": plan["source_table"],
        "records_scanned": plan["records_scanned"],
        "eligible_records": plan["eligible_records"],
        "sources_would_create": len(plan["sources_to_create"]),
        "entities_would_create": len(plan["entities_to_create"]),
        "relationships_would_create": len(plan["relationships_to_create"]),
        "content_would_create": len(plan["content_to_create"]),
        "duplicates_skipped": len(plan["duplicates_skipped"]),
        "manual_review_needed": len(plan["manual_review_needed"]),
        "details": {
            "sources": plan["sources_to_create"],
            "entities": plan["entities_to_create"],
            "relationships": plan["relationships_to_create"],
            "content": plan["content_to_create"],
            "duplicates": plan["duplicates_skipped"],
            "manual_review": plan["manual_review_needed"],
            "failures": plan["failures"],
        },
    }
    if applied is not None:
        out["applied"] = applied
    print(json.dumps(out, indent=2))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Bridge approved knowledge into Nexus OS sources, graph, and optional content drafts.")
    p.add_argument("--dry-run", action="store_true", help="Preview only. This is the default mode.")
    p.add_argument("--apply", action="store_true", help="Write bridged rows to Nexus OS tables.")
    p.add_argument("--limit", type=int, default=10, help="Maximum source rows to scan.")
    p.add_argument("--source", choices=["knowledge_items", "source_extractions"], default="knowledge_items", help="Source table to bridge.")
    p.add_argument("--id", help="Optional exact source row id to bridge.")
    p.add_argument("--campaign", help="Optional campaign filter: Nav, LegalZoom, Newsletter, Business Credit Builder, Paydex Education.")
    p.add_argument("--create-content", action="store_true", help="Also create optional draft content suggestions when campaign relevance is clear.")
    p.add_argument("--since", help="Optional YYYY-MM-DD lower bound for updated_at/created_at.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.apply and args.dry_run:
        print(json.dumps({"ok": False, "error": "choose_apply_or_dry_run_not_both"}, indent=2))
        return 1

    campaign_filter = _campaign_alias_to_name(args.campaign)
    if args.campaign and not campaign_filter:
        print(json.dumps({"ok": False, "error": "unknown_campaign_filter", "campaign": args.campaign}, indent=2))
        return 1

    if args.source == "knowledge_items":
        rows = _select_knowledge_items(limit=args.limit, since=args.since, row_id=args.id)
    else:
        rows = _select_source_extractions(limit=args.limit, since=args.since, row_id=args.id)

    plan = build_bridge_plan(
        rows=rows,
        source_table=args.source,
        campaign_filter=campaign_filter,
        create_content=bool(args.create_content),
        campaigns=_select_campaigns(),
        campaign_entities=_select_campaign_entities(),
        existing_source_entities=_select_entities_for_source_table(args.source),
        existing_source_rows=_select_existing_source_rows(),
        existing_content_rows=_select_existing_content_rows(),
    )

    if not args.apply:
        _print_report(plan, applied=None)
        return 0

    applied = apply_bridge_plan(plan)
    _print_report(plan, applied=applied)
    return 0 if not applied["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
