"""
hermes_monetization_today.py
Content-first monetization handler. Reads real local artifacts — never stale exec memory.
Replaces the old generic evidence dump for all monetization/revenue questions.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

_ROOT = Path(__file__).resolve().parent.parent

# Directories scanned for live content assets
_CONTENT_DIRS = [
    _ROOT / "docs" / "reports" / "content",
    _ROOT / "docs" / "content" / "newsletter",
]
_MONETIZATION_DIRS = [
    _ROOT / "docs" / "reports" / "monetization",
]
_FLAGSHIP = _ROOT / "reports" / "flagship_lead_magnet.md"

# Asset type weights — higher = more monetizable right now
_TYPE_SCORES: dict[str, int] = {
    "lead_magnet":        90,
    "short_video_script": 80,
    "newsletter":         75,
    "simplified":         60,
    "cleaned":            50,
    "checklist_draft":    45,
}

_AUDIT_PHRASE_KEYWORDS = frozenset([
    "nexus monetization audit", "run nexus monetization audit",
    "show monetization audit", "monetization audit",
])

_TODAY_PHRASE_KEYWORDS = frozenset([
    "how do we make money today", "how can we make money today",
    "how to make money today", "best money making opportunity",
    "what can make money today", "what can make money this week",
    "best revenue move", "next best money move", "what is our fastest money path",
    "fastest money path", "revenue plan for today", "monetization plan",
    "monetization priorities",
])


class ContentAsset(TypedDict):
    path: str
    name: str
    asset_type: str
    score: int
    date_str: str


def _extract_type(stem: str) -> str:
    for t in ("lead_magnet", "short_video_script", "newsletter",
              "simplified", "cleaned", "checklist_draft"):
        if t in stem:
            return t
    return "other"


def _extract_date(stem: str) -> str:
    m = re.search(r"(\d{8})", stem)
    if m:
        d = m.group(1)
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    return ""


def find_current_content_assets() -> list[ContentAsset]:
    assets: list[ContentAsset] = []

    # Flagship lead magnet (single file)
    if _FLAGSHIP.exists():
        assets.append(ContentAsset(
            path=str(_FLAGSHIP.relative_to(_ROOT)),
            name="flagship_lead_magnet",
            asset_type="lead_magnet",
            score=_TYPE_SCORES["lead_magnet"],
            date_str="2026-05-31",
        ))

    # Content dirs
    for d in _CONTENT_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md"), reverse=True):
            asset_type = _extract_type(p.stem)
            if asset_type == "other":
                continue
            score = score_content_asset_for_monetization(p)
            assets.append(ContentAsset(
                path=str(p.relative_to(_ROOT)),
                name=p.stem,
                asset_type=asset_type,
                score=score,
                date_str=_extract_date(p.stem),
            ))

    # Newsletters in newsletter dir
    for d in [_ROOT / "docs" / "content" / "newsletter"]:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.md"), reverse=True):
            if "newsletter" not in p.stem:
                continue
            already = any(a["name"] == p.stem for a in assets)
            if not already:
                assets.append(ContentAsset(
                    path=str(p.relative_to(_ROOT)),
                    name=p.stem,
                    asset_type="newsletter",
                    score=_TYPE_SCORES["newsletter"],
                    date_str=_extract_date(p.stem),
                ))

    # Deduplicate by name, keep highest score
    seen: dict[str, ContentAsset] = {}
    for a in assets:
        if a["name"] not in seen or a["score"] > seen[a["name"]]["score"]:
            seen[a["name"]] = a

    return sorted(seen.values(), key=lambda x: (-x["score"], x["name"]), reverse=False)


def score_content_asset_for_monetization(path: Path | str) -> int:
    path = Path(path)
    stem = path.stem
    base = _TYPE_SCORES.get(_extract_type(stem), 30)

    # Recency bonus: within last 7 days = +10
    d = _extract_date(stem)
    if d:
        try:
            age = (datetime.now(timezone.utc).date() -
                   datetime.strptime(d, "%Y-%m-%d").date()).days
            if age <= 3:
                base += 10
            elif age <= 7:
                base += 5
        except ValueError:
            pass

    return min(base, 100)


def _latest_monetization_actions() -> str:
    """Return first 6 lines from the most recent top_monetization_actions file."""
    mon_dir = _ROOT / "docs" / "reports" / "monetization"
    if not mon_dir.exists():
        return ""
    files = sorted(mon_dir.glob("top_monetization_actions_*.md"), reverse=True)
    if not files:
        return ""
    try:
        lines = files[0].read_text(encoding="utf-8").splitlines()
        # skip blank title line, return up to first 10 non-empty lines
        out = []
        for ln in lines:
            stripped = ln.strip()
            if stripped and not stripped.startswith("#"):
                out.append(stripped)
            if len(out) >= 6:
                break
        return "\n".join(out)
    except Exception:
        return ""


class MonetizationPlan(TypedDict):
    assets: list[ContentAsset]
    top_actions: str
    has_lead_magnet: bool
    has_newsletter: bool
    has_video_script: bool
    asset_count: int
    latest_newsletter_date: str


def build_today_monetization_plan() -> MonetizationPlan:
    assets = find_current_content_assets()
    top_actions = _latest_monetization_actions()

    has_lead_magnet = any(a["asset_type"] == "lead_magnet" for a in assets)
    has_newsletter = any(a["asset_type"] == "newsletter" for a in assets)
    has_video_script = any(a["asset_type"] == "short_video_script" for a in assets)

    newsletter_dates = [a["date_str"] for a in assets if a["asset_type"] == "newsletter" and a["date_str"]]
    latest_newsletter_date = max(newsletter_dates) if newsletter_dates else ""

    return MonetizationPlan(
        assets=assets[:10],
        top_actions=top_actions,
        has_lead_magnet=has_lead_magnet,
        has_newsletter=has_newsletter,
        has_video_script=has_video_script,
        asset_count=len(assets),
        latest_newsletter_date=latest_newsletter_date,
    )


def format_today_monetization_response(plan: MonetizationPlan) -> str:
    lines = ["TODAY'S MONEY PLAN\n"]

    if plan["asset_count"] == 0:
        lines.append("No content assets found yet. Run a content pipeline cycle to generate assets.")
        lines.append("\nNext step: ask 'what do you recommend' or 'show opportunities'.")
        return "\n".join(lines)

    lines.append("Ready assets:")
    shown = 0
    for a in plan["assets"]:
        if shown >= 5:
            break
        label = a["asset_type"].replace("_", " ").title()
        lines.append(f"  • {label}: {a['name'][:60]}")
        shown += 1

    lines.append("")

    if plan["has_lead_magnet"]:
        lines.append("Move 1: Lead magnet is ready — add CTA to newsletter for email capture.")
    if plan["has_newsletter"] and plan["latest_newsletter_date"]:
        lines.append(f"Move 2: Newsletter ({plan['latest_newsletter_date']}) ready to publish — needs Ray approval.")
    if plan["has_video_script"]:
        lines.append("Move 3: Video script ready — record a short-form video to drive affiliate traffic.")

    if plan["top_actions"]:
        lines.append("\nTop scored actions:")
        for ln in plan["top_actions"].splitlines()[:4]:
            if ln.strip():
                lines.append(f"  {ln.strip()}")

    lines.append("\nApproval boundary: publishing, spending, and sending require Ray's sign-off.")
    lines.append("Run 'nexus monetization audit' for full scored asset list.")
    return "\n".join(lines)


def format_nexus_monetization_audit_response(plan: MonetizationPlan) -> str:
    lines = ["NEXUS MONETIZATION AUDIT\n"]

    if plan["asset_count"] == 0:
        lines.append("No monetizable content assets found in local artifact store.")
        lines.append("\nRun a content pipeline cycle to generate assets, then re-run audit.")
        return "\n".join(lines)

    lines.append(f"Assets found: {plan['asset_count']}")
    lines.append("")

    type_groups: dict[str, list[ContentAsset]] = {}
    for a in plan["assets"]:
        type_groups.setdefault(a["asset_type"], []).append(a)

    for atype, group in sorted(type_groups.items(), key=lambda x: -max(a["score"] for a in x[1])):
        label = atype.replace("_", " ").title()
        best = max(group, key=lambda a: a["score"])
        lines.append(f"{label} ({len(group)} file{'s' if len(group) > 1 else ''}):")
        lines.append(f"  Latest: {best['name'][:55]} | score: {best['score']}")

    if plan["top_actions"]:
        lines.append("\nTop monetization actions:")
        for ln in plan["top_actions"].splitlines()[:5]:
            if ln.strip():
                lines.append(f"  {ln.strip()}")

    lines.append("\nApproval boundary: no publishing, spending, or sending without Ray sign-off.")
    lines.append("Say 'what is the next best move' for a single recommended action.")
    return "\n".join(lines)


def is_monetization_audit_phrase(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _AUDIT_PHRASE_KEYWORDS)


def is_monetization_today_phrase(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _TODAY_PHRASE_KEYWORDS)
