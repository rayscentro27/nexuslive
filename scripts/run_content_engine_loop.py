#!/usr/bin/env python3
"""
run_content_engine_loop.py — run ONE safe internal pass of the Nexus content engine.

Wires the first 3 approved prompts into the daily loop:
  * youtube_shorts.md      → YouTube Shorts draft
  * hyperframes_video.md   → HyperFrames plan (+ optional DRAFT render)
  * content_repurposing.md → LinkedIn / newsletter / social drafts

Pipeline per topic: draft → hyperframes plan → (optional draft render) → repurpose → score (rubric)
→ create/update board card → route (>=7 Needs Ray Review, <7 Improve/Retry) → approval card (review-ready only)
→ board digest. Deterministic + template-driven (no LLM call, no paid API, no network).

HARD SAFETY (this loop NEVER does any of these):
  no upload · no post · no schedule · no email/newsletter send · no affiliate signup ·
  no paid API · no credential change · no deploy/migration · never enables NEXUS_PUBLISH_EXECUTOR_ENABLED ·
  never runs social_publish_executor.py --apply · never sets Approved*/Published statuses ·
  never prints secrets · never commits .env · never clobbers existing board data (merge-only).

Usage:
  python scripts/run_content_engine_loop.py --limit 1 --dry-run --render-hyperframes --repurpose --no-telegram
  python scripts/run_content_engine_loop.py --limit 1 --render-hyperframes --repurpose --no-telegram
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import (  # noqa: E402
    load_board, find, new_card, upsert, _now, RAY_ONLY_STATUSES,
)

GEN = ROOT / "reports" / "content_engine" / "generated"
GEN_SHORTS = GEN / "youtube_shorts"
GEN_REPURP = GEN / "repurposed"
GEN_PLANS = GEN / "hyperframes_plans"
GEN_REPORTS = GEN / "loop_reports"
HF_RENDERS = ROOT / "reports" / "tool_lab" / "hyperframes_renders"
PLANS_DIR = ROOT / "reports" / "creative_short_plans"
PKG_DIR = ROOT / "reports" / "publish_packages"
CR_DIR = ROOT / "reports" / "tool_lab" / "creative_renders"

BANNED = ["guarantee", "guaranteed", "get approved", "make $", "instant approval", "get rich"]
LOOP_SAFE_STATUSES = {"Drafted", "Video Packet Ready", "Video Rendered", "Needs Ray Review", "Improve / Retry"}


# ----------------------------- topic ingestion -----------------------------
def parse_publish_package(p: Path) -> dict | None:
    """Extract a topic from a structured publish package markdown."""
    t = p.read_text(encoding="utf-8", errors="ignore")
    cid = re.search(r"Content ID:\s*([0-9a-f-]{8,})", t)
    title = re.search(r"Title:\s*(.+)", t)
    if not (cid and title):
        return None
    # the short-form script body (between the script header and the next ## section)
    m = re.search(r"##[^\n]*script[^\n]*\n(.+?)(?:\n##\s|\Z)", t, re.I | re.S)
    script = (m.group(1).strip() if m else "").strip()
    cap = re.search(r"##\s*Caption\s*\n(.+)", t)
    tags = re.search(r"##\s*Hashtags\s*\n(.+)", t)
    clean_title = re.sub(r"\s*\(.*?script.*?\)\s*$", "", title.group(1).strip(), flags=re.I).strip()
    return {
        "content_id": cid.group(1).strip(),
        "short": cid.group(1).strip().split("-")[0],
        "title": clean_title,
        "script": script,
        "caption": (cap.group(1).strip() if cap else ""),
        "hashtags": (tags.group(1).strip() if tags else ""),
        "scenes_json": None,  # filled below if a plan exists
        "source_pkg": str(p.relative_to(ROOT)),
    }


def _known_full_ids() -> dict[str, str]:
    """Map short (8-char) → full content_id, from scenes.json files and the board.
    Lets us upgrade a publish package's short id (e.g. 'fcf087ea') to the full UUID so we
    match the existing board card and don't clobber it."""
    full: dict[str, str] = {}
    for sj in PLANS_DIR.glob("*.scenes.json"):
        try:
            cid = json.loads(sj.read_text()).get("content_id", "")
        except Exception:
            cid = ""
        if cid:
            full[cid.split("-")[0]] = cid
    for c in load_board():
        cid = c.get("content_id", "")
        if cid and "-" in cid:
            full.setdefault(cid.split("-")[0], cid)
    return full


def gather_topics() -> list[dict]:
    full_ids = _known_full_ids()
    topics: dict[str, dict] = {}   # keyed by short (8-char) to dedupe
    for p in sorted(PKG_DIR.glob("*.md")):
        if "checklist" in p.name:
            continue
        topic = parse_publish_package(p)
        if not (topic and topic["script"]):
            continue
        short = topic["short"]
        # upgrade a short content_id to the known full UUID where available
        topic["content_id"] = full_ids.get(short, topic["content_id"])
        topics.setdefault(short, topic)
    # attach an existing scenes.json (render-ready) by short
    for sj in PLANS_DIR.glob("*.scenes.json"):
        try:
            short = json.loads(sj.read_text()).get("content_id", "").split("-")[0]
        except Exception:
            short = ""
        if short in topics:
            topics[short]["scenes_json"] = str(sj.relative_to(ROOT))
    # render-ready topics (have scenes.json) first → exercises the full pipeline
    return sorted(topics.values(), key=lambda t: (0 if t["scenes_json"] else 1, t["short"]))


# ----------------------------- artifact builders -----------------------------
def render_ready_assets(short: str) -> dict:
    """Find an existing voiceover/timing/render for a topic (only fcf087ea has these today)."""
    vo = next(iter(CR_DIR.glob(f"{short}_*piper_voiceover.wav")), None) or \
        next(iter(CR_DIR.glob(f"{short}_*voiceover*.wav")), None)
    timing = next(iter(CR_DIR.glob(f"{short}_*voiceover_timing.json")), None)
    existing_mp4 = next(iter(HF_RENDERS.glob(f"{short}_*hyperframes_v1.mp4")), None)
    return {"voiceover": vo, "timing": timing, "existing_mp4": existing_mp4}


def write_youtube_short(topic: dict, dry: bool) -> Path:
    out = GEN_SHORTS / f"{topic['short']}_youtube_short.md"
    body = f"""# YouTube Short Draft — {topic['title']}
# prompt: skills/content_prompts/youtube_shorts.md · DRAFT only (no upload/post/schedule)
content_id: {topic['content_id']} · platform: YouTube Shorts · target 30-45s

## Hook
{(topic['script'].splitlines() or [''])[0]}

## Script (≤60s)
{topic['script']}

## Caption
{topic['caption'] or '(derive from script)'}

## Hashtags
{topic['hashtags'] or '#Shorts #businesscredit #smallbusiness'}

## Disclosure / compliance
Educational only — not financial advice. No guarantees.
This content may include affiliate links. If you use a link, Nexus/GoClearOnline may earn a commission at no extra cost to you.

_Generated by run_content_engine_loop.py · {_now()}_
"""
    if not dry:
        out.write_text(body, encoding="utf-8")
    return out


def build_hyperframes_plan(topic: dict, assets: dict, dry: bool) -> tuple[Path, bool]:
    """Build/refresh a HyperFrames composition + plan. Returns (plan_path, render_ready)."""
    plan = GEN_PLANS / f"{topic['short']}_hyperframes_plan.md"
    render_ready = bool(topic["scenes_json"] and assets["voiceover"] and assets["timing"])
    if not dry and render_ready:
        # regenerate the composition from the existing render-ready plan (free/local, no network)
        subprocess.run([sys.executable, str(ROOT / "scripts" / "export_creative_plan_to_hyperframes.py"),
                        "--scenes", str(ROOT / topic["scenes_json"]),
                        "--timing", str(assets["timing"]), "--audio", str(assets["voiceover"]),
                        "--outdir", str(ROOT / "tool-lab" / "hyperframes-shorts")],
                       check=False, capture_output=True)
    plan_body = f"""# HyperFrames Plan — {topic['title']}
# prompt: skills/content_prompts/hyperframes_video.md · DRAFT only
content_id: {topic['content_id']}

- scenes source: {topic['scenes_json'] or '(none yet — generate scenes.json from script, then synth Piper voiceover)'}
- voiceover: {assets['voiceover'].relative_to(ROOT) if assets['voiceover'] else '(needs Piper TTS — queued)'}
- timing: {assets['timing'].relative_to(ROOT) if assets['timing'] else '(needs voiceover timing)'}
- render_ready: {render_ready}
- composition (if render-ready): tool-lab/hyperframes-shorts/index.html
- render output target: reports/tool_lab/hyperframes_renders/{topic['short']}_business_credit_myths_hyperframes_v1.mp4

Style: Nexus palette motion graphics; myth(red ✕)/truth(green ✓) pattern interrupts; kinetic captions; brand + disclosure.
{'' if render_ready else 'NEXT: synthesize a Piper voiceover + timing for this topic, then this plan becomes render-ready.'}

_Generated by run_content_engine_loop.py · {_now()}_
"""
    if not dry:
        plan_body and plan.write_text(plan_body, encoding="utf-8")
    return plan, render_ready


def maybe_render(topic: dict, assets: dict, render_ready: bool, do_render: bool, dry: bool) -> tuple[Path | None, str]:
    """Render a draft MP4 only when render-ready. Idempotent: reuse an existing MP4."""
    if not do_render:
        return None, "render not requested"
    if not render_ready:
        return None, "skipped — not render-ready (needs Piper voiceover + timing)"
    if assets["existing_mp4"] and assets["existing_mp4"].exists():
        return assets["existing_mp4"], "reused existing render (idempotent — no re-render)"
    if dry:
        return None, "dry-run — would render"
    target = HF_RENDERS / f"{topic['short']}_business_credit_myths_hyperframes_v1.mp4"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "render_creative_short_hyperframes.py"),
                           "--project", str(ROOT / "tool-lab" / "hyperframes-shorts"),
                           "--out", str(target)], capture_output=True, text=True)
    if proc.returncode == 0 and target.exists():
        return target, "rendered draft MP4"
    return None, f"render failed (exit {proc.returncode}) — kept plan; not faked"


def write_repurposed(topic: dict, dry: bool) -> Path:
    out = GEN_REPURP / f"{topic['short']}_repurposed.md"
    first = (topic["script"].splitlines() or [""])[0].replace("HOOK:", "").strip()
    body = f"""# Repurposed Assets — {topic['title']}
# prompt: skills/content_prompts/content_repurposing.md · DRAFT only · content_family: fam-{topic['short']}
content_id: {topic['content_id']} · parent_source_id: {topic['source_pkg']}

## LinkedIn post (draft — no auto-posting)
{first}

Here's the part most people skip — and the order that actually works. (Educational only — not financial advice.)
What's the worst advice you've heard on this? 👇

## Newsletter snippet (draft — no send without Ray approval)
{topic['caption'] or first} The boring, correct version beats every "instant" promise. Full breakdown inside.
(Educational only — not financial advice.)

## 3 social captions
1. {first}
2. The one thing most people miss about {topic['title'].lower()}.
3. Save this before you apply anywhere. (Educational, not advice.)

## 3 quote cards
1. "{first}"
2. "Structure and patterns beat shortcuts."
3. "Anyone promising instant results is selling something."

_Generated by run_content_engine_loop.py · {_now()}_
"""
    if not dry:
        out.write_text(body, encoding="utf-8")
    return out


# ----------------------------- scoring -----------------------------
def score_topic(topic: dict, has_render: bool, scenes_n: int) -> tuple[float, dict, bool]:
    text = (topic["script"] + " " + topic["caption"]).lower()
    compliant = not any(b in text for b in BANNED)
    dims = {
        "hook_strength": 8 if topic["script"] else 4,
        "clarity": 8,
        "pacing": 8 if scenes_n >= 3 else 6,
        "visual_potential": 8 if has_render else 6,
        "platform_fit": 9,
        "brand_fit": 8,
        "compliance_safety": 10 if compliant else 4,
        "cta_quality": 8 if re.search(r"\b(cta|comment|follow|save|reply)\b", text) else 6,
        "originality": 7,
        "production_readiness": 8 if has_render else 6,
    }
    overall = round(mean(dims.values()), 1)
    if dims["compliance_safety"] <= 5:
        overall = min(overall, 6.0)
    return overall, dims, compliant


# ----------------------------- main pass -----------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Run one safe internal content engine pass")
    ap.add_argument("--limit", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--topic-source", default="default",
                    choices=["proposed_topics", "research", "default", "manual"])
    ap.add_argument("--content-type", default="youtube_short", choices=["youtube_short"])
    ap.add_argument("--render-hyperframes", action="store_true")
    ap.add_argument("--repurpose", action="store_true")
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--report-path", default=None)
    args = ap.parse_args()

    dry = args.dry_run
    for d in (GEN, GEN_SHORTS, GEN_REPURP, GEN_PLANS, GEN_REPORTS, HF_RENDERS,
              ROOT / "reports" / "content_engine" / "approval_cards"):
        d.mkdir(parents=True, exist_ok=True)

    topics = gather_topics()[: args.limit]
    no_new = not topics
    results = []

    print(f"=== content engine loop ({'DRY-RUN' if dry else 'LIVE'}) · "
          f"source={args.topic_source} · limit={args.limit} · topics={len(topics)} ===")

    for topic in topics:
        assets = render_ready_assets(topic["short"])
        scenes_n = 8 if topic["scenes_json"] else max(3, topic["script"].count("\n\n") + 1)

        yt = write_youtube_short(topic, dry)
        plan, render_ready = build_hyperframes_plan(topic, assets, dry)
        mp4, render_msg = maybe_render(topic, assets, render_ready, args.render_hyperframes, dry)
        repurp = write_repurposed(topic, dry) if args.repurpose else None

        has_render = bool(mp4)
        score, dims, compliant = score_topic(topic, has_render, scenes_n)
        status = "Needs Ray Review" if score >= 7 else "Improve / Retry"

        gen_artifacts = [str(yt.relative_to(ROOT)), str(plan.relative_to(ROOT))]
        if repurp:
            gen_artifacts.append(str(repurp.relative_to(ROOT)))

        # ---- board upsert (MERGE — never clobber, never set Ray-only statuses) ----
        board_action = "skipped (dry-run)"
        if not dry:
            cards = load_board()
            existing = find(cards, topic["content_id"])
            card = dict(existing) if existing else new_card(content_id=topic["content_id"])
            # never let the loop move a card into an Approved*/Published state
            safe_status = status if status in LOOP_SAFE_STATUSES else card.get("status", "Drafted")
            if existing and existing.get("status") in RAY_ONLY_STATUSES:
                safe_status = existing["status"]  # don't drag a Ray-approved card backwards
            card.update({
                "title": topic["title"] or card.get("title", ""),
                "topic": topic["title"], "content_type": "YouTube Short",
                "platform_targets": card.get("platform_targets") or ["YouTube Shorts"],
                "status": safe_status,
                "prompt_used": "youtube_shorts.md+hyperframes_video.md+content_repurposing.md",
                "quality_score": int(round(score)),
                "publish_risk_level": card.get("publish_risk_level") or "external/public",
                "approval_required": True,
                "compliance_status": "pass" if compliant else "fail",
                "disclosure_present": True,
                "recommended_next_action": (
                    "Ray: review draft + preview; decide improve vs approve UNLISTED" if score >= 7
                    else "auto: revise (below quality threshold) — see loop report"),
                "performance_check_status": card.get("performance_check_status", "n/a (pre-publish)"),
                "telegram_summary": f"{topic['short']} · {topic['title']} · score {score}/10 · {safe_status}",
            })
            # merge artifact/preview lists without duplicates
            card["generated_artifacts"] = list(dict.fromkeys((card.get("generated_artifacts") or []) + gen_artifacts))
            card["source_paths"] = list(dict.fromkeys((card.get("source_paths") or []) + [topic["source_pkg"]]))
            if mp4:
                card["preview_paths"] = list(dict.fromkeys((card.get("preview_paths") or []) + [str(mp4.relative_to(ROOT))]))
            saved, created = upsert(card)
            board_action = ("created" if created else "merged") + f" → {saved['status']}"

            # approval card only for review-ready items
            if score >= 7 and safe_status == "Needs Ray Review":
                subprocess.run([sys.executable, str(ROOT / "scripts" / "create_content_approval_card.py"),
                                "--id", topic["content_id"], "--scope", "review",
                                "--out", str(ROOT / "reports" / "content_engine" / "approval_cards" /
                                            f"{topic['short']}_loop_review_approval.md")],
                               check=False, capture_output=True)

        results.append({"topic": topic["title"], "short": topic["short"], "score": score,
                        "status": status, "render": render_msg, "board": board_action,
                        "dims": dims})
        print(f"  • {topic['short']} · {topic['title']}")
        print(f"      score {score}/10 → {status} · render: {render_msg} · board: {board_action}")

    # ---- digest (write-only unless telegram explicitly allowed elsewhere) ----
    digest_path = ROOT / "reports" / "content_engine" / "telegram_digests" / "content_engine_digest_latest.md"
    if not dry:
        cmd = [sys.executable, str(ROOT / "scripts" / "content_board_digest.py")]
        # --send only if telegram allowed AND not suppressed; the digest script itself is still gated.
        if not args.no_telegram:
            cmd.append("--send")
        subprocess.run(cmd, check=False, capture_output=True)

    # ---- loop report ----
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    needs = sum(1 for r in results if r["score"] >= 7)
    retry = sum(1 for r in results if r["score"] < 7)
    report_lines = [
        f"# Content Engine Loop Report — {ts}",
        f"_mode: {'DRY-RUN' if dry else 'LIVE'} · source: {args.topic_source} · limit: {args.limit}_",
        "",
        f"- topics processed: {len(results)}",
        f"- Needs Ray Review (score ≥7): {needs}",
        f"- Improve / Retry (score <7): {retry}",
        f"- render: {'requested' if args.render_hyperframes else 'not requested'} · "
        f"repurpose: {args.repurpose} · telegram: {'suppressed' if args.no_telegram else 'gated'}",
        "",
    ]
    if no_new:
        report_lines.append("**No structured topics found** — nothing processed. "
                            "(fcf087ea fallback applies only when zero topics exist.)")
    for r in results:
        report_lines.append(f"## {r['short']} — {r['topic']}")
        report_lines.append(f"- score: {r['score']}/10 → {r['status']}")
        report_lines.append(f"- render: {r['render']}")
        report_lines.append(f"- board: {r['board']}")
        report_lines.append(f"- dims: {json.dumps(r['dims'])}")
        report_lines.append("")
    report_lines.append("**Safety:** no upload · no post · no schedule · executor disabled · "
                        "no --apply · no paid APIs · no secrets · board merged (not clobbered).")
    report = "\n".join(report_lines)
    report_path = Path(args.report_path) if args.report_path else GEN_REPORTS / f"loop_report_{ts}.md"
    if not dry:
        report_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nloop report: {report_path.relative_to(ROOT)}")
        print(f"digest: {digest_path.relative_to(ROOT)}")
    else:
        print("\n(dry-run: no files or board changes written)")
    print(f"summary: {len(results)} processed · {needs} Needs Ray Review · {retry} Improve/Retry")
    return 0


if __name__ == "__main__":
    sys.exit(main())
