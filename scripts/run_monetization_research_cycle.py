#!/usr/bin/env python3
"""
run_monetization_research_cycle.py — proactive monetization topic discovery.

Closes the missing piece in Nexus: KEYWORD-DRIVEN discovery. The existing
youtube_intelligence_worker only processes a REGISTERED source list
(config/nexus_sources.yaml); nothing searched YouTube/web by keyword to find
new recognizable, in-demand, monetizable topics. This runner does that using a
FREE, no-API-key provider (yt-dlp `ytsearch`), scores monetization fit, and
feeds the EXISTING pipeline tables (source_extractions + proposed
knowledge_items) for human review — no new duplicate system.

SAFETY CONTRACT:
  * Dry-run by default. Writes to Supabase ONLY with --apply.
  * YouTube discovery uses yt-dlp `ytsearch` (free, no API key, no paid credits).
  * Web/Google discovery is DISABLED unless a free/local provider is configured
    (none today) — never silently calls a paid/unknown search API.
  * Writes ONLY to review/research tables (source_extractions, knowledge_items
    with status='proposed'/dry_run). Never writes to publishing/content-live
    tables. No posting, scheduling, email, ads, or Nexus OS bridge.
  * No revenue/approval claims; flags compliance-risky "guarantee" language.

Usage:
  python3 scripts/run_monetization_research_cycle.py \
      --keywords "business credit funding,Chase small business funding" \
      --source both --limit 5 --dry-run
  python3 scripts/run_monetization_research_cycle.py \
      --keywords "business credit funding" --source youtube --limit 3 --apply
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "reports" / "monetization_research"

DEFAULT_KEYWORDS = [
    "business credit funding", "Chase small business funding",
    "business funding readiness", "Paydex vendor credit", "Nav business credit",
    "LLC funding readiness", "business credit cards no PG",
    "startup business funding", "vendor tradelines", "business credit monitoring",
]

# keyword/topic → existing Revenue Hub campaign name
CAMPAIGN_RULES = [
    (r"\bnav\b", "Nav Business Credit"),
    (r"paydex|vendor (credit|tradeline)|net.?30|tradeline", "Paydex / Business Credit Education"),
    (r"legalzoom|llc|formation|incorporat", "LegalZoom Business Formation"),
    (r"newsletter|beehiiv|email list", "Beehiiv Newsletter Platform"),
    (r"business credit|paydex|builder|no pg|monitoring|business credit card", "Business Credit Builder Tools"),
    (r"funding|chase|sba|loan|grant|capital", "Business Credit Builder Tools"),
]

# language that needs compliance care (no guaranteed-approval/earnings claims)
RISK_PATTERNS = re.compile(
    r"guarantee|guaranteed|100%|approved instantly|get approved|no credit check|"
    r"easy money|risk.?free|secret the banks|they don.?t want you",
    re.I,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ── Discovery ─────────────────────────────────────────────────────────────────

def youtube_search(keyword: str, max_results: int) -> list[dict]:
    """Free keyword discovery via yt-dlp ytsearch. No API key, no paid credits."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json",
             f"ytsearch{max_results}:{keyword}"],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except Exception as e:
        return [{"_error": f"yt-dlp failed: {str(e)[:120]}"}]
    items = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        items.append({
            "title": d.get("title") or "",
            "url": d.get("url") or (f"https://www.youtube.com/watch?v={d.get('id')}" if d.get("id") else ""),
            "video_id": d.get("id") or "",
            "channel": d.get("channel") or d.get("uploader") or "",
            "views": d.get("view_count"),
            "duration": d.get("duration"),
            "snippet": (d.get("description") or "")[:240],
            "keyword": keyword,
            "source": "youtube",
        })
    return items


def web_search(keyword: str, max_results: int, allow_paid: bool) -> list[dict]:
    """Web/Google discovery — disabled unless a free/local provider is configured."""
    # No free/local web-search provider is installed (no SERP/CSE/Tavily/DDG libs,
    # no API keys). Per the safety contract we never call a paid/unknown API.
    return [{"_skipped": "no free web-search provider configured; web discovery skipped (safe)",
             "keyword": keyword, "source": "web"}]


# ── Scoring ───────────────────────────────────────────────────────────────────

def match_campaign(text: str) -> str:
    t = text.lower()
    for pat, camp in CAMPAIGN_RULES:
        if re.search(pat, t):
            return camp
    return "Business Credit Builder Tools"


def score_item(item: dict) -> dict:
    title = item.get("title", "")
    text = f"{title} {item.get('snippet','')} {item.get('keyword','')}"
    views = item.get("views") or 0

    # demand: log-scaled view count (0..100)
    demand = min(round((math.log10(views + 1) / 7) * 100), 100) if views else 30
    # recognition: has a named channel + meaningful views
    recognition = min((40 if item.get("channel") else 10) + (min(views, 500000) / 500000 * 60), 100)
    recognition = round(recognition)
    # revenue fit: keyword strongly maps to a monetizable campaign
    campaign = match_campaign(text)
    revenue_fit = 80 if re.search(r"funding|credit|paydex|nav|llc|tradeline|capital|loan", text, re.I) else 45
    # content fit: question/how-to/list framings convert well to content
    content_fit = 75 if re.search(r"how|why|best|top|\d+\s|guide|tips|secrets?", title, re.I) else 50
    # compliance risk: guarantee/earnings claims → higher risk (worse)
    risk = 70 if RISK_PATTERNS.search(text) else 15
    # confidence: blended, penalized by risk
    confidence = round(max(0, (demand * 0.3 + recognition * 0.2 + revenue_fit * 0.3 + content_fit * 0.2) - risk * 0.3))

    angle = (f"Educational {campaign} content answering the demand behind "
             f"\"{item.get('keyword')}\" — disclosure required, no earnings/approval guarantees.")
    rec_action = ("Draft-only educational piece for review" if risk < 50
                  else "Review carefully — title uses risky claim language; reframe without guarantees")

    return {
        **item,
        "demand_score": demand,
        "recognition_score": recognition,
        "revenue_fit_score": revenue_fit,
        "content_fit_score": content_fit,
        "compliance_risk_score": risk,
        "confidence": confidence,
        "recommended_campaign": campaign,
        "monetization_angle": angle,
        "recommended_action": rec_action,
    }


# ── Supabase write (only with --apply) ────────────────────────────────────────

def sb_creds():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    if not (url and key):
        envf = ROOT / ".env"
        if envf.exists():
            for line in envf.read_text(errors="ignore").splitlines():
                if line.startswith("SUPABASE_URL=") and not url:
                    url = line.split("=", 1)[1].strip().strip('"')
                if line.startswith("SUPABASE_SERVICE_ROLE_KEY=") and not key:
                    key = line.split("=", 1)[1].strip().strip('"')
    return url, key


def sb_get_existing_urls(table, column, match):
    """Return set of existing values for `column` matching `match` filters (idempotency)."""
    try:
        import requests
    except Exception:
        return set()
    url, key = sb_creds()
    if not (url and key):
        return set()
    import requests
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    params = {"select": column, **match}
    try:
        r = requests.get(f"{url}/rest/v1/{table}", headers=h, params=params, timeout=30)
        if r.status_code in (200, 206):
            return {row.get(column) for row in r.json() if row.get(column)}
    except Exception:
        pass
    return set()


def sb_insert(table, rows, on_conflict=None):
    try:
        import requests
    except Exception:
        return False, "requests unavailable"
    url, key = sb_creds()
    if not (url and key):
        return False, "Supabase creds not found"
    import requests
    prefer = "return=minimal" + (",resolution=merge-duplicates" if on_conflict else "")
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json", "Prefer": prefer}
    params = {"on_conflict": on_conflict} if on_conflict else None
    try:
        r = requests.post(f"{url}/rest/v1/{table}", headers=h, params=params, data=json.dumps(rows), timeout=40)
        if r.status_code in (200, 201, 204):
            return True, f"{len(rows)} rows -> {table}"
        return False, f"{table}: HTTP {r.status_code} {r.text[:140]}"
    except Exception as e:
        return False, f"{table}: {str(e)[:140]}"


def to_source_extraction(it: dict, dry: bool) -> dict:
    return {
        "source_id": f"monsearch_{it.get('video_id','')[:16]}",
        "division": "monetization_intelligence",
        "scout_id": "monetization_search_scout",
        "video_id": it.get("video_id"),
        "video_title": it.get("title"),
        "source_url": it.get("url"),
        "tier": "B",
        "summary": it.get("monetization_angle"),
        "confidence_score": it.get("confidence"),
        "raw_content_chars": len(it.get("snippet", "")),
        "tags": [it.get("keyword"), it.get("recommended_campaign"), "keyword_discovery"],
        "fed_to_consensus": False,
        "fed_to_briefing": False,
        "extraction_data": {
            "channel": it.get("channel"), "views": it.get("views"),
            "demand_score": it.get("demand_score"),
            "recognition_score": it.get("recognition_score"),
            "revenue_fit_score": it.get("revenue_fit_score"),
            "content_fit_score": it.get("content_fit_score"),
            "compliance_risk_score": it.get("compliance_risk_score"),
            "recommended_campaign": it.get("recommended_campaign"),
            "recommended_action": it.get("recommended_action"),
            "discovery": "keyword_search", "dry_run": dry,
        },
    }


def to_knowledge_item(it: dict, dry: bool) -> dict:
    return {
        "domain": "monetization",
        "title": f"[Proposed] {it.get('title','')[:160]}",
        "content": (f"Discovered via keyword \"{it.get('keyword')}\" (YouTube). "
                    f"Channel: {it.get('channel')}. Views: {it.get('views')}. "
                    f"Angle: {it.get('monetization_angle')} "
                    f"Action: {it.get('recommended_action')}."),
        "source_url": it.get("url"),
        "source_type": "youtube",
        "quality_score": it.get("confidence"),
        "quality_label": ("high" if it.get("confidence", 0) >= 60 else
                          "medium" if it.get("confidence", 0) >= 35 else "low"),
        "status": "proposed",
        "dry_run": dry,
        "metadata": {
            "keyword": it.get("keyword"),
            "recommended_campaign": it.get("recommended_campaign"),
            "demand_score": it.get("demand_score"),
            "revenue_fit_score": it.get("revenue_fit_score"),
            "compliance_risk_score": it.get("compliance_risk_score"),
            "discovery": "monetization_search_scout",
        },
    }


# ── Report ────────────────────────────────────────────────────────────────────

def write_report(scored, queries, skipped_web, apply, stamp):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    md = REPORT_DIR / f"monetization_research_{stamp}.md"
    L = [f"# Monetization Research Cycle — {stamp}",
         f"_Mode: {'APPLY' if apply else 'DRY-RUN'} · provider: yt-dlp ytsearch (free, no API key)_\n",
         f"## Queries ({len(queries)})", ""]
    L += [f"- {q}" for q in queries]
    if skipped_web:
        L.append("\n> Web/Google discovery skipped — no free provider configured (safe).")
    L.append(f"\n## Top opportunities ({len(scored)})\n")
    for i, it in enumerate(sorted(scored, key=lambda x: x["confidence"], reverse=True)[:15], 1):
        L.append(f"{i}. **{it['title'][:80]}** — conf {it['confidence']} "
                 f"(demand {it['demand_score']}, rev-fit {it['revenue_fit_score']}, "
                 f"risk {it['compliance_risk_score']})\n   - {it['channel']} · {it.get('views')} views · {it['url']}\n"
                 f"   - → {it['recommended_campaign']} · {it['recommended_action']}")
    md.write_text("\n".join(L) + "\n")
    return md


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Proactive monetization topic discovery (dry-run by default)")
    ap.add_argument("--keywords", default=",".join(DEFAULT_KEYWORDS))
    ap.add_argument("--campaign", default="auto")
    ap.add_argument("--source", choices=["youtube", "web", "both"], default="youtube")
    ap.add_argument("--limit", type=int, default=5, help="max keywords to process")
    ap.add_argument("--max-results", type=int, default=5, help="results per keyword")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-paid-api", action="store_true", default=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    apply = args.apply and not args.dry_run
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()][:args.limit]
    stamp = ts()

    queries, scored, skipped_web = [], [], False
    for kw in keywords:
        if args.source in ("youtube", "both"):
            queries.append(f"youtube: {kw}")
            for it in youtube_search(kw, args.max_results):
                if it.get("_error"):
                    print(f"  ! {it['_error']}")
                    continue
                scored.append(score_item(it))
        if args.source in ("web", "both"):
            queries.append(f"web: {kw}")
            res = web_search(kw, args.max_results, not args.no_paid_api)
            if res and res[0].get("_skipped"):
                skipped_web = True

    md = write_report(scored, queries, skipped_web, apply, stamp)
    if args.json:
        (REPORT_DIR / f"monetization_research_{stamp}.json").write_text(json.dumps(scored, indent=2, default=str))

    top = sorted(scored, key=lambda x: x["confidence"], reverse=True)
    print(f"\nMode: {'APPLY (writing review rows)' if apply else 'DRY-RUN (no writes)'}")
    print(f"Provider: yt-dlp ytsearch (free, no API key){' · web skipped (no free provider)' if skipped_web else ''}")
    print(f"Keywords: {len(keywords)} · discovered: {len(scored)}")
    print(f"Report: {md}")
    print("\nTop 5 opportunities:")
    for it in top[:5]:
        print(f"  [{it['confidence']:>3}] {it['title'][:60]:62} → {it['recommended_campaign']} (risk {it['compliance_risk_score']})")

    if apply:
        print("\n-- Supabase writes (review tables only) --")
        if scored:
            # source_extractions: dedupe batch by video_id, then upsert (idempotent)
            seen_vid, se_rows = set(), []
            for it in top:
                vid = it.get("video_id")
                if vid and vid not in seen_vid:
                    seen_vid.add(vid)
                    se_rows.append(to_source_extraction(it, False))
            ok1, m1 = sb_insert("source_extractions", se_rows, on_conflict="source_id,video_id")
            print(f"  [{'OK' if ok1 else 'SKIP'}] {m1}")
            # knowledge_items: dedupe against existing monetization rows by source_url
            existing = sb_get_existing_urls("knowledge_items", "source_url", {"domain": "eq.monetization"})
            ki = [to_knowledge_item(it, False) for it in top
                  if it["compliance_risk_score"] < 50 and it["confidence"] >= 30
                  and it.get("url") not in existing]
            if ki:
                ok2, m2 = sb_insert("knowledge_items", ki)
                print(f"  [{'OK' if ok2 else 'SKIP'}] {m2}")
            else:
                print("  [SKIP] knowledge_items: no new items (all already proposed or gated)")
        else:
            print("  [SKIP] nothing discovered")
    else:
        print("\n(no writes — re-run with --apply to persist review rows)")
        print("Would write: source_extractions (all) + knowledge_items status='proposed' "
              "(risk<50 & conf>=30). review_required; no Nexus OS bridge until reviewed.")


if __name__ == "__main__":
    main()
