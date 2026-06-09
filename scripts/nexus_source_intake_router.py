#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.hermes_email_knowledge_intake import _supabase_post, ingest_email_to_transcript_queue, parse_knowledge_email
from lib.notebooklm_ingest_adapter import (
    _build_transcript_rows as notebooklm_build_transcript_rows,
    _existing_dedup_keys as notebooklm_existing_dedup_keys,
    _supabase_post as notebooklm_supabase_post,
    build_proposed_record as notebooklm_build_proposed_record,
)
from lib.youtube_source_registry import find_by_url, register_source
from scripts.ingest_local_youtube_transcripts_once import (
    _build_records as build_local_transcript_records,
    _is_duplicate as local_transcript_duplicate,
    _load_transcript_file as load_local_transcript_file,
    _row_count as local_row_count,
)


INBOX_DIR = ROOT / "inbox" / "youtube_transcripts"
DOCS_DEFAULT = ROOT / "docs" / "nexus_source_intake.md"
TYPE_CHOICES = [
    "auto",
    "youtube_video",
    "youtube_channel",
    "youtube_playlist",
    "notebooklm_export",
    "email_body",
    "transcript_file",
    "repo_link",
    "article_link",
]
CAMPAIGN_CHOICES = [
    "auto",
    "Nav",
    "Business Credit Builder",
    "Paydex Education",
    "LegalZoom",
    "Newsletter",
    "Nexus OS Strategy",
]
URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
YOUTUBE_VIDEO_RE = re.compile(r"https?://(?:www\.)?(?:youtube\.com/watch\?[^#\s]*v=[\w-]{6,}|youtu\.be/[\w-]{6,})", re.I)
YOUTUBE_CHANNEL_RE = re.compile(r"https?://(?:www\.)?youtube\.com/(?:@[\w.-]+|channel/[\w-]+|c/[\w-]+)", re.I)
YOUTUBE_PLAYLIST_RE = re.compile(r"https?://(?:www\.)?youtube\.com/.*[?&]list=[\w-]+", re.I)
GITHUB_REPO_RE = re.compile(r"https?://github\.com/[\w.-]+/[\w.-]+/?$", re.I)


CAMPAIGN_KEYWORDS: dict[str, list[str]] = {
    "Nav": ["nav", "funding readiness", "business financing marketplace", "business credit monitoring"],
    "Business Credit Builder": ["business credit", "funding prep", "credit profile", "tier 1", "tradelines", "net 30", "vendor credit"],
    "Paydex Education": ["paydex", "d&b", "dun & bradstreet", "vendor credit", "trade lines", "business credit score"],
    "LegalZoom": ["llc", "business formation", "registered agent", "ein setup", "legal docs", "legalzoom"],
    "Newsletter": ["newsletter", "beehiiv", "email list", "subscribers", "email audience"],
    "Nexus OS Strategy": ["nexus", "hermes", "operating system", "tool registry", "content studio", "knowledge graph", "supabase"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _urls(text: str) -> list[str]:
    seen: list[str] = []
    for match in URL_RE.findall(text or ""):
        cleaned = match.rstrip('.,;:!?)"]}\'')
        if cleaned not in seen:
            seen.append(cleaned)
    return seen


def _detect_type(raw_input: str, file_path: Path | None, explicit: str) -> str:
    if explicit != "auto":
        return explicit
    if file_path is not None:
        name = file_path.name.lower()
        if "notebooklm" in name or "notebook" in name:
            return "notebooklm_export"
        return "transcript_file"

    if YOUTUBE_PLAYLIST_RE.search(raw_input):
        return "youtube_playlist"
    if YOUTUBE_CHANNEL_RE.search(raw_input):
        return "youtube_channel"
    if YOUTUBE_VIDEO_RE.search(raw_input):
        return "youtube_video"
    if GITHUB_REPO_RE.search(raw_input):
        return "repo_link"
    if URL_RE.search(raw_input):
        return "article_link"
    if "youtube.com" in raw_input.lower() or "youtu.be" in raw_input.lower():
        return "email_body"
    if raw_input.strip():
        return "email_body"
    return "auto"


def _infer_campaign(text: str, requested: str) -> str:
    if requested != "auto":
        return requested
    lower = text.lower()
    best_name = "auto"
    best_hits = 0
    for name, keywords in CAMPAIGN_KEYWORDS.items():
        hits = sum(1 for keyword in keywords if keyword in lower)
        if hits > best_hits:
            best_name = name
            best_hits = hits
    return best_name


def _category_for_campaign(campaign: str, raw_text: str) -> str:
    if campaign in {"Nav", "Business Credit Builder", "Paydex Education"}:
        return "funding"
    if campaign == "LegalZoom":
        return "business_setup"
    if campaign == "Newsletter":
        return "marketing"
    if campaign == "Nexus OS Strategy":
        return "operations"
    text = raw_text.lower()
    if any(key in text for key in ("business credit", "funding", "paydex", "lender")):
        return "funding"
    if any(key in text for key in ("newsletter", "beehiiv", "content", "landing page")):
        return "marketing"
    if any(key in text for key in ("llc", "registered agent", "legal docs")):
        return "business_setup"
    if any(key in text for key in ("nexus", "hermes", "tool", "repo", "supabase")):
        return "operations"
    return "operations"


def _email_subject(category: str, has_youtube: bool) -> str:
    prefix = "youtube" if has_youtube else "website"
    mapping = {
        "funding": f"funding {prefix} business credit",
        "business_setup": f"businessopps {prefix} ai automation",
        "marketing": f"marketing {prefix} funnel",
        "credit": f"credit {prefix} tradelines",
        "trading": f"trading {prefix} strategy",
        "operations": f"operations {prefix} workflow",
    }
    return mapping.get(category, f"operations {prefix} workflow")


def _bridge_commands(limit: int = 10) -> dict[str, str]:
    return {
        "bridge_dry_run": f"python3 scripts/bridge_approved_knowledge_to_nexus_os.py --dry-run --source knowledge_items --limit {limit}",
        "bridge_apply_after_approval": "python3 scripts/bridge_approved_knowledge_to_nexus_os.py --apply --source knowledge_items --limit 3",
    }


def _review_handoff() -> dict[str, Any]:
    return {
        "review_queue": "knowledge_items where status='proposed' or review_required=true",
        "bridge": _bridge_commands(),
    }


def _route_video(url: str, *, apply: bool, campaign: str, limit: int) -> dict[str, Any]:
    category = _category_for_campaign(campaign, url)
    body = f"{url}\n\nCategory: {category}\nCampaign: {campaign}"
    parsed = parse_knowledge_email(
        sender="Source Intake Router <router@nexus.local>",
        subject=_email_subject(category, has_youtube=True),
        body=body,
        message_id=f"<source-router-{_sha(url)}>",
    )
    result = ingest_email_to_transcript_queue(parsed, apply=apply, max_channel_videos=1)
    return {
        "ok": bool(result.get("ok")),
        "route": "youtube_video -> transcript_queue + knowledge_items (existing email intake logic)",
        "type": "youtube_video",
        "input": url,
        "campaign": campaign,
        "writes_to": ["transcript_queue", "knowledge_items"] if apply else [],
        "result": result,
        "review": _review_handoff(),
        "next_safe_command": f"python3 scripts/nexus_source_intake_router.py --input \"{url}\" --type youtube_video --apply",
        "bridge": _bridge_commands(limit),
    }


def _route_email_body(text: str, *, apply: bool, campaign: str, limit: int) -> dict[str, Any]:
    category = _category_for_campaign(campaign, text)
    parsed = parse_knowledge_email(
        sender="Source Intake Router <router@nexus.local>",
        subject=_email_subject(category, has_youtube="youtube" in text.lower() or "youtu.be" in text.lower()),
        body=text,
        message_id=f"<source-router-email-{_sha(text)}>",
    )
    result = ingest_email_to_transcript_queue(parsed, apply=apply, max_channel_videos=max(1, min(limit, 10)))
    return {
        "ok": bool(result.get("ok")),
        "route": "email_body -> transcript_queue + knowledge_items (existing email intake logic)",
        "type": "email_body",
        "campaign": campaign,
        "writes_to": ["transcript_queue", "knowledge_items"] if apply else [],
        "result": result,
        "review": _review_handoff(),
        "email_restore_command": "python3 scripts/process_knowledge_emails_once.py --dry-run",
        "bridge": _bridge_commands(limit),
    }


def _route_youtube_channel(url: str, *, apply: bool, campaign: str) -> dict[str, Any]:
    existing = find_by_url(url)
    record = existing.to_dict() if existing else None
    if apply and existing is None:
        created = register_source(
            url=url,
            source_type="channel",
            submitted_by="source_intake_router",
            notes="Registered via nexus_source_intake_router",
        )
        record = created.to_dict()
    return {
        "ok": True,
        "route": "youtube_channel -> source_registry + intelligence review lane",
        "type": "youtube_channel",
        "campaign": campaign,
        "writes_to": ["docs/reports/youtube/source_registry.json"] if apply and existing is None else [],
        "existing": existing is not None,
        "record": record,
        "next_safe_commands": [
            f"python3 scripts/run_youtube_intelligence_cycle.py --url \"{url}\" --dry-run",
            f"python3 scripts/nexus_source_intake_router.py --input \"{url}\" --type youtube_channel --apply",
        ],
        "notes": [
            "Channel links are registered for review only.",
            "The router does not ingest the full channel automatically.",
        ],
    }


def _route_youtube_playlist(url: str, *, apply: bool, campaign: str, limit: int) -> dict[str, Any]:
    existing = find_by_url(url)
    record = existing.to_dict() if existing else None
    if apply and existing is None:
        created = register_source(
            url=url,
            source_type="playlist",
            submitted_by="source_intake_router",
            notes="Playlist registered via nexus_source_intake_router",
        )
        record = created.to_dict()
    return {
        "ok": True,
        "route": "youtube_playlist -> playlist review lane",
        "type": "youtube_playlist",
        "campaign": campaign,
        "writes_to": ["docs/reports/youtube/source_registry.json"] if apply and existing is None else [],
        "existing": existing is not None,
        "record": record,
        "notes": [
            "The current playlist path is review-first.",
            "Mass ingestion is not performed automatically from the router.",
        ],
        "next_safe_commands": [
            f"python3 scripts/nexus_source_intake_router.py --input \"{url}\" --type youtube_playlist --apply --limit {limit}",
            "python3 scripts/run_youtube_intelligence_cycle.py --all --dry-run",
        ],
    }


def _parse_notebook_export(text: str, file_path: Path | None, campaign: str) -> dict[str, Any]:
    urls = _urls(text)
    notebook_name = ""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            notebook_name = stripped[:120]
            break
    if not notebook_name:
        notebook_name = file_path.stem.replace("_", " ").strip() if file_path else "NotebookLM Export"
    non_empty = [line.strip() for line in text.splitlines() if line.strip()]
    summary = "\n".join(non_empty[:8])[:2400]
    if not summary:
        summary = "NotebookLM export text pending review."
    insights = []
    for line in non_empty:
        cleaned = line.lstrip("-* ").strip()
        if len(cleaned) >= 20 and cleaned not in insights:
            insights.append(cleaned[:220])
        if len(insights) >= 8:
            break
    domain = _category_for_campaign(campaign, text)
    return {
        "notebook_name": notebook_name,
        "domain": domain,
        "summary": summary,
        "source_urls": urls,
        "source_count": len(urls),
        "insights": insights,
        "created_at": _now(),
        "updated_at": _now(),
        "dry_run": True,
    }


def _route_notebooklm_export(text: str, *, file_path: Path | None, apply: bool, campaign: str) -> dict[str, Any]:
    note = _parse_notebook_export(text, file_path, campaign)
    proposed = notebooklm_build_proposed_record(note)
    dedup_key = str((proposed.get("metadata") or {}).get("dedup_key") or "")
    duplicates = 0
    inserted_knowledge = 0
    inserted_transcripts = 0
    errors: list[str] = []
    if apply:
        try:
            if dedup_key and dedup_key in notebooklm_existing_dedup_keys():
                duplicates += 1
            else:
                inserted_knowledge = len(notebooklm_supabase_post("knowledge_items", [proposed]))
                sources = [{"url": url} for url in note.get("source_urls") or []]
                transcript_rows = notebooklm_build_transcript_rows(note["notebook_name"], note["domain"], sources)
                if transcript_rows:
                    inserted_transcripts = len(notebooklm_supabase_post("transcript_queue", transcript_rows))
        except Exception as exc:
            errors.append(str(exc))
    return {
        "ok": not errors,
        "route": "notebooklm_export -> notebooklm ingest adapter",
        "type": "notebooklm_export",
        "campaign": campaign,
        "writes_to": ["knowledge_items", "transcript_queue"] if apply else [],
        "duplicates": duplicates,
        "knowledge_rows_inserted": inserted_knowledge,
        "transcript_rows_inserted": inserted_transcripts,
        "proposed_record": proposed,
        "next_safe_commands": [
            "python3 scripts/nexus_notebooklm_ops.py status --pending-review",
            "python3 scripts/bridge_approved_knowledge_to_nexus_os.py --dry-run --source knowledge_items --limit 10",
        ],
        "errors": errors,
    }


def _route_transcript_file(path: Path, *, apply: bool, campaign: str) -> dict[str, Any]:
    item = load_local_transcript_file(path)
    duplicate = False
    reason = ""
    duplicate_check_error = ""
    try:
        duplicate, reason = local_transcript_duplicate(item)
    except Exception as exc:
        duplicate_check_error = str(exc)
    record = build_local_transcript_records(item)
    if campaign != "auto":
        for bucket in ("transcript_payload", "knowledge_payload"):
            metadata = record[bucket].setdefault("metadata", {})
            metadata["campaign_hint"] = campaign
    transcript_rows_created = 0
    knowledge_items_created = 0
    errors: list[str] = []
    if apply and not duplicate:
        try:
            transcript_rows_created = local_row_count(_supabase_post("transcript_queue", record["transcript_payload"]))
            knowledge_items_created = local_row_count(_supabase_post("knowledge_items", record["knowledge_payload"]))
        except Exception as exc:
            errors.append(str(exc))
    return {
        "ok": not errors,
        "route": "local transcript file -> transcript_queue + proposed knowledge_items",
        "type": "transcript_file",
        "campaign": campaign,
        "file": str(path),
        "duplicate": duplicate,
        "duplicate_reason": reason,
        "duplicate_check_error": duplicate_check_error,
        "writes_to": ["transcript_queue", "knowledge_items"] if apply and not duplicate else [],
        "transcript_queue_rows_created": transcript_rows_created,
        "knowledge_items_created": knowledge_items_created,
        "preview": {
            "title": item.title,
            "source_url": item.url,
            "related_area": item.related_area,
            "campaign_matches": record["campaign_matches"],
            "content_ideas": record["content_ideas"],
            "risk_notes": record["risk_notes"],
        },
        "review": _review_handoff(),
        "errors": errors,
    }


def _route_article_or_repo(raw_input: str, *, input_type: str, campaign: str) -> dict[str, Any]:
    urls = _urls(raw_input)
    url = urls[0] if urls else raw_input.strip()
    campaign_match = _infer_campaign(raw_input, campaign)
    return {
        "ok": True,
        "route": f"{input_type} -> source candidate only",
        "type": input_type,
        "campaign": campaign_match,
        "writes_to": [],
        "candidate": {
            "url": url,
            "campaign_hint": campaign_match,
            "lane": "tool_registry" if input_type == "repo_link" else "source_review",
            "status": "review_pending",
        },
        "notes": [
            "Generic repo/article links are not scraped automatically.",
            "Use this as a source candidate and route manually after review.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Nexus source intake router for links, emails, NotebookLM exports, and local transcripts.")
    parser.add_argument("--input", default="", help="Raw URL or text input.")
    parser.add_argument("--file", default="", help="Optional path to a local file.")
    parser.add_argument("--type", choices=TYPE_CHOICES, default="auto")
    parser.add_argument("--campaign", choices=CAMPAIGN_CHOICES, default="auto")
    parser.add_argument("--dry-run", action="store_true", help="Preview only. Dry-run is the default.")
    parser.add_argument("--apply", action="store_true", help="Write to the existing destination for the selected route.")
    parser.add_argument("--limit", type=int, default=3, help="Max items to process for expandable sources. Default: 3.")
    args = parser.parse_args()

    apply = bool(args.apply)
    file_path = Path(args.file).resolve() if args.file else None
    raw_input = args.input.strip()
    if file_path is None and not raw_input:
        print(_json({"ok": False, "error": "one_of_input_or_file_required"}))
        return 1
    if file_path is not None and not file_path.exists():
        print(_json({"ok": False, "error": f"file_not_found: {file_path}"}))
        return 1

    effective_type = _detect_type(raw_input, file_path, args.type)
    campaign = _infer_campaign(raw_input or str(file_path or ""), args.campaign)

    if effective_type == "youtube_video":
        url = _urls(raw_input)[0] if _urls(raw_input) else raw_input
        result = _route_video(url, apply=apply, campaign=campaign, limit=args.limit)
    elif effective_type == "youtube_channel":
        url = _urls(raw_input)[0] if _urls(raw_input) else raw_input
        result = _route_youtube_channel(url, apply=apply, campaign=campaign)
    elif effective_type == "youtube_playlist":
        url = _urls(raw_input)[0] if _urls(raw_input) else raw_input
        result = _route_youtube_playlist(url, apply=apply, campaign=campaign, limit=args.limit)
    elif effective_type == "email_body":
        body = raw_input
        if file_path is not None:
            body = file_path.read_text(encoding="utf-8")
        result = _route_email_body(body, apply=apply, campaign=campaign, limit=args.limit)
    elif effective_type == "notebooklm_export":
        if file_path is None and not raw_input:
            print(_json({"ok": False, "error": "notebooklm_export_requires_input_or_file"}))
            return 1
        text = file_path.read_text(encoding="utf-8") if file_path is not None else raw_input
        result = _route_notebooklm_export(text, file_path=file_path, apply=apply, campaign=campaign)
    elif effective_type == "transcript_file":
        if file_path is None:
            print(_json({"ok": False, "error": "transcript_file_requires_file"}))
            return 1
        result = _route_transcript_file(file_path, apply=apply, campaign=campaign)
    elif effective_type in {"repo_link", "article_link"}:
        result = _route_article_or_repo(raw_input, input_type=effective_type, campaign=campaign)
    else:
        print(_json({"ok": False, "error": f"unsupported_or_unresolved_type: {effective_type}"}))
        return 1

    payload = {
        "ok": bool(result.get("ok")),
        "generated_at": _now(),
        "mode": "apply" if apply else "dry-run",
        "requested_type": args.type,
        "effective_type": effective_type,
        "campaign": campaign,
        "canonical_path": "transcript_queue -> knowledge_items -> bridge_approved_knowledge_to_nexus_os.py",
        "result": result,
        "documentation": str(DOCS_DEFAULT.relative_to(ROOT)),
    }
    print(_json(payload))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
