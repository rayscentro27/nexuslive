#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib.hermes_email_knowledge_intake import _supabase_get, _supabase_post
from lib.knowledge_ingestion_ops import (
    build_searchable_tags,
    normalize_category,
    owner_for_category,
    quality_score,
    source_metadata,
    transcript_state,
)


DEFAULT_INBOX = ROOT / "inbox" / "youtube_transcripts"
ALLOWED_EXTENSIONS = {".txt", ".md"}
SECTION_HEADERS = {"title", "url", "source type", "related area", "transcript"}

CAMPAIGN_RULES: dict[str, dict[str, Any]] = {
    "Nav": {
        "keywords": ["nav", "funding readiness", "business financing marketplace", "business credit monitoring"],
        "content_ideas": ["checklist_explainer", "landing_page_cta"],
    },
    "Business Credit Builder": {
        "keywords": ["business credit", "funding prep", "credit profile", "tier 1", "tradelines", "vendor credit", "net 30"],
        "content_ideas": ["checklist_explainer", "linkedin_post", "youtube_short"],
    },
    "Paydex Education": {
        "keywords": ["paydex", "d&b", "dun & bradstreet", "vendor credit", "trade lines", "business credit score"],
        "content_ideas": ["youtube_short", "linkedin_post", "checklist_explainer"],
    },
    "LegalZoom": {
        "keywords": ["llc", "business formation", "registered agent", "legal docs", "ein setup", "legalzoom"],
        "content_ideas": ["landing_page_cta", "linkedin_post"],
    },
    "Newsletter/Beehiiv": {
        "keywords": ["newsletter", "beehiiv", "email list", "subscribers", "email audience"],
        "content_ideas": ["newsletter_blurb", "landing_page_cta"],
    },
    "Nexus OS product strategy": {
        "keywords": ["nexus", "hermes", "operating system", "agent", "workflow", "supabase", "dashboard"],
        "content_ideas": ["product_note", "internal_positioning"],
    },
    "Tool Registry": {
        "keywords": ["tool", "repo", "github", "api", "integration", "open notebook", "notebooklm", "headroom", "postiz"],
        "content_ideas": ["tool_card", "internal_note"],
    },
    "Content Studio": {
        "keywords": ["content studio", "shorts", "reels", "video script", "newsletter", "content engine", "distribution"],
        "content_ideas": ["youtube_short", "newsletter_blurb", "linkedin_post"],
    },
}

COMPLIANCE_PATTERNS = {
    "guaranteed outcome language": ["guaranteed", "guarantee", "100%"],
    "instant funding language": ["instant funding", "instant approval"],
    "credit repair risk": ["credit repair", "remove negative items", "fix your credit"],
    "no-risk claim": ["no risk", "risk-free"],
}

TOOL_KEYWORDS = [
    "supabase",
    "notebooklm",
    "open notebook",
    "headroom",
    "postiz",
    "github",
    "beehiiv",
    "nav",
    "legalzoom",
    "dun & bradstreet",
    "d&b",
]


@dataclass
class TranscriptFile:
    path: Path
    title: str
    url: str
    source_type: str
    related_area: str
    transcript: str
    sha256: str


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_") or "transcript"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _split_sentences(text: str) -> list[str]:
    raw = re.split(r"(?<=[.!?])\s+", _clean_text(text))
    return [item.strip() for item in raw if item.strip()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_structured_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("#"):
            header = stripped.lstrip("#").strip().lower()
            if header in SECTION_HEADERS:
                current = header
                sections.setdefault(current, [])
                continue
        if current is not None:
            sections[current].append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _load_transcript_file(path: Path) -> TranscriptFile:
    raw = path.read_text(encoding="utf-8")
    sections = _parse_structured_sections(raw)
    transcript = sections.get("transcript", "").strip()
    title = sections.get("title", "").strip() or path.stem.replace("_", " ").strip()
    url = sections.get("url", "").strip()
    source_type = sections.get("source type", "").strip() or "youtube_transcript"
    related_area = sections.get("related area", "").strip() or "Revenue Hub"
    if not transcript:
        transcript = raw.strip()
    return TranscriptFile(
        path=path,
        title=title,
        url=url,
        source_type=source_type,
        related_area=related_area,
        transcript=transcript,
        sha256=_sha256(path),
    )


def _domain_for_related_area(area: str, transcript: str) -> str:
    area_key = (area or "").strip().lower()
    if "revenue" in area_key:
        return "funding"
    if "content" in area_key:
        return "marketing"
    if "tool" in area_key or "hermes" in area_key or "knowledge graph" in area_key:
        return "automation"
    text = transcript.lower()
    if any(key in text for key in ("funding", "business credit", "paydex", "llc", "newsletter")):
        return "funding"
    if any(key in text for key in ("content", "distribution", "shorts", "reels")):
        return "marketing"
    return normalize_category(area_key or "general")


def _infer_campaigns(title: str, transcript: str, related_area: str) -> list[dict[str, Any]]:
    text = f"{title} {related_area} {transcript}".lower()
    matches: list[dict[str, Any]] = []
    for campaign, rule in CAMPAIGN_RULES.items():
        hits = [keyword for keyword in rule["keywords"] if keyword in text]
        if not hits:
            continue
        confidence = "high" if len(hits) >= 3 else ("medium" if len(hits) >= 2 else "low")
        matches.append(
            {
                "campaign": campaign,
                "confidence": confidence,
                "hits": hits[:6],
                "content_ideas": rule["content_ideas"],
            }
        )
    matches.sort(key=lambda item: (item["confidence"] != "high", item["confidence"] != "medium", item["campaign"]))
    return matches


def _extract_tools(text: str) -> list[str]:
    text_l = text.lower()
    found: list[str] = []
    for tool in TOOL_KEYWORDS:
        if tool in text_l and tool not in found:
            found.append(tool)
    return found[:12]


def _compliance_notes(text: str) -> list[str]:
    text_l = text.lower()
    notes: list[str] = []
    for label, patterns in COMPLIANCE_PATTERNS.items():
        if any(pattern in text_l for pattern in patterns):
            notes.append(label)
    return notes


def _recommended_next_action(campaigns: list[dict[str, Any]], tools: list[str], compliance: list[str]) -> str:
    if campaigns:
        top = campaigns[0]["campaign"]
        if top in {"Nav", "Business Credit Builder", "Paydex Education", "LegalZoom", "Newsletter/Beehiiv"}:
            return f"Queue this for revenue review against the {top} campaign."
        return f"Route this into {top} planning before revenue packaging."
    if tools:
        return "Route this into Tool Registry review for reusable infrastructure value."
    if compliance:
        return "Keep in review_pending until compliance-safe framing is confirmed."
    return "Keep in review_pending and classify manually."


def _summary_and_key_ideas(transcript: str) -> tuple[str, list[str]]:
    sentences = _split_sentences(transcript)
    summary = " ".join(sentences[:3]).strip()
    if not summary:
        summary = _clean_text(transcript[:700])
    ideas = []
    for sentence in sentences[:8]:
        trimmed = sentence.strip()
        if len(trimmed) >= 40 and trimmed not in ideas:
            ideas.append(trimmed[:220])
    return summary[:700], ideas[:5]


def _build_records(item: TranscriptFile) -> dict[str, Any]:
    summary, key_ideas = _summary_and_key_ideas(item.transcript)
    campaigns = _infer_campaigns(item.title, item.transcript, item.related_area)
    tools = _extract_tools(f"{item.title} {item.transcript}")
    compliance = _compliance_notes(f"{item.title} {item.transcript}")
    domain = _domain_for_related_area(item.related_area, item.transcript)
    source_url = item.url.strip()
    src_meta = source_metadata(source_url) if source_url else {
        "source_url": "",
        "source_type": "youtube",
        "domain": "youtube.com",
        "channel_name": "",
        "website_name": "",
    }
    status = transcript_state(item.transcript, "local_file_ingest")
    tags = build_searchable_tags(domain, "youtube", item.transcript, item.title)
    recommended_next_action = _recommended_next_action(campaigns, tools, compliance)
    campaign_names = [match["campaign"] for match in campaigns]
    content_ideas: list[str] = []
    for match in campaigns:
        for idea in match["content_ideas"]:
            if idea not in content_ideas:
                content_ideas.append(idea)
    metadata_common = {
        "ingestion_source": "local_youtube_transcript_file",
        "local_file_name": item.path.name,
        "local_file_relpath": str(item.path.relative_to(ROOT)),
        "local_file_sha256": item.sha256,
        "related_area": item.related_area,
        "campaign_candidates": campaigns,
        "content_ideas": content_ideas[:6],
        "key_ideas": key_ideas,
        "monetization_angle": campaign_names[0] if campaign_names else "",
        "risk_notes": compliance,
        "tools_or_repos": tools,
        "recommended_next_action": recommended_next_action,
    }
    transcript_payload = {
        "title": item.title,
        "source_url": src_meta["source_url"],
        "source_type": src_meta["source_type"],
        "raw_content": item.transcript,
        "cleaned_content": item.transcript,
        "extraction_notes": f"local_file={item.path.name}; sha256={item.sha256[:16]}; source=local_youtube_transcript_file",
        "quality_label": "high" if len(item.transcript) > 1500 else ("medium" if len(item.transcript) > 500 else "low"),
        "status": status,
        "domain": domain,
        "metadata": {
            **metadata_common,
            "department": owner_for_category(domain),
            "channel_name": src_meta["channel_name"],
            "website_name": src_meta["website_name"],
            "domain": src_meta["domain"],
            "ingestion_category": domain,
            "transcript_state": status,
            "searchable_tags": tags,
        },
    }
    knowledge_payload = {
        "domain": domain,
        "title": f"[Proposed] {item.title}",
        "content": summary,
        "source_url": src_meta["source_url"],
        "source_type": "youtube",
        "status": "proposed",
        "quality_score": quality_score(summary, item.transcript, "youtube"),
        "freshness_status": "fresh",
        "metadata": {
            **metadata_common,
            "review_required": True,
            "transcript_status": status,
            "channel_name": src_meta["channel_name"],
            "website_name": src_meta["website_name"],
            "domain": src_meta["domain"],
            "ingestion_category": domain,
            "searchable_tags": tags,
            "suggested_owner": owner_for_category(domain),
        },
    }
    return {
        "transcript_payload": transcript_payload,
        "knowledge_payload": knowledge_payload,
        "campaign_matches": campaign_names,
        "content_ideas": content_ideas[:6],
        "tools_or_repos": tools,
        "risk_notes": compliance,
        "recommended_next_action": recommended_next_action,
    }


def _query_rows(table: str, *, title: str, source_url: str) -> list[dict[str, Any]]:
    params = {"select": "id,title,source_url,metadata", "limit": "20"}
    if source_url:
        params["source_url"] = f"eq.{source_url}"
    else:
        params["title"] = f"eq.{title}"
    return _supabase_get(table, params)


def _row_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return 1
    return 0


def _is_duplicate(item: TranscriptFile) -> tuple[bool, str]:
    transcript_rows = _query_rows("transcript_queue", title=item.title, source_url=item.url)
    knowledge_rows = _query_rows("knowledge_items", title=f"[Proposed] {item.title}", source_url=item.url)
    for bucket_name, rows in (("transcript_queue", transcript_rows), ("knowledge_items", knowledge_rows)):
        for row in rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if metadata.get("local_file_sha256") == item.sha256:
                return True, f"{bucket_name}:matching_sha256"
            if item.url and (row.get("source_url") or "") == item.url:
                return True, f"{bucket_name}:matching_source_url"
            if not item.url and (row.get("title") or "") in {item.title, f"[Proposed] {item.title}"}:
                return True, f"{bucket_name}:matching_title"
    return False, ""


def _iter_transcript_files(inbox: Path, limit: int) -> list[Path]:
    files = [
        path for path in sorted(inbox.iterdir())
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return files[: max(0, limit)] if limit > 0 else files


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest local YouTube transcript files into transcript_queue and proposed knowledge_items.")
    parser.add_argument("--inbox", default=str(DEFAULT_INBOX), help="Folder containing local transcript .txt/.md files.")
    parser.add_argument("--limit", type=int, default=3, help="Maximum number of files to process. Default: 3.")
    parser.add_argument("--dry-run", action="store_true", help="No-op flag for explicit dry-run calls. Dry-run is already the default.")
    parser.add_argument("--apply", action="store_true", help="Write transcript_queue and knowledge_items rows.")
    args = parser.parse_args()

    inbox = Path(args.inbox).resolve()
    if not inbox.exists():
        print(_safe_json({"ok": False, "error": f"inbox_not_found: {inbox}"}))
        return 1
    if not inbox.is_dir():
        print(_safe_json({"ok": False, "error": f"inbox_not_directory: {inbox}"}))
        return 1
    if DEFAULT_INBOX not in {inbox, *inbox.parents}:
        print(_safe_json({"ok": False, "error": f"refusing_to_process_outside_canonical_inbox: {inbox}"}))
        return 1

    files = _iter_transcript_files(inbox, args.limit)
    report: dict[str, Any] = {
        "ok": True,
        "apply": bool(args.apply),
        "inbox": str(inbox),
        "files_found": len(files),
        "files_processed": 0,
        "files_skipped": 0,
        "duplicates_skipped": 0,
        "transcript_queue_rows_created": 0,
        "knowledge_items_created": 0,
        "review_items_pending": 0,
        "campaign_matches": {},
        "manual_review_needed": [],
        "processed_files": [],
        "skipped_files": [],
        "errors": [],
    }
    if not files:
        print(_safe_json(report))
        return 0

    for path in files:
        try:
            item = _load_transcript_file(path)
            duplicate, reason = _is_duplicate(item)
            if duplicate:
                report["duplicates_skipped"] += 1
                report["files_skipped"] += 1
                report["skipped_files"].append({"file": path.name, "reason": reason})
                continue
            record = _build_records(item)
            report["files_processed"] += 1
            report["review_items_pending"] += 1
            report["campaign_matches"][path.name] = record["campaign_matches"]
            report["manual_review_needed"].append(
                {
                    "file": path.name,
                    "title": item.title,
                    "recommended_next_action": record["recommended_next_action"],
                    "campaign_matches": record["campaign_matches"],
                    "risk_notes": record["risk_notes"],
                }
            )
            report["processed_files"].append(
                {
                    "file": path.name,
                    "title": item.title,
                    "source_url": item.url,
                    "related_area": item.related_area,
                    "campaign_matches": record["campaign_matches"],
                    "content_ideas": record["content_ideas"],
                    "tools_or_repos": record["tools_or_repos"],
                    "risk_notes": record["risk_notes"],
                }
            )
            if args.apply:
                inserted_t = _supabase_post("transcript_queue", record["transcript_payload"])
                inserted_k = _supabase_post("knowledge_items", record["knowledge_payload"])
                report["transcript_queue_rows_created"] += _row_count(inserted_t)
                report["knowledge_items_created"] += _row_count(inserted_k)
        except Exception as exc:
            report["ok"] = False
            report["files_skipped"] += 1
            report["errors"].append(f"{path.name}: {exc}")

    print(_safe_json(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
