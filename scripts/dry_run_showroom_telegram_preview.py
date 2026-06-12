#!/usr/bin/env python3
"""
Dry-run: generate Telegram review package preview text (no send).
Prints the message that WOULD be sent so Ray can review before any Telegram delivery.

Usage:
  python3 scripts/dry_run_showroom_telegram_preview.py
  python3 scripts/dry_run_showroom_telegram_preview.py --package monetization_pack_v2
  python3 scripts/dry_run_showroom_telegram_preview.py --save reports/showroom/telegram_review_package_preview.md

Safety:
  - Does NOT send any Telegram message
  - Does NOT publish anything
  - Does NOT call any external API
  - Read-only: only reads the local showroom registry
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib import showroom_assets as SA  # noqa: E402

LOCAL_REVIEW_URL = "http://localhost:3000/admin/showroom"
DEFAULT_PACKAGE = "monetization_pack_v2"


def _status_icon(status: str) -> str:
    return {
        "needs_review": "🔍",
        "approved": "✅",
        "approved_with_notes": "📝",
        "revise": "🔄",
        "revised": "✅",
        "ready_to_publish_pending_approval": "⏳",
        "archived": "📦",
    }.get(status, "❓")


def build_package_summary(package_id: str | None = None) -> str:
    assets = SA.recent(100)
    if package_id:
        filtered = [a for a in assets if a.get("asset_type") == package_id]
    else:
        filtered = assets

    if not filtered:
        return f"SHOWROOM REVIEW PACKAGE\n\nNo assets found{' for ' + package_id if package_id else ''}."

    # Group by package
    packages: dict[str, list[dict]] = {}
    for a in filtered:
        pkg = a.get("asset_type", "uncategorized")
        packages.setdefault(pkg, []).append(a)

    reg = SA.load()
    pkg_meta = reg.get("packages", {})

    lines = ["Nexus created a review package:", ""]

    for pkg_id, pkg_assets in sorted(packages.items()):
        if package_id and pkg_id != package_id:
            continue
        title = pkg_id.replace("_", " ").title()
        meta = pkg_meta.get(pkg_id, {})
        pkg_status = meta.get("status", "needs_review")

        lines.append(f"📂 {title} ({len(pkg_assets)} assets)")
        lines.append(f"   Package status: {pkg_status.replace('_', ' ')}")
        lines.append("")

        for a in sorted(pkg_assets, key=lambda x: x.get("title", "")):
            icon = _status_icon(a.get("status", "needs_review"))
            status = a.get("status", "needs_review").replace("_", " ")
            title_short = a.get("title", "Untitled")[:50]
            lines.append(f"  {icon} {title_short} — {status}")
            # Last feedback note if available
            fb = a.get("feedback", [])
            if fb:
                last = fb[-1].get("note", "")[:60]
                if last:
                    lines.append(f"     ↳ {last}")

        lines.append("")

    lines.append(f"───")
    lines.append(f"Open review page: {LOCAL_REVIEW_URL}")
    lines.append("")
    lines.append("Quick actions:")
    lines.append("  • View and approve individual assets in the Showroom GUI")
    lines.append("  • Set package-level status (approved_for_manual_use_only / needs_revision / blocked)")
    lines.append("  • Feedback is saved to content_feedback_latest.json for future content loops")
    lines.append("")
    lines.append("What this preview does NOT do:")
    lines.append("  • Does NOT publish anything")
    lines.append("  • Does NOT send emails")
    lines.append("  • Does NOT send DMs")
    lines.append("  • Does NOT activate payment/Stripe")
    lines.append("  • Does NOT deploy")

    return "\n".join(lines)


def build_beta_packet_summary() -> str:
    """Focused summary for the Credit/Funding Consultant beta launch packet."""
    pkg_id = "monetization_pack_v2"
    assets = [a for a in SA.recent(100) if a.get("asset_type") == pkg_id]

    if not assets:
        return "CREDIT/FUNDING BETA PACKET\n\nNo beta packet assets found."

    reg = SA.load()
    meta = reg.get("packages", {}).get(pkg_id, {})
    pkg_status = meta.get("status", "needs_review")

    lines = [
        "CREDIT & FUNDING CONSULTANT — BETA LAUNCH PACKET",
        "",
        f"Package status: {pkg_status.replace('_', ' ')}",
        f"{len(assets)} assets",
        "",
        "─── ASSET STATUS ───",
        "",
    ]

    # Define the expected beta assets and their display order
    beta_assets = {
        "README": "asset_4a647d2f",
        "Landing page draft": "asset_0b594c89",
        "Lead magnet": "asset_84825f05",
        "Newsletter 01": "asset_8b295931",
        "Newsletter 02": "asset_9bb84396",
        "Newsletter 03": "asset_a2949d43",
        "Newsletter 04": "asset_cd7a49d7",
        "Video scripts": "asset_9087c2a2",
        "Social posts": "asset_1a1729b0",
        "30-day calendar": "asset_52d6f8ed",
        "Compliance notes": "asset_e1c8c8aa",
        "Review checklist": "asset_525c9b18",
        "Revision notes": "asset_45f41016",
        "Beta intake questions": "asset_c46afe22",
        "Beta outreach message": "asset_7a6143a0",
        "Manual invoice plan": "asset_15c19f49",
        "Payment tracker": "asset_6e343a18",
        "Close script": "asset_355c96b6",
        "Launch packet index": "asset_d7eb86dc",
    }

    asset_map = {a["asset_id"]: a for a in assets}

    for label, aid in beta_assets.items():
        a = asset_map.get(aid)
        if a:
            icon = _status_icon(a.get("status", "needs_review"))
            status = a.get("status", "needs_review").replace("_", " ")
            lines.append(f"  {icon} {label}: {status}")
            fb = a.get("feedback", [])
            if fb:
                last = fb[-1].get("note", "")[:60]
                if last:
                    lines.append(f"     ↳ {last}")
        else:
            lines.append(f"  ❓ {label}: not registered")

    lines += [
        "",
        "───",
        f"Open review page: {LOCAL_REVIEW_URL}",
        "",
        "Quick actions:",
        "  • Approve individual assets in the Showroom GUI",
        "  • Approve package for manual use only",
        "  • Request revisions",
        "",
        "What this does NOT authorize:",
        "  ❌ Publishing",
        "  ❌ Email sends",
        "  ❌ DMs to prospects",
        "  ❌ Stripe/payment activation",
        "  ❌ Production deployment",
    ]

    return "\n".join(lines)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Dry-run Telegram review package preview (no send).")
    ap.add_argument("--package", help="Filter by asset_type (e.g. monetization_pack_v2)")
    ap.add_argument("--beta", action="store_true", help="Show Credit/Funding beta packet summary")
    ap.add_argument("--save", help="Save output to file path")
    args = ap.parse_args()

    if args.beta:
        text = build_beta_packet_summary()
    else:
        text = build_package_summary(args.package)

    print(text)

    if args.save:
        path = Path(args.save)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"\n--- Saved to {path} ---")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
