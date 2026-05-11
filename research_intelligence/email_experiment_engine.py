"""
YouTube video -> email experiment drafter.

Reads recent YouTube-backed `research_artifacts` rows, turns them into
`video_email_experiments`, `email_campaigns`, and `email_variants`, and leaves
everything in draft/manual-review status for operator testing.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
DEFAULT_LIMIT = int(os.getenv("YOUTUBE_EMAIL_EXPERIMENT_LIMIT", "5"))

TOPIC_AUDIENCES = {
    "business_opportunities": "operators_founders",
    "crm_automation": "agency_owners",
    "general_business_intelligence": "small_business_owners",
    "trading": "traders_investing_curiosity",
}

TOPIC_CTAS = {
    "business_opportunities": "Reply with BUILD if you want the playbook turned into a real offer.",
    "crm_automation": "Reply with PIPELINE if you want the automation version.",
    "general_business_intelligence": "Reply with BREAKDOWN if you want the implementation notes.",
    "trading": "Reply with SETUP if you want the distilled rules and caveats.",
}

HOOK_TYPES = ("curiosity", "contrarian", "playbook")
FILLER_PHRASES = (
    "in this video",
    "i'm going to show you",
    "i am going to show you",
    "walk you through",
    "before we get into it",
    "if you haven't subscribed",
    "consider subscribing",
    "drop a comment",
    "click the like button",
)


def _headers(prefer: str = "return=representation") -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_get(path: str) -> List[dict]:
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{path}", headers=_headers())
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _sb_post(table: str, rows: List[dict], prefer: str = "return=representation") -> List[dict]:
    req = urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/{table}",
        data=json.dumps(rows).encode(),
        headers=_headers(prefer),
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def _quote(value: str) -> str:
    return urllib.parse.quote(str(value), safe="")


def _deterministic_uuid(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, name))


def _slug(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-") or "untitled"


def _clean(text: object, limit: int = 240) -> str:
    value = str(text or "")
    value = re.sub(r"Kind:\s*captions\s*Language:\s*[a-z-]+\s*", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\bkind:\s*captions\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\blanguage:\s*[a-z-]+\b", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\[[^\]]+\]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" .,-")
    value = re.sub(r"([.!?])\1+", r"\1", value)
    return value[:limit]


def _maybe_uuid(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        return None


def _first(items: object, fallback: str = "") -> str:
    if isinstance(items, list):
        for item in items:
            cleaned = _clean(item)
            if cleaned:
                return cleaned
    return _clean(fallback)


def _sentences(text: object, limit: int = 8) -> List[str]:
    value = _clean(text, limit=2000)
    if not value:
        return []
    chunks = re.split(r"(?<=[.!?])\s+|\s{2,}", value)
    cleaned: List[str] = []
    for chunk in chunks:
        sentence = _clean(chunk, limit=220)
        if sentence and len(sentence) > 25:
            cleaned.append(sentence)
        if len(cleaned) >= limit:
            break
    return cleaned


def _depromo(text: str) -> str:
    value = _clean(text, limit=220)
    lower = value.lower()
    for phrase in FILLER_PHRASES:
        if phrase in lower:
            value = re.sub(re.escape(phrase), "", value, flags=re.IGNORECASE).strip(" ,-.:")
            lower = value.lower()
    value = re.sub(r"^(so|and|but)\s+", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+", " ", value)
    return value[:220]


def _operator_rewrite(line: str, topic: str) -> str:
    lower = line.lower()

    if "apollo" in lower or "kalman filter" in lower:
        return "Apollo-era Kalman filtering can remove market noise and make trend signals easier to trade."

    if "leaps" in lower and "selling" in lower:
        return "Selling LEAPS instead of buying them changes the payoff profile while keeping the setup rule-based."

    if "seven top trading skills" in lower or ("trading for" in lower and "lost for" in lower):
        return "A small set of trading skills separates random screen time from repeatable execution."

    if any(phrase in lower for phrase in ("bad leads", "ghosted by clients", "six figures a month", "funding business")):
        return "The growth came from tightening lead quality, fixing fulfillment mistakes, and turning the process into a repeatable funding offer."

    if "cloud design wrong" in lower or "claude design wrong" in lower:
        return "Most people use Claude for surface-level assets when the bigger opportunity is packaging stronger offers."

    if topic == "business_opportunities" and lower.startswith("i "):
        return "The edge came from turning a messy learning process into one repeatable offer and sales motion."

    if topic == "trading" and lower.startswith(("i ", "my ")):
        return "The useful part is the rule set, not the personality behind the chart."

    return line


def _pick_best_line(candidates: List[str], fallback: str = "") -> str:
    scored: List[tuple[int, str]] = []
    for raw in candidates:
        line = _depromo(raw)
        lower = line.lower()
        if not line or len(line) < 25:
            continue
        score = 0
        if any(char.isdigit() for char in line):
            score += 3
        if any(word in lower for word in ("instead", "because", "without", "only", "exactly", "rule", "system", "offer", "strategy", "framework")):
            score += 2
        if any(word in lower for word in ("subscribe", "comment", "channel", "like button")):
            score -= 5
        if lower.startswith(("this video", "i'm going", "i am going", "before we")):
            score -= 3
        score += min(len(line) // 40, 3)
        scored.append((score, line))
    if scored:
        scored.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        return scored[0][1]
    return _depromo(fallback)


def _distill_row(row: dict) -> dict:
    title = _clean(row.get("title"), limit=120)
    summary = _clean(row.get("summary"), limit=300)
    content_sentences = _sentences(row.get("content"), limit=10)
    key_points = [_clean(item) for item in (row.get("key_points") or []) if _clean(item)]
    action_items = [_clean(item) for item in (row.get("action_items") or []) if _clean(item)]
    opportunity_notes = [_clean(item) for item in (row.get("opportunity_notes") or []) if _clean(item)]

    topic = str(row.get("topic") or "")
    insight = _operator_rewrite(
        _pick_best_line(key_points + content_sentences + [summary], fallback=summary or title),
        topic,
    )
    action = _operator_rewrite(
        _pick_best_line(action_items + content_sentences + [insight], fallback=insight),
        topic,
    )
    why_it_matters = _operator_rewrite(
        _pick_best_line(opportunity_notes + [summary] + content_sentences, fallback=summary or insight),
        topic,
    )

    if topic == "trading":
        why_it_matters = _pick_best_line(
            [why_it_matters, "A setup is only useful if it is simple enough to repeat and strict enough to test."],
            fallback=why_it_matters,
        )
    elif topic == "business_opportunities":
        why_it_matters = _pick_best_line(
            [why_it_matters, "The value is in turning the idea into a specific offer someone can buy quickly."],
            fallback=why_it_matters,
        )

    return {
        "title": title,
        "summary": summary,
        "insight": insight,
        "action": action,
        "why_it_matters": why_it_matters,
    }


def _fetch_candidates(limit: int) -> List[dict]:
    rows = _sb_get(
        "research_artifacts"
        "?select=id,source,source_type,source_url,topic,subtheme,title,summary,content,key_points,action_items,opportunity_notes,trace_id,created_at"
        "&source_type=eq.youtube_channel"
        "&order=created_at.desc"
        f"&limit={limit * 4}"
    )
    try:
        _sb_get("video_email_experiments?select=id&limit=1")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RuntimeError(
                "Missing table `video_email_experiments`. Apply "
                "`supabase/migrations/20260425150000_youtube_email_experiments.sql` "
                "to the remote Supabase database, then rerun the email experiment engine."
            ) from exc
        raise
    candidates: List[dict] = []
    for row in rows:
        if not _clean(row.get("summary")):
            continue
        candidates.append(row)
        if len(candidates) >= limit:
            break
    return candidates


def _audience(row: dict) -> str:
    return TOPIC_AUDIENCES.get(str(row.get("topic") or ""), "general_business")


def _cta(row: dict) -> str:
    return TOPIC_CTAS.get(str(row.get("topic") or ""), "Reply if you want the full breakdown.")


def _primary_angle(row: dict) -> str:
    topic = str(row.get("topic") or "")
    if topic == "trading":
        return "distill the setup into one clear rule set with caveats"
    if topic == "crm_automation":
        return "show the automation bottleneck the video exposes and the practical fix"
    if topic == "business_opportunities":
        return "turn the video into a simple money-making angle readers can picture"
    return "extract the sharpest insight and frame it as an actionable lesson"


def _hypothesis(row: dict) -> str:
    title = _clean(row.get("title"), limit=120)
    topic = _clean(row.get("topic"), limit=40)
    return f"Videos about {topic or 'this topic'} like '{title}' will earn more replies when framed as a concrete takeaway instead of a generic summary."


def _experiment_row(row: dict) -> dict:
    artifact_uuid = _maybe_uuid(row.get("id"))
    key_points = [_clean(item) for item in (row.get("key_points") or []) if _clean(item)]
    action_items = [_clean(item) for item in (row.get("action_items") or []) if _clean(item)]
    distilled = _distill_row(row)
    return {
        "id": _deterministic_uuid(f"video-email-experiment:{row['id']}"),
        "research_artifact_id": artifact_uuid,
        "source_url": row.get("source_url"),
        "video_title": _clean(row.get("title"), limit=240),
        "topic": row.get("topic"),
        "subtheme": row.get("subtheme"),
        "audience": _audience(row),
        "hypothesis": _hypothesis(row),
        "primary_angle": _primary_angle(row),
        "cta": _cta(row),
        "status": "drafted",
        "metadata": {
            "research_artifact_id_raw": row.get("id"),
            "source": row.get("source"),
            "key_points": key_points,
            "action_items": action_items,
            "distilled": distilled,
        },
        "trace_id": row.get("trace_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _campaign_row(row: dict, experiment_id: str) -> dict:
    distilled = _distill_row(row)
    title = distilled["title"]
    summary = _clean(distilled["insight"] or distilled["summary"], limit=180)
    return {
        "id": _deterministic_uuid(f"email-campaign:{row['id']}"),
        "experiment_id": experiment_id,
        "campaign_name": f"{_slug(row.get('topic'))}-{_slug(title)}",
        "topic": row.get("topic"),
        "audience": _audience(row),
        "send_channel": "manual_review",
        "send_status": "draft",
        "subject_line": f"{title[:58]}",
        "preview_text": summary,
        "body_markdown": None,
        "cta": _cta(row),
        "metadata": {
            "research_artifact_id": row.get("id"),
            "video_title": title,
            "distilled": distilled,
        },
        "trace_id": row.get("trace_id"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _subject_for_hook(title: str, hook_type: str, key_point: str) -> str:
    if hook_type == "curiosity":
        return _clean(f"The part of '{title}' nobody uses", limit=78)
    if hook_type == "contrarian":
        return _clean(f"Most people took the wrong lesson from '{title}'", limit=78)
    return _clean(f"Steal this play from '{title}'", limit=78)


def _preview_for_hook(summary: str, hook_type: str, key_point: str) -> str:
    if hook_type == "curiosity":
        return _clean(f"I pulled one surprising angle from the video: {key_point or summary}", limit=160)
    if hook_type == "contrarian":
        return _clean(f"The useful takeaway is not the obvious one. It is this: {key_point or summary}", limit=160)
    return _clean(f"Here is the tactic worth testing from the video: {key_point or summary}", limit=160)


def _body_for_hook(row: dict, hook_type: str) -> str:
    distilled = _distill_row(row)
    title = distilled["title"]
    summary = distilled["summary"]
    key_point = distilled["insight"]
    action = distilled["action"]
    note = distilled["why_it_matters"]
    cta = _cta(row)

    if hook_type == "curiosity":
        opening = f"I watched a video called '{title}' and the most useful part was not the headline idea."
        bridge = f"It was this: {key_point}."
    elif hook_type == "contrarian":
        opening = f"Most people would summarize '{title}' the wrong way."
        bridge = f"The sharper lesson is: {key_point}."
    else:
        opening = f"If I had to steal one practical move from '{title}', it would be this."
        bridge = f"{action}."

    return "\n".join(
        [
            opening,
            "",
            bridge,
            "",
            f"Why it matters: {note or summary}",
            "",
            f"If this resonates, {cta}",
        ]
    ).strip()


def _variant_row(row: dict, campaign_id: str, hook_type: str) -> dict:
    distilled = _distill_row(row)
    title = distilled["title"]
    summary = _clean(distilled["summary"], limit=220)
    key_point = distilled["insight"]
    return {
        "id": _deterministic_uuid(f"email-variant:{row['id']}:{hook_type}"),
        "campaign_id": campaign_id,
        "variant_label": hook_type.upper(),
        "hook_type": hook_type,
        "angle_summary": _clean(f"{hook_type} framing around {key_point or title}", limit=200),
        "subject_line": _subject_for_hook(title, hook_type, key_point),
        "preview_text": _preview_for_hook(summary, hook_type, key_point),
        "body_markdown": _body_for_hook(row, hook_type),
        "cta": _cta(row),
        "status": "draft",
        "metadata": {
            "video_title": title,
            "research_artifact_id": row.get("id"),
            "distilled": distilled,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def draft_once(limit: int = DEFAULT_LIMIT) -> dict:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY are required")

    candidates = _fetch_candidates(limit)
    experiments_written: List[str] = []
    campaigns_written: List[str] = []
    variants_written: List[str] = []

    for row in candidates:
        experiment = _experiment_row(row)
        campaign = _campaign_row(row, experiment["id"])
        variants = [_variant_row(row, campaign["id"], hook_type) for hook_type in HOOK_TYPES]

        _sb_post("video_email_experiments", [experiment], prefer="resolution=merge-duplicates,return=representation")
        _sb_post("email_campaigns", [campaign], prefer="resolution=merge-duplicates,return=representation")
        _sb_post("email_variants", variants, prefer="resolution=merge-duplicates,return=representation")

        experiments_written.append(experiment["id"])
        campaigns_written.append(campaign["id"])
        variants_written.extend(variant["id"] for variant in variants)

    return {
        "candidates_considered": len(candidates),
        "experiments_written": experiments_written,
        "campaigns_written": campaigns_written,
        "variants_written": variants_written,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()
    print(json.dumps(draft_once(limit=args.limit), indent=2))
