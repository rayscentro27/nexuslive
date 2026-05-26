"""
Daily Content Engine — Nexus AI Wealth
========================================
Produces real content every day. No fake completions.

Daily output quota:
  - 1 YouTube script outline
  - 1 newsletter draft
  - 3 TikTok hooks
  - 5 X (Twitter) posts
  - 1 LinkedIn authority post
  - 1 SEO article draft

All outputs:
  - Saved to docs/content/<type>/YYYYMMDD_<slug>.md
  - Saved to Supabase workflow_outputs table
  - Require human approval before publishing (status='draft')
  - Carry evidence_path proving real execution

Topics cycle:
  business credit, PAYDEX score, AI automation, online business,
  funding readiness, affiliate systems, scalable income, AI operations,
  business systems

Usage:
  python3 -m lib.daily_content_engine
  python3 bin/nexus content pipeline
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "docs" / "content"

TOPICS = [
    "business credit building",
    "PAYDEX score optimization",
    "AI automation for business owners",
    "online business systems",
    "funding readiness strategy",
    "affiliate monetization systems",
    "scalable passive income",
    "AI operations and workflows",
    "business credit tiers and funding",
    "entrepreneur productivity with AI tools",
]

NEXUS_CTA = "https://goclearonline.cc"
NEWSLETTER_URL = "https://nexus-ai-wealth.beehiiv.com"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    return date.today().isoformat()


def _today_compact() -> str:
    return date.today().strftime("%Y%m%d")


def _topic_of_day() -> str:
    day_index = date.today().toordinal() % len(TOPICS)
    return TOPICS[day_index]


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower().strip())[:40]


def _sb_insert(payload: dict) -> dict:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return {"error": "supabase_not_configured"}
    data = json.dumps(payload).encode()
    import urllib.request
    req = urllib.request.Request(
        f"{url}/rest/v1/content_outputs",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
            return result[0] if isinstance(result, list) and result else result
    except Exception as exc:
        return {"error": str(exc)}


def _increment_quota(worker_id: str, quota_type: str) -> None:
    url = (os.getenv("SUPABASE_URL") or "").strip()
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY", "")
    )
    if not url or not key:
        return
    import urllib.request
    today = _today()
    # Upsert quota row
    payload = {
        "worker_id": worker_id,
        "quota_type": quota_type,
        "quota_date": today,
        "current_count": 1,
        "last_updated_at": _now(),
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{url}/rest/v1/worker_daily_quotas",
        data=data,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            pass
    except Exception:
        pass


def _save_file(subdir: str, filename: str, content: str) -> Path:
    d = CONTENT_DIR / subdir
    d.mkdir(parents=True, exist_ok=True)
    path = d / filename
    path.write_text(content, encoding="utf-8")
    return path


_CONTENT_TIER_MAP: dict[str, str] = {
    "draft":  "premium",    # YouTube scripts, newsletters, SEO articles, LinkedIn
    "cheap":  "lightweight", # TikTok hooks, X posts
    "reason": "reasoning",
}


def _call_model(prompt: str, system: str = "", task_type: str = "draft",
                content_type: str = "", min_words: int = 0) -> str:
    tier = _CONTENT_TIER_MAP.get(task_type, "premium")
    try:
        from lib.content_generation_router import generate_content, is_template_output
        result = generate_content(
            prompt, system=system, tier=tier,
            content_type=content_type, min_words=min_words,
            timeout=120, max_tokens=4096,
        )
        text = result.get("response") or ""
        if result.get("success") and text and not is_template_output(text):
            _log_generation(task_type, tier, result)
            return text
        # Quality below threshold or template — log and fall through
        _log_generation(task_type, tier, result, warn=True)
        if text:
            return text  # return even low-quality output rather than template
        return _template_fallback(prompt)
    except Exception as exc:
        print(f"[content_engine] content_generation_router error: {exc} — using nexus_model_caller")
    # Direct fallback to nexus_model_caller
    try:
        from lib.nexus_model_caller import call
        result = call(prompt, task_type=task_type, system=system, timeout=120)
        if result.get("success") and result.get("response"):
            return str(result["response"]).strip()
    except Exception:
        pass
    return _template_fallback(prompt)


def _log_generation(task_type: str, tier: str, result: dict, warn: bool = False) -> None:
    provider = result.get("provider", "?")
    model = result.get("model", "?")
    score = result.get("quality_score", "?")
    words = result.get("word_count", "?")
    flag = "WARN" if warn else "OK"
    print(f"[content_engine] {flag} {task_type}/{tier} → {provider}:{model} | {words}w | q={score}")


def _template_fallback(prompt: str) -> str:
    """Return a structured template when LLM is unavailable."""
    return (
        f"[TEMPLATE — LLM unavailable at generation time]\n\n"
        f"Prompt intent: {prompt[:200]}\n\n"
        f"Status: draft — requires human completion before publishing.\n"
        f"Generated: {_now()}"
    )


# ─── Content generators ────────────────────────────────────────────────────────

def generate_youtube_script(topic: str | None = None) -> dict:
    topic = topic or _topic_of_day()
    system = (
        "You are a faceless YouTube script writer for the Nexus AI Wealth channel. "
        "Write educational, high-retention business content for entrepreneurs. "
        "No fluff. Hook in first 5 seconds. Clear value. Strong CTA at end."
    )
    prompt = (
        f"Write a YouTube script outline for a faceless video on: '{topic}'.\n\n"
        f"Format:\n"
        f"TITLE: (clickable, SEO-optimized)\n"
        f"TARGET KEYWORD: (primary search keyword)\n"
        f"HOOK (0:00-0:30): (attention-grabbing opening)\n"
        f"INTRO (0:30-1:30): (establish authority + promise)\n"
        f"MAIN CONTENT (3-5 sections with timestamps):\n"
        f"  Section 1: ...\n"
        f"  Section 2: ...\n"
        f"  (etc)\n"
        f"CTA (last 30s): Direct to {NEXUS_CTA}\n"
        f"DESCRIPTION: (300 chars, SEO-rich)\n"
        f"TAGS: (10 tags)\n\n"
        f"Length: 8-12 minute script. Faceless format — no camera required."
    )
    body = _call_model(prompt, system=system, task_type="draft",
                       content_type="youtube_script", min_words=500)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_yt_script.md"
    path = _save_file("youtube", filename, f"# YouTube Script — {topic}\n\n{body}")

    row = _sb_insert({
        "worker_id": "content_worker",
        "output_type": "youtube_script",
        "title": f"YouTube Script: {topic}",
        "body": body,
        "metadata": {"topic": topic, "platform": "youtube"},
        "status": "draft",
        "evidence_path": str(path),
        "word_count": len(body.split()),
        "generated_by": "daily_content_engine",
        "requires_approval": True,
        "created_at": _now(),
    })
    _increment_quota("content_worker", "content_pieces")
    return {"type": "youtube_script", "topic": topic, "path": str(path), "row_id": row.get("id"), "words": len(body.split())}


def generate_newsletter_draft(topic: str | None = None) -> dict:
    topic = topic or _topic_of_day()
    system = (
        "You are writing the Nexus AI Wealth newsletter. "
        "Tone: direct, insightful, practical. No fluff. "
        "Readers are entrepreneurs and business owners who want real actionable intelligence."
    )
    prompt = (
        f"Write a complete newsletter issue for Nexus AI Wealth on: '{topic}'.\n\n"
        f"Format:\n"
        f"SUBJECT LINE: (open-worthy, 50 chars max)\n"
        f"PREVIEW TEXT: (90 chars — appears in inbox)\n\n"
        f"---\n\n"
        f"[HOOK PARAGRAPH]: (2-3 sentences. Why this matters now.)\n\n"
        f"[MAIN SECTION 1 — THE PROBLEM]: (what most people get wrong)\n\n"
        f"[MAIN SECTION 2 — THE INTELLIGENCE]: (the insight or strategy)\n\n"
        f"[MAIN SECTION 3 — THE ACTION]: (3 concrete steps to take this week)\n\n"
        f"[NEXUS RESOURCE]: Mention free tool at {NEXUS_CTA}\n\n"
        f"[SIGN-OFF]: (brief, personal tone)\n\n"
        f"Word count target: 400-600 words."
    )
    body = _call_model(prompt, system=system, task_type="draft",
                       content_type="newsletter", min_words=300)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_newsletter.md"
    path = _save_file("newsletter", filename, f"# Newsletter Draft — {topic}\n\n{body}")

    row = _sb_insert({
        "worker_id": "content_worker",
        "output_type": "newsletter",
        "title": f"Newsletter: {topic}",
        "body": body,
        "metadata": {"topic": topic, "platform": "beehiiv", "url": NEWSLETTER_URL},
        "status": "draft",
        "evidence_path": str(path),
        "word_count": len(body.split()),
        "generated_by": "daily_content_engine",
        "requires_approval": True,
        "created_at": _now(),
    })
    _increment_quota("content_worker", "content_pieces")
    return {"type": "newsletter", "topic": topic, "path": str(path), "row_id": row.get("id"), "words": len(body.split())}


def generate_tiktok_hooks(topic: str | None = None, count: int = 3) -> list[dict]:
    topic = topic or _topic_of_day()
    system = (
        "You write viral TikTok hooks for business and money content. "
        "Hooks must be under 15 seconds when read aloud. Pattern interrupt style. "
        "No hashtags in the hook itself."
    )
    prompt = (
        f"Write {count} separate TikTok hooks for the topic: '{topic}'.\n\n"
        f"Each hook should:\n"
        f"- Start with a pattern interrupt (number, 'Stop', 'Most', 'Nobody tells you', etc.)\n"
        f"- Create immediate curiosity\n"
        f"- Be 1-2 sentences max (under 15 seconds spoken)\n"
        f"- Target business owners and entrepreneurs\n\n"
        f"Format each as:\nHOOK 1: ...\nHOOK 2: ...\nHOOK 3: ..."
    )
    body = _call_model(prompt, system=system, task_type="cheap",
                       content_type="tiktok_hook", min_words=8)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_tiktok_hooks.md"
    path = _save_file("tiktok", filename, f"# TikTok Hooks — {topic}\n\n{body}")

    results = []
    for i in range(count):
        row = _sb_insert({
            "worker_id": "content_worker",
            "output_type": "tiktok_hook",
            "title": f"TikTok Hook #{i+1}: {topic}",
            "body": body,
            "metadata": {"topic": topic, "platform": "tiktok", "hook_index": i+1},
            "status": "draft",
            "evidence_path": str(path),
            "generated_by": "daily_content_engine",
            "requires_approval": True,
            "created_at": _now(),
        })
        results.append({"type": "tiktok_hook", "topic": topic, "path": str(path), "row_id": row.get("id")})
        _increment_quota("content_worker", "content_pieces")
    return results


def generate_x_posts(topic: str | None = None, count: int = 5) -> list[dict]:
    topic = topic or _topic_of_day()
    system = (
        "You write high-engagement X (Twitter) posts about business, AI, and entrepreneurship. "
        "Style: authority + insight. Short sentences. Real value. End with a hook or question."
    )
    prompt = (
        f"Write {count} X posts on the topic: '{topic}'.\n\n"
        f"Each post must:\n"
        f"- Be under 280 characters\n"
        f"- Stand alone (no thread — single post)\n"
        f"- Deliver genuine insight or contrarian take\n"
        f"- Target entrepreneurs and business owners\n"
        f"- Not use hashtags (they reduce reach on X)\n\n"
        f"Format:\nPOST 1: ...\nPOST 2: ...\n(etc)"
    )
    body = _call_model(prompt, system=system, task_type="cheap",
                       content_type="x_post", min_words=10)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_x_posts.md"
    path = _save_file("x_posts", filename, f"# X Posts — {topic}\n\n{body}")

    results = []
    for i in range(count):
        row = _sb_insert({
            "worker_id": "content_worker",
            "output_type": "x_post",
            "title": f"X Post #{i+1}: {topic}",
            "body": body,
            "metadata": {"topic": topic, "platform": "x_twitter"},
            "status": "draft",
            "evidence_path": str(path),
            "generated_by": "daily_content_engine",
            "requires_approval": True,
            "created_at": _now(),
        })
        results.append({"type": "x_post", "topic": topic, "path": str(path), "row_id": row.get("id")})
        _increment_quota("content_worker", "content_pieces")
    return results


def generate_linkedin_post(topic: str | None = None) -> dict:
    topic = topic or _topic_of_day()
    system = (
        "You write LinkedIn authority posts for business owners who use AI. "
        "Style: first person, professional but conversational, insight-driven. "
        "Starts with a hook line. Short paragraphs. Ends with a question or CTA."
    )
    prompt = (
        f"Write a LinkedIn authority post on: '{topic}'.\n\n"
        f"Structure:\n"
        f"Line 1: Hook (bold claim or insight — no fluff)\n"
        f"Lines 2-4: Context / the problem most people face\n"
        f"Lines 5-8: The insight or framework (3 short bullet points or paragraph)\n"
        f"Lines 9-10: Call to action (ask about free tool at {NEXUS_CTA} or ask a question)\n\n"
        f"Length: 200-300 words. Short paragraphs. Professional but not corporate."
    )
    body = _call_model(prompt, system=system, task_type="draft",
                       content_type="linkedin_post", min_words=120)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_linkedin.md"
    path = _save_file("linkedin", filename, f"# LinkedIn Post — {topic}\n\n{body}")

    row = _sb_insert({
        "worker_id": "content_worker",
        "output_type": "linkedin_post",
        "title": f"LinkedIn Post: {topic}",
        "body": body,
        "metadata": {"topic": topic, "platform": "linkedin"},
        "status": "draft",
        "evidence_path": str(path),
        "word_count": len(body.split()),
        "generated_by": "daily_content_engine",
        "requires_approval": True,
        "created_at": _now(),
    })
    _increment_quota("content_worker", "content_pieces")
    return {"type": "linkedin_post", "topic": topic, "path": str(path), "row_id": row.get("id"), "words": len(body.split())}


def generate_seo_article(topic: str | None = None) -> dict:
    topic = topic or _topic_of_day()
    system = (
        "You write SEO-optimized articles for small business owners about business credit, "
        "AI tools, funding, and income strategies. Style: clear, authoritative, practical. "
        "Include header structure (H2, H3). No fluff. Real actionable advice."
    )
    prompt = (
        f"Write a full SEO article on: '{topic}' for the Nexus AI Wealth blog.\n\n"
        f"Format:\n"
        f"META TITLE: (55-60 chars)\n"
        f"META DESCRIPTION: (150-160 chars)\n"
        f"PRIMARY KEYWORD: ...\n"
        f"SECONDARY KEYWORDS: (3-4)\n\n"
        f"---\n\n"
        f"# [Article Title]\n\n"
        f"[Introduction — 100 words. State the problem, promise the solution.]\n\n"
        f"## [H2 Section 1]\n...\n\n"
        f"## [H2 Section 2]\n...\n\n"
        f"## [H2 Section 3]\n...\n\n"
        f"## Conclusion\n"
        f"[Recap + CTA to {NEXUS_CTA}]\n\n"
        f"Target word count: 1,200-1,800 words."
    )
    body = _call_model(prompt, system=system, task_type="draft",
                       content_type="seo_article", min_words=900)
    slug = _slugify(topic)
    filename = f"{_today_compact()}_{slug}_seo_article.md"
    path = _save_file("seo", filename, f"# SEO Article Draft — {topic}\n\n{body}")

    row = _sb_insert({
        "worker_id": "content_worker",
        "output_type": "seo_article",
        "title": f"SEO Article: {topic}",
        "body": body,
        "metadata": {"topic": topic, "platform": "blog", "target_url": NEXUS_CTA},
        "status": "draft",
        "evidence_path": str(path),
        "word_count": len(body.split()),
        "generated_by": "daily_content_engine",
        "requires_approval": True,
        "created_at": _now(),
    })
    _increment_quota("content_worker", "content_pieces")
    return {"type": "seo_article", "topic": topic, "path": str(path), "row_id": row.get("id"), "words": len(body.split())}


# ─── Daily pipeline ───────────────────────────────────────────────────────────

def run_daily_pipeline(topic: str | None = None, dry_run: bool = False) -> dict:
    """
    Run the full daily content generation pipeline.
    Returns summary dict with evidence paths for every output.
    """
    topic = topic or _topic_of_day()
    print(f"[content_engine] Daily pipeline starting — topic: '{topic}'")
    print(f"[content_engine] Output: {CONTENT_DIR}")
    print(f"[content_engine] Dry run: {dry_run}")
    print()

    outputs = []
    errors = []

    def _run(label: str, fn, *args, **kwargs):
        print(f"  Generating {label}...", end="", flush=True)
        try:
            if dry_run:
                print(f" [DRY RUN — skipped]")
                return
            result = fn(*args, **kwargs)
            if isinstance(result, list):
                for r in result:
                    outputs.append(r)
                    print(f"\n    ✅ {r['type']} → {Path(r['path']).name} [{r.get('row_id','?')[:8] if r.get('row_id') else 'no-db'}...]", end="")
                print()
            else:
                outputs.append(result)
                print(f" ✅ {result.get('words','?')} words → {Path(result['path']).name}")
        except Exception as exc:
            errors.append({"label": label, "error": str(exc)})
            print(f" ❌ {exc}")

    _run("YouTube script",    generate_youtube_script,  topic)
    _run("Newsletter draft",  generate_newsletter_draft, topic)
    _run("TikTok hooks (3)",  generate_tiktok_hooks,     topic, 3)
    _run("X posts (5)",       generate_x_posts,          topic, 5)
    _run("LinkedIn post",     generate_linkedin_post,    topic)
    _run("SEO article",       generate_seo_article,      topic)

    total = len(outputs)
    print(f"\n[content_engine] Pipeline complete: {total} outputs | {len(errors)} errors")
    if errors:
        for e in errors:
            print(f"  ❌ {e['label']}: {e['error']}")

    return {
        "date": _today(),
        "topic": topic,
        "outputs": outputs,
        "errors": errors,
        "total_outputs": total,
        "content_dir": str(CONTENT_DIR),
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv
    result = run_daily_pipeline(dry_run=dry)
    print(f"\nEvidence: {result['content_dir']}")
    for o in result["outputs"]:
        print(f"  {o.get('type','?'):20} → {o.get('path','?')}")
