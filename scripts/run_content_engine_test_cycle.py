#!/usr/bin/env python3
"""
run_content_engine_test_cycle.py — orchestrate ONE day of the expanded controlled content test.

THIN orchestrator. Reuses (never duplicates) the existing scripts:
  * Day 1 (script→video):  scripts/run_content_engine_loop.py
  * Day 2 (viral research): scripts/run_viral_pattern_scout.py   (the ONLY scout; free, no paid LLM)
  * Telegram requests:      scripts/create_telegram_approval_request.py
  * Digest:                 scripts/content_board_digest.py

Quality-gated: low-quality ideas become board cards only (not videos); renders happen only for render-ready
candidates at/above the threshold (handled by the content loop). Telegram approval requests are CREATED
(write-only) for Needs-Ray-Review / controlled-test-candidate items; they never execute a broad action.

SAFETY (hard): no upload/post/schedule/email · no paid API · NO paid/OpenRouter LLM (--no-paid-llm) ·
never enables the executor · never runs --apply · never sets Approved*/Published · no secrets · merge-only board.

Usage (see expanded_content_engine_test_plan.md):
  python scripts/run_content_engine_test_cycle.py --day 1 --expanded --limit 5 --max-renders 3 \
      --quality-threshold 7 --render --repurpose --telegram-approvals --no-telegram --dry-run
  python scripts/run_content_engine_test_cycle.py --day 2 --expanded --viral-patterns --max-searches 20 \
      --max-patterns 20 --max-ideas 8 --max-renders 5 --quality-threshold 7 --render --repurpose \
      --no-paid-llm --telegram-approvals --no-telegram --dry-run
"""
from __future__ import annotations
import argparse, math, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.content_board import load_board, RAY_REVIEW_STATUSES  # noqa: E402

PY = sys.executable
REPORTS = ROOT / "reports" / "content_engine" / "generated" / "loop_reports"
NICHES_DEFAULT = ROOT / "reports" / "content_engine" / "test_niches.txt"


def read_niches(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def create_tg_request(content_id: str, title: str, preview: str, dry: bool) -> str | None:
    if dry:
        return "(dry-run: would create CONTENT_REVIEW request)"
    code, out = run([PY, str(ROOT / "scripts" / "create_telegram_approval_request.py"),
                     "--type", "CONTENT_REVIEW", "--title", title[:120], "--content-id", content_id,
                     "--risk-level", "low", "--preview-path", preview,
                     "--summary", "Controlled-test candidate from expanded content test.",
                     "--allowed-scope", "approve for unlisted/private test only, improve/retry, reject, ask summary",
                     "--blocked-actions", "no public post, no scheduling, no paid tools, no secrets"])
    for line in out.splitlines():
        if line.startswith("request:"):
            return line.strip()
    return f"(request create exit {code})"


def main() -> int:
    ap = argparse.ArgumentParser(description="Expanded content engine test cycle (orchestrator)")
    ap.add_argument("--day", type=int, default=1)
    ap.add_argument("--expanded", action="store_true")
    ap.add_argument("--viral-patterns", action="store_true")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--max-searches", type=int, default=20)
    ap.add_argument("--max-patterns", type=int, default=20)
    ap.add_argument("--max-ideas", type=int, default=8)
    ap.add_argument("--max-renders", type=int, default=5)
    ap.add_argument("--quality-threshold", type=float, default=7.0)
    ap.add_argument("--render-only-if-score", action="store_true", default=True)
    ap.add_argument("--skip-render-below-score", action="store_true", default=True)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--repurpose", action="store_true")
    ap.add_argument("--niches-file", default=str(NICHES_DEFAULT))
    ap.add_argument("--no-paid-llm", action="store_true", default=True)
    ap.add_argument("--telegram-approvals", action="store_true")
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dry = args.dry_run
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log: list[str] = []
    print(f"=== TEST CYCLE Day {args.day} ({'DRY-RUN' if dry else 'LIVE'}) · "
          f"{'viral' if args.viral_patterns else 'script→video'} · no-paid-llm={args.no_paid_llm} ===")

    board_before = {c['content_id'] for c in load_board()}

    if args.viral_patterns:
        # ---- Day 2: viral research across niches (reuse the ONE scout; free; no paid LLM) ----
        niches = read_niches(Path(args.niches_file))[: args.max_searches]
        per = max(1, math.ceil(args.max_searches / max(1, len(niches))))
        searched = 0
        for niche in niches:
            if searched >= args.max_searches:
                break
            lim = min(per, args.max_searches - searched)
            cmd = [PY, str(ROOT / "scripts" / "run_viral_pattern_scout.py"),
                   "--niche", niche, "--limit", str(lim), "--free-only"]
            cmd += ["--dry-run"] if dry else ["--create-board-cards"]
            code, out = run(cmd)
            tail = next((l for l in out.splitlines() if l.startswith("summary:")), f"exit {code}")
            log.append(f"- niche '{niche}' (limit {lim}): {tail}")
            searched += lim
        log.insert(0, f"searched ~{searched} videos across {len(niches)} niches (free yt-dlp; cap {args.max_searches}).")
    else:
        # ---- Day 1: script→video via the content loop (renders render-ready ≥ threshold) ----
        cmd = [PY, str(ROOT / "scripts" / "run_content_engine_loop.py"),
               "--limit", str(min(args.limit, args.max_renders if args.render else args.limit))]
        if args.render:
            cmd.append("--render-hyperframes")
        if args.repurpose:
            cmd.append("--repurpose")
        cmd.append("--no-telegram")
        if dry:
            cmd.append("--dry-run")
        code, out = run(cmd)
        for l in out.splitlines():
            if l.strip().startswith(("•", "summary:")):
                log.append("  " + l.strip())
        log.insert(0, f"content loop exit {code} (render={'on' if args.render else 'off'}, "
                      f"cap renders {args.max_renders}, threshold {args.quality_threshold}).")

    # ---- Telegram approval requests for review-ready / candidate items (write-only) ----
    tg_made = []
    if args.telegram_approvals:
        cards = load_board()
        new_or_review = []
        for c in cards:
            is_new = c["content_id"] not in board_before
            review = c.get("status") in RAY_REVIEW_STATUSES
            candidate = (c.get("status") == "Researched" and (c.get("originality_score") or 0) >= args.quality_threshold)
            already = bool(c.get("telegram_approval_request_id"))
            if (review or candidate or (is_new and candidate)) and not already:
                new_or_review.append(c)
        # rank: review first, then originality; cap to a sane number
        new_or_review.sort(key=lambda c: (0 if c.get("status") in RAY_REVIEW_STATUSES else 1,
                                          -(c.get("originality_score") or 0)))
        for c in new_or_review[: args.max_ideas]:
            preview = (c.get("preview_paths") or [""])[0]
            res = create_tg_request(c["content_id"], c.get("title", ""), preview, dry)
            tg_made.append(f"- {c['board_id']} [{c.get('status')}]: {res}")

    # ---- day report ----
    cards_after = load_board()
    counts: dict[str, int] = {}
    for c in cards_after:
        counts[c.get("status", "?")] = counts.get(c.get("status", "?"), 0) + 1
    body = [f"# Expanded Test Cycle — Day {args.day} ({'DRY-RUN' if dry else 'LIVE'}) — {ts}",
            f"_mode: {'viral research' if args.viral_patterns else 'script→video'} · threshold {args.quality_threshold} · "
            f"no-paid-llm={args.no_paid_llm} · render={'on' if args.render else 'off'}_", "",
            "## Actions", *log, "",
            f"## Board status counts (after)\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(counts.items())), "",
            f"## Telegram approval requests ({'created' if args.telegram_approvals and not dry else 'none/dry'})",
            *(tg_made or ["- none"]), "",
            "**Safety:** no upload · no post · no schedule · no email · executor disabled · no --apply · "
            "no paid API · no paid LLM · no copied scripts/footage · board merge-only."]
    report = "\n".join(body)
    rp = REPORTS / f"test_cycle_day{args.day}_{ts}.md"
    if not dry:
        rp.write_text(report + "\n", encoding="utf-8")
        print(f"\nday report: {rp.relative_to(ROOT)}")
    else:
        print("\n(dry-run: no files or board changes written by sub-tools)")
    print(f"summary: day={args.day} · board cards={len(cards_after)} · "
          f"tg_requests={len(tg_made)} · {'DRY' if dry else 'LIVE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
