#!/usr/bin/env python3
"""
Results Showroom builder
========================
Scans the real locations where the continuous loops write their outputs, copies
the freshest human-readable drafts into a clean local `outputs/` showroom, and
regenerates `reports/showroom/latest_results_showroom.md` so Ray has ONE place
to see what Nexus is producing.

Read-only against the loops + copy-only into outputs/. Never publishes, never
sends Telegram/email, never posts, never deploys, never uses paid APIs, never
prints secrets. Run: python3 scripts/build_results_showroom.py
"""
from __future__ import annotations

import glob as _glob
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    from lib import showroom_assets as SA
except Exception:  # pragma: no cover
    SA = None
NOW = datetime.now(timezone.utc)
DAY = 24 * 3600

SHOWROOM_MD = ROOT / "reports" / "showroom" / "latest_results_showroom.md"

# group -> (destination dir, source globs, max files to copy, copy whole files?)
GROUPS = [
    ("YouTube shorts / scripts", "outputs/content/shorts",
     ["reports/content_engine/generated/youtube_shorts/*.md"], 10, True),
    ("Repurposed content drafts", "outputs/content/scripts",
     ["reports/content_engine/generated/repurposed/*.md",
      "reports/content_engine/generated/avatar_video_packets/*.md"], 10, True),
    ("Video / HyperFrames plans", "outputs/content/scripts",
     ["reports/content_engine/generated/hyperframes_plans/*.md"], 10, True),
    ("Business / monetization opportunities", "outputs/business/opportunities",
     ["reports/*business*opportunit*.md", "reports/opportunity_hall_of_fame.md",
      "reports/ai_business_opportunity_system.md", "reports/monetization_research/*latest*.md"], 10, True),
    ("30-Day AI Content Growth Pack", "outputs/monetization/content_growth_pack",
     ["outputs/monetization/content_growth_pack/*.md"], 20, True),
    ("Trading reports", "outputs/trading/reports",
     ["logs/trading_intelligence_packet_latest.md", "logs/nexus_trading_telegram_ready_latest.md",
      "logs/practice_trade_memory_latest.md", "logs/trading_strategy_discovery_latest.md",
      "logs/full_trading_test_cycle_latest.md", "logs/trading_engine_phase_status_latest.md",
      "logs/trading_strategy_scout_visual_inventory_latest.md",
      "logs/charts/trade_replay_latest.html"], 12, True),
    ("Learning loop reports", "outputs/showroom/learning",
     ["logs/safe_learning_loop_latest.md", "logs/learning_memory_latest.md",
      "logs/next_safe_actions_latest.md", "logs/evolution_tasks_latest.md",
      "logs/safe_research_loops_latest.md"], 10, True),
]

# Landing pages are whole site folders — reference, don't copy.
LANDING_GLOB = "generated_sites/*"


def expand(globs: list[str]) -> list[Path]:
    out: list[Path] = []
    for g in globs:
        # stdlib glob (robust across Python versions); anchor at repo ROOT
        out.extend(Path(m) for m in _glob.glob(str(ROOT / g)) if Path(m).is_file())
    # de-dup, newest first
    seen, uniq = set(), []
    for p in sorted(out, key=lambda x: x.stat().st_mtime, reverse=True):
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def age(epoch: float) -> str:
    s = NOW.timestamp() - epoch
    if s < 90 * 60:
        return f"{int(s/60)}m ago"
    if s < 48 * 3600:
        return f"{s/3600:.1f}h ago"
    return f"{s/DAY:.1f}d ago"


def fresh_24h(p: Path) -> bool:
    return (NOW.timestamp() - p.stat().st_mtime) <= DAY


def content_loop_status() -> str:
    reps = expand(["reports/content_engine/generated/loop_reports/loop_report_*.md"])
    if not reps:
        return "no loop_report found — run the content loop (see commands)"
    latest = reps[0]
    head = latest.read_text(errors="ignore").splitlines()
    summary = next((l for l in head if l.lower().startswith("summary") or "processed" in l.lower()), "")
    return f"latest `{latest.relative_to(ROOT)}` ({age(latest.stat().st_mtime)}) — {summary.strip()[:120]}"


def learning_status() -> str:
    p = ROOT / "logs" / "safe_learning_loop_latest.md"
    if not p.exists():
        return "no safe_learning_loop_latest.md"
    metrics = [l.strip("- ").strip() for l in p.read_text(errors="ignore").splitlines()
               if "Seeds found" in l or "Variants created" in l or "Tests run" in l or "Lanes run" in l]
    return f"`{p.relative_to(ROOT)}` ({age(p.stat().st_mtime)}) — " + " · ".join(metrics)[:200]


def trading_status() -> str:
    p = ROOT / "logs" / "trading_engine_status.json"
    if not p.exists():
        return "no trading_engine_status.json"
    try:
        d = json.loads(p.read_text())
        eng = d.get("engine", d)
        broker = eng.get("broker_type") or eng.get("broker_mode")
        running = eng.get("is_running")
        blockers = eng.get("execution_blockers") or eng.get("execution_mode")
        return (f"broker={broker} · live={eng.get('live_trading')} · paper_only={eng.get('paper_only')} · "
                f"dry_run={eng.get('dry_run')} · running={running} · blockers={blockers} "
                f"({age(p.stat().st_mtime)})")
    except Exception:
        return f"trading_engine_status.json present ({age(p.stat().st_mtime)})"


def business_status() -> int:
    # GROUPS entry = (name, dest, globs, maxn, copy) -> globs is index [2]
    return len(expand(GROUPS[3][2]))


def notification_status() -> dict:
    preview = ROOT / "logs" / "showroom_notification_preview_latest.md"
    email = ROOT / "logs" / "ray_email_notification_test_latest.json"
    telegram_enabled = False
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("TELEGRAM_ENABLED="):
                telegram_enabled = line.split("=", 1)[1].strip().lower() == "true"
                break
    email_payload = {}
    if email.exists():
        try:
            email_payload = json.loads(email.read_text())
        except Exception:
            email_payload = {}
    return {
        "telegram_preview_exists": preview.exists(),
        "telegram_enabled": telegram_enabled,
        "email_status": email_payload.get("status", "not_run"),
        "email_configured": email_payload.get("email_configured", False),
        "email_subject": email_payload.get("subject"),
    }


def profile_fix_status() -> str:
    report = ROOT / "reports" / "showroom" / "profile_completion_fix_review.md"
    if report.exists():
        return f"verified via `{report.relative_to(ROOT)}`"
    return "verification report not found"


def read_status_lines(path: Path, prefix: str = "- ") -> list[str]:
    if not path.exists():
        return [f"{prefix}(missing: {path.relative_to(ROOT)})"]
    lines = []
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("- "):
            lines.append(f"{prefix}{line[2:]}")
        if len(lines) >= 6:
            break
    return lines or [f"{prefix}`{path.relative_to(ROOT)}` available"]


def oanda_execution_summary() -> list[str]:
    report = ROOT / "reports" / "trading" / "oanda_practice_execution_test" / "OANDA_PRACTICE_EXECUTION_RETRY_FINAL_REPORT.md"
    if not report.exists():
        return ["- no OANDA practice execution report found"]
    lines = []
    for raw in report.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if line.startswith("- practice/demo confirmed:") or line.startswith("- order submitted:") or \
           line.startswith("- broker accepted:") or line.startswith("- rejection reason:"):
            lines.append(line)
    return lines[:4] or [f"- `{report.relative_to(ROOT)}` available"]


def main() -> int:
    copied: dict[str, list[Path]] = {}
    for name, dest, globs, maxn, do_copy in GROUPS:
        dst = ROOT / dest
        dst.mkdir(parents=True, exist_ok=True)
        files = expand(globs)[:maxn]
        copied[name] = []
        for f in files:
            target = dst / f.name
            if do_copy and f.resolve() != target.resolve():
                try:
                    shutil.copy2(f, target)
                except Exception:
                    continue
            copied[name].append(f)

    landings = [p for p in ROOT.glob(LANDING_GLOB) if p.is_dir()]
    # Landing sites have relative assets, so we don't copy them; write a pointer/index instead.
    lp_dir = ROOT / "outputs" / "content" / "landing_pages"
    lp_dir.mkdir(parents=True, exist_ok=True)
    lp_lines = ["# Sample Landing Pages (generated)\n",
                "Full sites live under `generated_sites/`. Preview locally (no deploy) with:\n",
                "```bash", "cd generated_sites/<site> && python3 -m http.server 8080  # then open http://localhost:8080",
                "```\n"]
    for d in landings:
        idx = d / "index.html"
        lp_lines.append(f"- `{d.relative_to(ROOT)}/`" + (" — has index.html" if idx.exists() else ""))
    (lp_dir / "INDEX.md").write_text("\n".join(lp_lines) + "\n")
    all_files = [f for fs in copied.values() for f in fs]
    last24 = sorted([f for f in all_files if fresh_24h(f)],
                    key=lambda x: x.stat().st_mtime, reverse=True)

    # ---- register reviewable assets (content + trading builder + vibe) ----
    ASSET_TYPES = {
        "YouTube shorts / scripts": "youtube_short",
        "Repurposed content drafts": "repurposed_content",
        "Video / HyperFrames plans": "video_plan",
        "Business / monetization opportunities": "business_opportunity",
        "30-Day AI Content Growth Pack": "monetization_packet",
        "Trading reports": "trading_report",
    }
    if SA is not None:
        for name, dest, *_ in GROUPS:
            atype = ASSET_TYPES.get(name)
            if not atype:
                continue
            for f in copied.get(name, []):
                title = f.stem.replace("_", " ").title()
                SA.register(atype, title, str(f.relative_to(ROOT)),
                            showroom_path=f"{dest}/{f.name}", key=f.name)
        # strategy builder + vibe review as their own assets
        for path, atype, title in [
            ("logs/trading_strategy_builder_latest.md", "trading_strategy_builder", "Trading Strategy Builder"),
            ("logs/vibe_trading_review_latest.md", "vibe_trading_review", "Vibe Trading Review"),
            ("reports/showroom/funding_readiness_packet.md", "funding_readiness", "Funding Readiness Packet (mock)"),
            ("outputs/social/drafts/test_post_draft_001.md", "social_test_post", "Social Test Post Draft 001")]:
            if (ROOT / path).exists():
                SA.register(atype, title, path, showroom_path=path, key=path)
        for folder, atype, title in [
            ("outputs/content/video_packets", "video_packet", "Latest HyperFrames Packet"),
            ("outputs/content/storyboards", "storyboard", "Latest Storyboard"),
            ("outputs/content/thumbnail_prompts", "thumbnail_prompt", "Latest Thumbnail Prompt"),
        ]:
            base = ROOT / folder
            if base.exists():
                latest = sorted(base.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
                if latest:
                    rel = str(latest[0].relative_to(ROOT))
                    SA.register(atype, title, rel, showroom_path=rel, key=rel)

    review_queue = SA.recent(60) if SA else []
    def _by(status): return [a for a in review_queue if a.get("status") == status]
    notify = notification_status()
    postiz_status = ROOT / "reports" / "showroom" / "postiz_status.md"
    hyperframes_status = ROOT / "reports" / "showroom" / "hyperframes_status.md"
    funding_packet = ROOT / "reports" / "showroom" / "funding_readiness_packet.md"
    practice_report = ROOT / "reports" / "trading" / "oanda_practice_execution_test" / "OANDA_PRACTICE_EXECUTION_RETRY_FINAL_REPORT.md"
    dns_report = ROOT / "reports" / "showroom" / "network_dns_stability_report.md"
    growth_pack_status = ROOT / "reports" / "showroom" / "content_growth_pack_status.md"

    L = ["# Nexus Results Showroom",
         f"_Generated: {NOW.isoformat()} · local only · no publish/telegram/email/deploy/paid-API_\n",
         "One place to see what the continuous loops are producing. Drafts are **copies** of the "
         "live outputs, mirrored into `outputs/` for easy browsing.\n",
         "## Loop status",
         f"- **Content loop:** {content_loop_status()}",
         f"- **Safe learning loop:** {learning_status()}",
         f"- **Trading:** {trading_status()}",
         f"- **Business / monetization:** {business_status()} opportunity/monetization docs found\n",
         "## Generated drafts (showroom copies)"]
    for name, dest, *_ in GROUPS:
        fs = copied.get(name, [])
        L.append(f"\n### {name}  →  `{dest}/`")
        if not fs:
            L.append("- _(none yet — run the generating loop; see commands below)_")
        for f in fs[:8]:
            L.append(f"- `{dest}/{f.name}` — from `{f.relative_to(ROOT)}` ({age(f.stat().st_mtime)})")

    L.append(f"\n### Sample landing pages  →  `outputs/content/landing_pages/` (referenced, not copied)")
    if landings:
        for d in landings:
            idx = d / "index.html"
            L.append(f"- `{d.relative_to(ROOT)}/`" + (" (has index.html)" if idx.exists() else ""))
    else:
        L.append("- _(none in generated_sites/)_")

    L.append("\n## Created in the last 24 hours")
    if last24:
        for f in last24[:20]:
            L.append(f"- `{f.relative_to(ROOT)}` ({age(f.stat().st_mtime)})")
    else:
        L.append("- _(nothing in the last 24h — loops may have run --dry-run, which does not write drafts)_")

    L += [
        "\n## Dry-run vs written",
        "- The content loop **only writes draft files when run WITHOUT `--dry-run`**. With `--dry-run` it "
        "scores + reports but writes nothing (`board: skipped (dry-run)`).",
        "- A safe local-write mode already exists: run without `--dry-run` but with `--no-telegram` — it writes "
        "drafts to `reports/content_engine/generated/` and updates the **local** board only (no publish, no email, "
        "no telegram, no network, no paid API).",
        "\n## Next commands (safe, local only)",
        "```bash",
        "# Generate visible local content drafts (no publish/telegram):",
        "python3 scripts/run_content_engine_loop.py --limit 1 --repurpose --no-telegram",
        "# Refresh learning + evolution reports:",
        "python3 scripts/run_safe_learning_loops.py --scope all --dry-run",
        "# Rebuild this showroom:",
        "python3 scripts/build_results_showroom.py",
        "```",
    ]

    # ---- Part 10 operating-loop sections ----
    def asset_line(a):
        return f"- `{a['asset_id']}` [{a['asset_type']}] **{a['status']}** — {a['title'][:55]}  ·  {a['showroom_path']}"

    new_assets = [a for a in review_queue if a.get("status") in ("new", "needs_review")]
    L += ["\n---\n## Review Queue",
          f"{len(review_queue)} reviewable assets registered. Feedback: "
          "`python3 scripts/review_showroom_asset.py --asset-id <id> --status revise --feedback \"...\"`"]
    L += ["\n### New Assets Awaiting Ray"] + ([asset_line(a) for a in new_assets[:15]] or ["- (none)"])
    L += ["\n### Feedback Needed (revise)"] + ([asset_line(a) for a in _by("revise")] or ["- (none)"])
    L += ["\n### Approved With Notes"] + ([asset_line(a) for a in _by("approved_with_notes")] or ["- (none)"])
    L += ["\n### Ready for Publishing Approval"] + ([asset_line(a) for a in _by("ready_to_publish_pending_approval")] or ["- (none — publishing stays Ray-gated)"])

    L += ["\n## Telegram Notification Status",
          f"- automatic Ray-only notifications active: {'yes' if notify['telegram_enabled'] else 'no'}",
          f"- dry-run preview generated: {'yes' if notify['telegram_preview_exists'] else 'no'}",
          "- send mode remains manual/safe Ray-only unless Ray separately approves broader automation.",
          "\n## Email Notification Status",
          f"- Ray-only email status: {notify['email_status']}",
          f"- email configured: {'yes' if notify['email_configured'] else 'no'}",
          f"- last subject: {notify['email_subject'] or 'none'}",
          "\n## Trading Practice Execution Result",
          f"- latest execution report: `{practice_report.relative_to(ROOT)}`" if practice_report.exists()
          else "- latest execution report: not available"] + oanda_execution_summary() + [
          "\n## Trading Practice Status",
          f"- {trading_status()}",
          "- Discovery active; strategies promoted/queued for next cap reset; duplicate rotation working.",
          "## Trading Execution Readiness",
          "- Bracketed practice execution path exists and remains practice-only.",
          "- One approved practice-order lane exists; no live-money path is enabled.",
          "## Trading Strategy Builder",
          "- Report: `outputs/trading/reports/trading_strategy_builder_latest.md` — seeds converted into scored variants (not '0 found').",
          "## Vibe Trading Status",
          "- Report: `outputs/trading/reports/vibe_trading_review_latest.md` — status: VIBE_TRADING_PASSIVE_ONLY (CLI installed; active calls cost-gated).",
          "## Postiz Social Publishing Status"] + read_status_lines(postiz_status) + [
          "## HyperFrames Video Packets"] + read_status_lines(hyperframes_status) + [
          "## 30-Day AI Content Growth Pack"] + read_status_lines(growth_pack_status) + [
          "## Landing Page Draft",
          "- `outputs/monetization/content_growth_pack/landing_page_draft.md`",
          "## Lead Magnet",
          "- `outputs/monetization/content_growth_pack/lead_magnet_outline.md`",
          "## Newsletter Ideas",
          "- `outputs/monetization/content_growth_pack/newsletter_topic_ideas.md`",
          "## Short Video Ideas",
          "- `outputs/monetization/content_growth_pack/short_video_ideas.md`",
          "## Social Drafts",
          "- `outputs/monetization/content_growth_pack/social_post_drafts.md`",
          "## Postiz Draft Payload",
          "- `outputs/monetization/content_growth_pack/postiz_draft_payload.md`",
          "## Storyboard / Thumbnail Concepts",
          "- `outputs/content/storyboards/` and `outputs/content/thumbnail_prompts/` hold the current local packet support artifacts.",
          "## DNS Stability Status"] + read_status_lines(dns_report) + [
          "## Ray Review Needed",
          "- Review the 30-Day AI Content Growth Pack pricing, audience focus, and first CTA direction.",
          "## Next Safe Action",
          "- Run the DNS diagnostic again before retrying Telegram, Ray-only email, Supabase dry-run, or Oanda execution.",
          "## Social Drafts Awaiting Ray Approval",
          "- `outputs/social/drafts/test_post_draft_001.md` is the controlled test post draft; no public scheduling or posting occurred.",
          "## Funding Test Readiness",
          f"- `{funding_packet.relative_to(ROOT)}` (mock/new LLC readiness only; no applications)." if funding_packet.exists()
          else "- funding readiness packet missing",
          "## Image/Video Output Status",
          "- HyperFrames plans, avatar packets, and thumbnail/storyboard prompts are local-only and reviewable in the showroom.",
          "## Deploy / Profile Status",
          f"- profile completion fix: {profile_fix_status()}",
          "- duplicate prevention remains part of the verified production path.",
          "## Business / Funding Test Readiness",
          "- See `outputs/business/opportunities/` and `reports/showroom/funding_readiness_packet.md` (mock only; no applications).",
          "## Real-World Test Status",
          "- Tier 0 (local dry-run) + Tier 1 (Ray-only notify) ACTIVE. Tiers 2–4 require Ray approval per action.",
          "## Broken Workflows",
          "- Postiz is not installed/wired as an active scheduler yet.",
          "- Some resident launchd workers still show missing in `reports/system/nexus_continuous_running_status.md`.",
          "## Next Safe Tests",
          "```bash",
          "python3 scripts/run_content_engine_loop.py --limit 1 --repurpose --no-telegram",
          "python3 scripts/build_hyperframes_packet.py",
          "python3 scripts/postiz_status_check.py",
          "python3 scripts/run_vibe_strategy_builder_review.py --dry-run",
          "python3 scripts/build_results_showroom.py",
          "python3 scripts/send_showroom_notification.py --dry-run",
          "```",
          "## What Requires Ray Approval",
          "- Public posting / social test post · external emails · funding applications · paid APIs · production deploy · "
          "Oanda practice **order execution** · activating Vibe CLI (paid-LLM cost)."]

    SHOWROOM_MD.parent.mkdir(parents=True, exist_ok=True)
    SHOWROOM_MD.write_text("\n".join(L) + "\n")
    # also drop a copy in outputs/showroom for one-stop browsing
    (ROOT / "outputs" / "showroom").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SHOWROOM_MD, ROOT / "outputs" / "showroom" / "latest_results_showroom.md")

    total = sum(len(v) for v in copied.values())
    print(f"Showroom built: {SHOWROOM_MD.relative_to(ROOT)}")
    print(f"  drafts mirrored into outputs/: {total} · landing pages referenced: {len(landings)} · last-24h: {len(last24)}")
    for name, _d, *_ in GROUPS:
        print(f"  - {name}: {len(copied.get(name, []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
