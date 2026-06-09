#!/usr/bin/env python3
"""
run_viral_pattern_scout.py — THIN adapter over Nexus's existing YouTube scouts.

Reuses the existing free discovery + source-extraction pipeline and connects it to the
Content Workspace Board + Prompt Library. It does NOT duplicate or replace any existing
scout/intelligence module. It studies successful public videos for PATTERN ONLY (hook/title/
format/pacing) and produces ORIGINAL Nexus angles — never copies scripts or footage.

Reused (not rebuilt):
  * scripts/run_monetization_research_cycle.py  → youtube_search() (free yt-dlp ytsearch) + to_source_extraction()
  * lib/content_board.py                        → board cards (merge-only, never clobber)
  * skills/content_prompts/youtube_viral_pattern_research.md → governing prompt
Downstream routing: youtube_shorts.md → hyperframes_video.md → content_repurposing.md (via the loop later).

HARD SAFETY (defaults): free-only · NO paid APIs · NO paid/OpenRouter LLM · NO upload/post/schedule ·
never enables NEXUS_PUBLISH_EXECUTOR_ENABLED · never runs the executor · never sets Approved*/Published ·
never prints secrets · dry-run writes nothing. Pattern-only (no copied scripts, no copyrighted footage).

Usage:
  python scripts/run_viral_pattern_scout.py --niche "business credit" --limit 3 --free-only --dry-run
  python scripts/run_viral_pattern_scout.py --niche "business credit" --limit 3 --free-only --create-board-cards
  python scripts/run_viral_pattern_scout.py --from-file sources.txt --create-board-cards
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from lib.content_board import load_board, find, new_card, upsert, _now, RAY_ONLY_STATUSES  # noqa: E402

# Reuse the existing free discovery + source-extraction format (no duplicate scout).
try:
    from run_monetization_research_cycle import youtube_search as _reuse_search, to_source_extraction  # noqa: E402
    _REUSED = True
except Exception:
    _reuse_search, to_source_extraction, _REUSED = None, None, False

VP_DIR = ROOT / "reports" / "content_engine" / "viral_patterns"
REPORTS = ROOT / "reports" / "content_engine" / "generated" / "loop_reports"
BANNED = ["guarantee", "guaranteed", "get approved", "approved fast", "make $", "instant approval",
          "get rich", "100%", "overnight", "fast cash"]
LOOP_SAFE = {"Researched", "Drafted", "Improve / Retry", "Archived / Rejected"}


def _free_youtube_search(keyword: str, n: int) -> list[dict]:
    """Free yt-dlp ytsearch — reuse the research cycle's function, else inline fallback (same call)."""
    if _REUSED and _reuse_search:
        return _reuse_search(keyword, n)
    try:
        out = subprocess.run(["yt-dlp", "--flat-playlist", "--dump-json", f"ytsearch{n}:{keyword}"],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        return [{"_error": f"yt-dlp failed: {str(e)[:120]}"}]
    items = []
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        items.append({"title": d.get("title") or "", "video_id": d.get("id") or "",
                      "url": d.get("url") or (f"https://www.youtube.com/watch?v={d.get('id')}" if d.get("id") else ""),
                      "channel": d.get("channel") or d.get("uploader") or "", "views": d.get("view_count"),
                      "duration": d.get("duration"), "snippet": (d.get("description") or "")[:240],
                      "keyword": keyword, "source": "youtube"})
    return items


# ----------------------- manual source mode (--from-file) -----------------------
def load_from_file(path: Path) -> list[dict]:
    items = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("http"):
            vid = ""
            m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{6,})", line)
            if m:
                vid = m.group(1)
            items.append({"title": "", "url": line, "video_id": vid, "channel": "",
                          "views": None, "snippet": "", "source": "manual_url"})
        elif (ROOT / line).exists() or line.endswith((".txt", ".md", ".json", ".vtt", ".srt")):
            p = (ROOT / line) if (ROOT / line).exists() else Path(line)
            txt = ""
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                pass
            items.append({"title": p.stem.replace("_", " "), "url": "", "video_id": "", "channel": "",
                          "views": None, "snippet": txt[:240], "transcript_path": str(p), "source": "manual_transcript"})
        else:
            items.append({"title": line, "url": "", "video_id": "", "channel": "",
                          "views": None, "snippet": "", "source": "manual_note"})
    return items


# ----------------------- pattern extraction (free heuristic) -----------------------
def detect_title_formula(title: str) -> tuple[str, str, str]:
    """Return (title_formula, hook_type, script_structure) from the title text only (pattern, not copy)."""
    t = title.lower().strip()
    if re.match(r"^\s*\d+\b", t) or re.search(r"\b\d+\s+\w+", t):
        return ("number + payoff (e.g. 'N X that …')", "curiosity list", "listicle")
    if "myth" in t or "truth about" in t or "lie" in t or "wrong" in t:
        return ("myth vs truth", "contrarian reveal", "myth-vs-truth")
    if t.startswith(("how to", "how i", "how you")):
        return ("how-to / transformation", "promise of a result", "tutorial")
    if t.endswith("?") or t.startswith(("why", "what", "should")):
        return ("question hook", "open question", "explainer")
    if any(w in t for w in ("stop ", "don't", "avoid", "mistake", "never")):
        return ("warning / mistake callout", "loss-aversion", "mistake-list")
    if any(w in t for w in ("secret", "nobody tells", "they don't want", "hidden")):
        return ("curiosity gap", "withheld information", "reveal")
    if "$" in title or any(w in t for w in ("money", "fund", "cash", "fast")):
        return ("money / outcome", "outcome promise", "explainer")
    return ("statement / declaration", "bold claim", "explainer")


def extract_pattern(item: dict, niche: str) -> dict:
    title = item.get("title") or "(title not captured)"
    title_formula, hook_type, structure = detect_title_formula(title)
    text = (title + " " + (item.get("snippet") or "")).lower()
    cta = {"listicle": "save this / follow for the list",
           "myth-vs-truth": "comment a keyword to get the breakdown",
           "tutorial": "follow for the step-by-step",
           "mistake-list": "save this before you make the mistake",
           "reveal": "comment to get the full reveal",
           "explainer": "follow for more / comment a keyword"}.get(structure, "follow for more")
    retention = ["hook in first 1.5s", "one idea per scene", "open loop early → payoff at end"]
    if structure in ("listicle", "mistake-list"):
        retention.append("numbered countdown keeps viewers to the end")
    if structure == "myth-vs-truth":
        retention.append("pattern interrupt on each myth→truth flip")
    risks = sorted({b for b in BANNED if b in text})
    return {
        "title_formula": title_formula, "hook_type": hook_type, "script_structure": structure,
        "pacing": "fast, mobile pacing; short spoken lines (≤14 words); 1 idea/scene",
        "visual_style": "faceless motion graphics, Nexus palette (navy/blue, myth=red/truth=green)",
        "CTA_style": cta,
        "audience_promise": f"a clear, no-hype takeaway about {niche} they can act on",
        "retention_devices": retention,
        "compliance_risks": risks,
    }


# ----------------------- originality / transformation -----------------------
_STOP = set("the a an of to and or for that this you your with how what why are is in on it".split())


def _words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9$]+", s.lower()) if w not in _STOP and len(w) > 1}


def jaccard(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def nexus_angle(pattern: dict, niche: str, source_title: str) -> tuple[str, str]:
    """Build an ORIGINAL Nexus title using the FORMULA (not the source's words) + a concept."""
    struct = pattern["script_structure"]
    topic = niche.strip() or "business credit"
    title = {
        "listicle": f"3 {topic} moves most founders skip (and the boring order that works)",
        "myth-vs-truth": f"3 {topic} myths that cost you time — and what actually works",
        "tutorial": f"The simple {topic} setup, in the right order",
        "mistake-list": f"3 {topic} mistakes quietly costing founders months",
        "reveal": f"What most {topic} advice gets backwards",
        "explainer": f"{topic.title()}, explained without the hype",
    }.get(struct, f"{topic.title()}: the boring, correct version")
    concept = (f"Original Nexus faceless short using the '{pattern['title_formula']}' structure and "
               f"'{pattern['hook_type']}' hook, but with Nexus's own examples, script, and visuals. "
               f"Educational only; no guarantees; affiliate disclosure if links. No source wording or footage.")
    return title, concept


def score_originality(suggested_title: str, source_title: str, pattern: dict) -> tuple[int, bool, list[str]]:
    j = jaccard(suggested_title, source_title or "")
    score = max(1, min(10, round(10 * (1 - j))))
    too_close = j > 0.5
    notes = [f"title-overlap(jaccard)={j:.2f} vs source",
             "pattern studied = structure only (hook/title/format) — no script or footage captured/reused",
             "no creator impersonation; original Nexus wording + visuals"]
    if pattern["compliance_risks"]:
        notes.append("source title carried risky phrasing → Nexus version must avoid it")
    return score, too_close, notes


# ----------------------- card + board -----------------------
def pattern_id_for(item: dict) -> str:
    key = item.get("url") or item.get("video_id") or item.get("title") or ""
    return "vp-" + hashlib.sha1(key.encode()).hexdigest()[:10]


def stable_content_id(item: dict) -> str:
    key = item.get("url") or item.get("video_id") or item.get("title") or uuid.uuid4().hex
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "nexus-viral:" + key))


def write_pattern_card(pid: str, item: dict, pattern: dict, niche: str, orig: int,
                       too_close: bool, notes: list[str], nx_title: str, nx_concept: str,
                       board_id: str | None, dry: bool) -> Path:
    out = VP_DIR / f"{pid}.md"
    body = f"""# Viral Pattern Card — {pid}
# Pattern study ONLY. No copied script. No copyrighted footage. No impersonation. Original Nexus output.

- pattern_id: {pid}
- source_url: {item.get('url') or '(manual / none)'}
- source_title: {item.get('title') or '(not captured)'}
- source_channel: {item.get('channel') or '(unknown)'}
- source_date: {item.get('date') or '(unknown)'}
- source_views: {item.get('views') if item.get('views') is not None else '(unknown)'}
- niche: {niche}
- topic: {item.get('title') or niche}

## Extracted pattern (structure only)
- hook_type: {pattern['hook_type']}
- title_formula: {pattern['title_formula']}
- script_structure: {pattern['script_structure']}
- pacing: {pattern['pacing']}
- visual_style: {pattern['visual_style']}
- CTA_style: {pattern['CTA_style']}
- audience_promise: {pattern['audience_promise']}
- retention_devices: {', '.join(pattern['retention_devices'])}
- compliance_risks (in source): {', '.join(pattern['compliance_risks']) or 'none detected'}

## Transformation (model, don't copy)
- transformation_notes: {' | '.join(notes)}
- originality_score: {orig}/10{'  ⚠ TOO CLOSE TO SOURCE' if too_close else ''}

## Nexus-original output
- suggested Nexus title: {nx_title}
- suggested Nexus script concept: {nx_concept}
- recommended next prompt: skills/content_prompts/youtube_shorts.md → hyperframes_video.md → content_repurposing.md
- governing prompt: skills/content_prompts/youtube_viral_pattern_research.md
- board_id: {board_id or '(not created)'}

_Generated by run_viral_pattern_scout.py · {_now()} · free heuristic extraction · no paid API_
"""
    if not dry:
        out.write_text(body, encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Thin viral pattern scout (reuses existing free scouts)")
    ap.add_argument("--niche", default="business credit")
    ap.add_argument("--query", default=None, help="explicit search query (defaults to --niche)")
    ap.add_argument("--limit", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-file", default=None, help="manual sources file (URLs/titles/notes/transcript paths)")
    ap.add_argument("--no-web", action="store_true", help="skip live discovery (use --from-file only)")
    ap.add_argument("--free-only", action="store_true", default=True, help="free providers only (default on)")
    ap.add_argument("--create-board-cards", action="store_true")
    ap.add_argument("--route-to-content-loop", action="store_true",
                    help="mark strong originals as Drafted + next-prompt so the loop can pick them up")
    ap.add_argument("--report-path", default=None)
    args = ap.parse_args()

    dry = args.dry_run
    VP_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    # ---- discovery ----
    candidates: list[dict] = []
    disc_mode = []
    if args.from_file:
        candidates += load_from_file(Path(args.from_file))
        disc_mode.append(f"from-file:{args.from_file}")
    if not args.no_web and not args.from_file:
        kw = args.query or args.niche
        found = _free_youtube_search(kw, args.limit)
        found = [f for f in found if not f.get("_error") and not f.get("_skipped")]
        candidates += found
        disc_mode.append(f"yt-dlp ytsearch (free):'{kw}'" + ("" if _REUSED else " [inline fallback]"))
    candidates = candidates[: args.limit] if args.limit else candidates

    print(f"=== viral pattern scout ({'DRY-RUN' if dry else 'LIVE'}) · niche='{args.niche}' · "
          f"discovery=[{', '.join(disc_mode) or 'none'}] · candidates={len(candidates)} · free-only={args.free_only} ===")
    if not candidates:
        print("  no candidates (no web/yt-dlp result and no --from-file). Nothing to do; safe exit.")

    results = []
    for item in candidates:
        pattern = extract_pattern(item, args.niche)
        nx_title, nx_concept = nexus_angle(pattern, args.niche, item.get("title", ""))
        orig, too_close, notes = score_originality(nx_title, item.get("title", ""), pattern)
        nx_compliant = not any(b in nx_title.lower() for b in BANNED)
        pid = pattern_id_for(item)
        cid = stable_content_id(item)

        # status rules (never Approved*/Published; never self-advance)
        if not nx_compliant or (too_close and orig < 4):
            status = "Archived / Rejected" if (too_close and orig < 4) else "Improve / Retry"
        elif too_close:
            status = "Improve / Retry"
        elif args.route_to_content_loop and orig >= 7:
            status = "Drafted"
        else:
            status = "Researched"

        board_id = None
        if args.create_board_cards and not dry:
            cards = load_board()
            existing = find(cards, cid)
            card = dict(existing) if existing else new_card(content_id=cid)
            if existing and existing.get("status") in RAY_ONLY_STATUSES:
                safe_status = existing["status"]  # never drag a Ray-approved card backward
            else:
                safe_status = status if status in LOOP_SAFE else "Researched"
            card.update({
                "title": nx_title, "topic": args.niche, "content_type": "YouTube Short",
                "platform_targets": card.get("platform_targets") or ["YouTube Shorts"],
                "status": safe_status,
                "prompt_used": "youtube_viral_pattern_research.md",
                "publish_risk_level": card.get("publish_risk_level") or "external/public",
                "approval_required": True,
                "compliance_status": "pass" if nx_compliant and not pattern["compliance_risks"] else "review",
                "disclosure_present": False,
                "recommended_next_action": (
                    "auto: reject — too close to source / non-compliant" if status in ("Archived / Rejected", "Improve / Retry")
                    else "draft original via youtube_shorts.md → hyperframes_video.md → content_repurposing.md"),
                "source_pattern_id": pid,
                "source_inspiration_urls": list(dict.fromkeys((card.get("source_inspiration_urls") or []) +
                                                              ([item["url"]] if item.get("url") else []))),
                "transformation_notes": " | ".join(notes),
                "originality_score": orig,
                "telegram_summary": f"{pid} · {nx_title[:60]} · orig {orig}/10 · {safe_status}",
            })
            saved, created = upsert(card)
            board_id = saved["board_id"]
            status = saved["status"]

        card_path = write_pattern_card(pid, item, pattern, args.niche, orig, too_close, notes,
                                       nx_title, nx_concept, board_id, dry)
        results.append({"pid": pid, "source_title": item.get("title", ""), "nx_title": nx_title,
                        "orig": orig, "too_close": too_close, "status": status,
                        "structure": pattern["script_structure"], "board_id": board_id,
                        "card_path": str(card_path.relative_to(ROOT))})
        print(f"  • {pid} · src='{(item.get('title') or '(manual)')[:48]}'")
        print(f"      pattern={pattern['script_structure']} · orig={orig}/10{' TOO-CLOSE' if too_close else ''} · "
              f"status={status} · board={board_id or '-'}")

    # ---- report ----
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [f"# Viral Pattern Scout Report — {ts}",
             f"_mode: {'DRY-RUN' if dry else 'LIVE'} · niche: {args.niche} · discovery: {', '.join(disc_mode) or 'none'} · "
             f"reused existing scout: {_REUSED}_", "",
             f"- candidates analyzed: {len(candidates)} · pattern cards: {len(results)}",
             f"- board cards: {'created/updated' if (args.create_board_cards and not dry) else 'not requested'}",
             f"- free-only: {args.free_only} · paid APIs used: NO · paid LLM used: NO", ""]
    for r in results:
        lines += [f"## {r['pid']} — {r['structure']}",
                  f"- source: {r['source_title'] or '(manual)'}",
                  f"- Nexus original: {r['nx_title']}",
                  f"- originality: {r['orig']}/10{'  ⚠ too close' if r['too_close'] else ''} · status: {r['status']}",
                  f"- card: {r['card_path']} · board_id: {r['board_id'] or '-'}", ""]
    lines.append("**Safety:** no upload · no post · no schedule · executor disabled · no paid API · "
                 "no paid LLM · pattern-only (no copied scripts/footage) · board merge-only.")
    report = "\n".join(lines)
    rp = Path(args.report_path) if args.report_path else REPORTS / f"viral_pattern_scout_{ts}.md"
    if not dry:
        rp.write_text(report + "\n", encoding="utf-8")
        print(f"\nreport: {rp.relative_to(ROOT) if rp.is_relative_to(ROOT) else rp}")
    else:
        print("\n(dry-run: no files or board changes written)")
    print(f"summary: {len(results)} pattern(s) · reused-existing-scout={_REUSED} · free-only={args.free_only}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
