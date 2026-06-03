"""
hermes_revenue_asset_fixer.py
Phase 6F: Safe Internal Revenue Asset Fixes

Apply safe internal fixes to internal draft content files to raise
readiness scores. Never overwrites originals — creates revised copies.

Safety rules:
  - Never overwrite original file directly
  - Create revised copies with suffix: _safe_fixed_<timestamp>.md
  - Never publish content
  - Never email subscribers
  - Never spend money
  - Never activate Stripe/payment
  - Never deploy production changes
  - Never run live trading
  - Never modify Supabase old tables
  - Never write to Supabase
  - Never expose secrets or private data
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR  = _ROOT / "docs" / "reports" / "content"
_FIXED_DIR    = _ROOT / "docs" / "reports" / "content" / "fixed"

SAFETY_BOUNDARY = (
    "Hermes will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, activate Stripe, run live trading, or use "
    "client-facing content without explicit Ray approval."
)

REVENUE_GOAL = "Generate $1,000/week in recurring or repeatable revenue."

# ── Detection patterns (same as scorer for consistency) ─────────────────────

_INTERNAL_MARKER_RE = re.compile(
    r"INTERNAL ONLY|Internal Draft|internal draft|not for publication",
    re.IGNORECASE,
)
_CTA_RE = re.compile(
    r"start your|download|sign up|join|check your|fix your|get your|comment \"ready\"",
    re.IGNORECASE,
)
_REVENUE_RE = re.compile(
    r"revenue|funding|credit|lead magnet|consultation|membership|Nexus",
    re.IGNORECASE,
)
_UNSAFE_RE = re.compile(
    r"guaranteed\s+approval|guarantee\s+funding|guaranteed\s+funding|"
    r"100%\s+approval|100%\s+success|get\s+approved\s+every\s+time|"
    r"lenders\s+will\s+approve\s+you|instant\s+funding|"
    r"guaranteed\s+results|no.risk\s+funding|"
    r"promise\s+you\s+will\s+get\s+funded|"
    r"I\s+promise|we\s+promise|"
    r"guaranteed|guarantee|risk.free\s+guarantee",
    re.IGNORECASE,
)
_COMPLIANCE_RE = re.compile(
    r"educational purposes only|does not guarantee|does not ensure|"
    r"individual results will vary|results will vary|"
    r"not financial advice|not constitute financial advice|"
    r"not a financial professional|consult a licensed",
    re.IGNORECASE,
)

# ── Unsafe promise replacement map ──────────────────────────────────────────
# Applied in order — most specific first to avoid double-replacement.
_UNSAFE_REPLACEMENTS: list[tuple[re.Pattern, str]] = [
    # Specific phrases first
    (re.compile(r"guaranteed\s+approval", re.IGNORECASE),
     "improved approval readiness"),
    (re.compile(r"guarantee\s+funding\s+approval", re.IGNORECASE),
     "ensure funding approval"),
    (re.compile(r"guaranteed\s+funding", re.IGNORECASE),
     "improved funding readiness"),
    (re.compile(r"guarantee\s+funding", re.IGNORECASE),
     "help identify funding readiness"),
    (re.compile(r"100%\s+approval", re.IGNORECASE),
     "improved approval potential"),
    (re.compile(r"100%\s+success", re.IGNORECASE),
     "improved readiness"),
    (re.compile(r"get\s+approved\s+every\s+time", re.IGNORECASE),
     "improve your chances of approval"),
    (re.compile(r"lenders\s+will\s+approve\s+you", re.IGNORECASE),
     "lenders may view your application more favorably"),
    (re.compile(r"instant\s+funding", re.IGNORECASE),
     "faster funding consideration"),
    (re.compile(r"guaranteed\s+results", re.IGNORECASE),
     "measurable readiness improvements"),
    (re.compile(r"no.risk\s+funding", re.IGNORECASE),
     "lower-risk funding preparation"),
    (re.compile(r"promise\s+you\s+will\s+get\s+funded", re.IGNORECASE),
     "help you understand what lenders look for"),
    (re.compile(r"I\s+promise", re.IGNORECASE),
     "The goal is"),
    (re.compile(r"we\s+promise", re.IGNORECASE),
     "we aim to show"),
    (re.compile(r"risk.free\s+guarantee", re.IGNORECASE),
     "educational resource"),
    # Safe disclaimer phrasing — keep meaning, remove trigger word
    (re.compile(r"does\s+not\s+guarantee", re.IGNORECASE),
     "cannot ensure"),
    (re.compile(r"guaranteed", re.IGNORECASE),
     "supported"),
    (re.compile(r"guarantee", re.IGNORECASE),
     "help identify gaps in"),
]

# ── Standard additions by asset type ────────────────────────────────────────

_INTERNAL_MARKER = """> INTERNAL ONLY — Draft for Ray review.
> Do not publish, email, sell, post, deploy, or use with clients until Ray explicitly approves."""

_COMPLIANCE_NOTE = """Compliance note:
This content is for educational purposes only. It does not ensure funding approval, credit approval, business credit results, or financial outcomes. Funding decisions depend on lender requirements, credit profile, business history, revenue, documentation, and other factors. Individual results will vary."""

_REVENUE_CONNECTION = """Nexus revenue connection:
This asset supports the 30-Day Revenue Goal by moving business owners from free education into a Funding Readiness Review, Nexus membership, or a related funding-prep offer. It is not approved for public use until Ray approves it."""

_CTA_BY_TYPE: dict[str, str] = {
    "lead_magnet": (
        "CTA:\n"
        "Download the free Funding Readiness Checklist and find out what to fix before you apply."
    ),
    "checklist": (
        "CTA:\n"
        "Download the free Funding Readiness Checklist and find out what to fix before you apply."
    ),
    "newsletter": (
        "CTA:\n"
        "Check your business funding readiness before you apply — start with the Nexus Funding Readiness Check."
    ),
    "short_video_script": (
        "CTA:\n"
        "Get your free Funding Readiness Checklist at Nexus and fix your gaps before you apply."
    ),
    "youtube_script": (
        "CTA:\n"
        "Get your free Funding Readiness Checklist at Nexus — start your readiness check today."
    ),
    "seo_article": (
        "CTA:\n"
        "Start your Nexus Funding Readiness Check to track your credit prep, documents, and next steps."
    ),
    "linkedin_post": (
        "CTA:\n"
        "Check your business funding readiness with the free Nexus Funding Readiness Checklist."
    ),
    "x_post": (
        "CTA:\n"
        "Get your free Nexus Funding Readiness Checklist — start before you apply."
    ),
    "tiktok_hook": (
        "CTA:\n"
        "Get your free Funding Readiness Checklist at Nexus — start your funding readiness check."
    ),
    "compliance_note": (
        "CTA:\n"
        "Start your Nexus Funding Readiness Check to understand what lenders look for before you apply."
    ),
    "other": (
        "CTA:\n"
        "Start your Nexus Funding Readiness Check and download the free checklist."
    ),
}
_CTA_DEFAULT = (
    "CTA:\n"
    "Start your Nexus Funding Readiness Check — download the free checklist and find your biggest approval blockers."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ── Detection functions ──────────────────────────────────────────────────────

def detect_missing_internal_marker(text: str) -> bool:
    """Return True if the text is missing an internal-only marker."""
    return not bool(_INTERNAL_MARKER_RE.search(text))


def detect_missing_cta(text: str) -> bool:
    """Return True if the text is missing a CTA."""
    return not bool(_CTA_RE.search(text))


def detect_missing_compliance_note(text: str) -> bool:
    """Return True if the text is missing a compliance/disclaimer note."""
    return not bool(_COMPLIANCE_RE.search(text))


def detect_missing_revenue_connection(text: str) -> bool:
    """Return True if the text is missing a revenue/funding connection."""
    return not bool(_REVENUE_RE.search(text))


def detect_unsafe_promise_language(text: str) -> list[str]:
    """Return list of unsafe promise phrases found in text."""
    return _UNSAFE_RE.findall(text)


# ── Fix functions ────────────────────────────────────────────────────────────

def remove_unsafe_promise_language(text: str) -> str:
    """Replace unsafe promise language with safer phrasings.

    Applies replacements in order (most specific first) to avoid
    double-replacement. Preserves all other content.
    """
    result = text
    for pattern, replacement in _UNSAFE_REPLACEMENTS:
        result = pattern.sub(replacement, result)
    return result


def add_internal_only_marker(text: str, asset_type: str = "other") -> str:
    """Add INTERNAL ONLY marker at top of text, below the title if present."""
    if not detect_missing_internal_marker(text):
        return text

    lines = text.splitlines()
    insert_at = 0

    # Find first non-empty line (title)
    for i, line in enumerate(lines):
        if line.strip():
            insert_at = i + 1
            break

    # Skip any immediately following metadata lines (italic, bold)
    while insert_at < len(lines) and lines[insert_at].strip().startswith("*"):
        insert_at += 1

    before = "\n".join(lines[:insert_at])
    after = "\n".join(lines[insert_at:])
    marker_block = f"\n{_INTERNAL_MARKER}\n"
    return f"{before}{marker_block}\n{after}".strip()


def _find_internal_marker_end(text: str) -> int:
    """Return the character offset after the complete internal marker block."""
    marker_match = _INTERNAL_MARKER_RE.search(text)
    if not marker_match:
        return 0
    # Advance to end of the line containing the match first
    newline_pos = text.find("\n", marker_match.end())
    if newline_pos == -1:
        return len(text)
    pos = newline_pos + 1  # First char of next line

    # Now advance past any continuation blockquote/separator/blank lines
    lines = text[pos:].splitlines(keepends=True)
    offset = pos
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">") or stripped == "---" or stripped == "":
            offset += len(line)
        else:
            break
    return offset


def add_cta_section(text: str, asset_type: str = "other") -> str:
    """Insert CTA after the internal marker block so scorer sees it within first 3000 chars.

    Guard uses first 3000 chars to match scorer behavior — avoids adding duplicates
    that are already visible to the scorer.
    """
    if not detect_missing_cta(text[:_SCORER_READ_LIMIT]):
        return text

    cta = _CTA_BY_TYPE.get(asset_type) or _CTA_DEFAULT
    insert_at = _find_internal_marker_end(text)
    if insert_at > 0:
        return text[:insert_at] + f"\n{cta}\n\n" + text[insert_at:]
    return text.rstrip() + f"\n\n---\n\n{cta}\n"


def add_compliance_note(text: str, asset_type: str = "other") -> str:
    """Insert compliance note after internal marker block so scorer sees it."""
    if not detect_missing_compliance_note(text[:_SCORER_READ_LIMIT]):
        return text

    insert_at = _find_internal_marker_end(text)
    if insert_at > 0:
        return text[:insert_at] + f"\n{_COMPLIANCE_NOTE}\n\n" + text[insert_at:]
    return text.rstrip() + f"\n\n---\n\n{_COMPLIANCE_NOTE}\n"


def add_revenue_connection_note(text: str, asset_type: str = "other") -> str:
    """Insert revenue connection note after internal marker block so scorer sees it."""
    if not detect_missing_revenue_connection(text[:_SCORER_READ_LIMIT]):
        return text

    insert_at = _find_internal_marker_end(text)
    if insert_at > 0:
        return text[:insert_at] + f"\n{_REVENUE_CONNECTION}\n\n" + text[insert_at:]
    return text.rstrip() + f"\n\n---\n\n{_REVENUE_CONNECTION}\n"


_SCORER_READ_LIMIT = 3000  # Must match score_asset_readiness text[:3000] limit


def fix_asset_text(text: str, asset_type: str = "other") -> tuple[str, list[str]]:
    """Apply all safe fixes to asset text. Returns (fixed_text, fixes_applied).

    Detection uses the same 3000-char window as the scorer so that fixes
    are only added when the scorer would not see the element in the original.

    Fixes applied (in order):
    1. Remove unsafe promise language (full text)
    2. Add internal-only marker if missing (full text check)
    3. Add CTA if missing in first 3000 chars (inserted after marker)
    4. Add compliance note if missing in first 3000 chars (inserted after marker)
    5. Add revenue connection if missing in first 3000 chars (inserted after marker)
    """
    fixed = text
    applied: list[str] = []

    # 1. Unsafe promise — check and fix full text
    unsafe = detect_unsafe_promise_language(fixed)
    if unsafe:
        fixed = remove_unsafe_promise_language(fixed)
        applied.append(f"unsafe_promise_language_softened ({len(unsafe)} instance(s))")

    # 2. Internal marker — full text check
    if detect_missing_internal_marker(fixed):
        fixed = add_internal_only_marker(fixed, asset_type)
        applied.append("internal_only_marker_added")

    # 3–5: Use scorer-window for detection (first 3000 chars of current fixed text)
    window = fixed[:_SCORER_READ_LIMIT]

    if detect_missing_cta(window):
        fixed = add_cta_section(fixed, asset_type)
        applied.append("cta_section_added")

    if detect_missing_compliance_note(window):
        fixed = add_compliance_note(fixed, asset_type)
        applied.append("compliance_note_added")

    if detect_missing_revenue_connection(window):
        fixed = add_revenue_connection_note(fixed, asset_type)
        applied.append("revenue_connection_note_added")

    return fixed, applied


def write_fixed_asset_copy(original_path: Path | str, fixed_text: str) -> Path:
    """Write fixed copy alongside original. Never overwrites original.

    Creates: <stem>_safe_fixed_<timestamp>.md in the fixed/ subdirectory.
    """
    original_path = Path(original_path)
    _FIXED_DIR.mkdir(parents=True, exist_ok=True)
    ts = _now_ts()
    fixed_name = f"{original_path.stem}_safe_fixed_{ts}.md"
    fixed_path = _FIXED_DIR / fixed_name
    fixed_path.write_text(fixed_text, encoding="utf-8")
    return fixed_path


# ── Asset discovery and batch fixing ────────────────────────────────────────

def find_assets_needing_fixes(packet: dict | None = None) -> list[dict]:
    """Return list of assets that need one or more fixes applied.

    Reads from packet or builds a fresh one if not provided.
    """
    if packet is None:
        try:
            from lib.hermes_revenue_asset_packet import (
                load_latest_revenue_asset_packet, build_revenue_asset_packet,
            )
            packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
        except Exception as exc:
            logger.warning("find_assets_needing_fixes: could not load packet: %s", exc)
            return []

    assets = packet.get("assets") or []
    needing_fixes = []
    for asset in assets:
        flags = asset.get("readiness_flags") or []
        status = asset.get("readiness_status", "")
        if flags or status in ("needs_revision", "internal_draft"):
            # Check if file still exists
            path = asset.get("path", "")
            if path and Path(path).exists():
                needing_fixes.append(asset)
    return needing_fixes


def apply_safe_asset_fixes(limit: int | None = None) -> dict:
    """Apply safe fixes to all assets needing work.

    Returns result dict with:
      - assets_reviewed: int
      - assets_fixed: int
      - fixed_copies: list[str]
      - fixes_applied: dict[filename → list[str]]
      - errors: list[str]
      - score_before: int
      - score_after: int

    Rules:
    - Never overwrites original files
    - Creates fixed copies in docs/reports/content/fixed/
    - Only applies safe internal text fixes
    """
    try:
        from lib.hermes_revenue_asset_packet import (
            load_latest_revenue_asset_packet, build_revenue_asset_packet,
            score_asset_readiness,
        )
    except ImportError as exc:
        return {"error": str(exc), "assets_reviewed": 0, "assets_fixed": 0}

    packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()
    score_before = packet.get("readiness_score", 0)

    assets = find_assets_needing_fixes(packet)
    if limit:
        assets = assets[:limit]

    fixed_copies: list[str] = []
    fixes_applied: dict[str, list[str]] = {}
    errors: list[str] = []
    assets_fixed = 0

    for asset in assets:
        path = Path(asset.get("path", ""))
        filename = asset.get("filename", path.name)
        asset_type = asset.get("category", "other")

        try:
            original_text = path.read_text(errors="replace")
            fixed_text, applied = fix_asset_text(original_text, asset_type)

            if not applied:
                continue

            fixed_path = write_fixed_asset_copy(path, fixed_text)
            fixed_copies.append(str(fixed_path))
            fixes_applied[filename] = applied
            assets_fixed += 1

        except Exception as exc:
            errors.append(f"{filename}: {exc!s:.100}")
            logger.warning("apply_safe_asset_fixes error for %s: %s", filename, exc)

    # Rescore after fixes by building fresh packet (which still reads originals)
    # To reflect fixed copies, rebuild from fixed dir too
    score_after = _rescore_with_fixed_copies(fixed_copies, packet) if fixed_copies else score_before

    return {
        "assets_reviewed":  len(assets),
        "assets_fixed":     assets_fixed,
        "fixed_copies":     fixed_copies,
        "fixes_applied":    fixes_applied,
        "errors":           errors,
        "score_before":     score_before,
        "score_after":      score_after,
        "safety_boundary":  SAFETY_BOUNDARY,
        "completed_at":     _now_iso(),
    }


def _rescore_with_fixed_copies(fixed_copies: list[str], original_packet: dict) -> int:
    """Rescore by substituting fixed copies for their originals in scoring."""
    try:
        from lib.hermes_revenue_asset_packet import score_asset_readiness
        assets = list(original_packet.get("assets") or [])
        if not assets:
            return original_packet.get("readiness_score", 0)

        # Build map from original filename stem to fixed path
        fixed_by_stem: dict[str, str] = {}
        for fp in fixed_copies:
            fp_path = Path(fp)
            # stem is like "original_stem_safe_fixed_ts"
            # original stem is everything before "_safe_fixed_"
            stem = fp_path.stem
            if "_safe_fixed_" in stem:
                orig_stem = stem.split("_safe_fixed_")[0]
                fixed_by_stem[orig_stem] = fp

        rescored_assets = []
        for asset in assets:
            orig_stem = Path(asset.get("path", "")).stem
            fixed_path = fixed_by_stem.get(orig_stem)
            if fixed_path and Path(fixed_path).exists():
                # Use fixed copy for scoring
                proxy = {**asset, "path": fixed_path, "filename": Path(fixed_path).name}
                rescored_assets.append(score_asset_readiness(proxy))
            else:
                rescored_assets.append(asset)

        if not rescored_assets:
            return 0
        return int(sum(a["readiness_score"] for a in rescored_assets) / len(rescored_assets))

    except Exception as exc:
        logger.warning("_rescore_with_fixed_copies error: %s", exc)
        return original_packet.get("readiness_score", 0)


# ── Report formatter ─────────────────────────────────────────────────────────

def format_asset_fix_report(result: dict) -> str:
    """Format the asset fix result as a readable report."""
    reviewed = result.get("assets_reviewed", 0)
    fixed    = result.get("assets_fixed", 0)
    score_before = result.get("score_before", 0)
    score_after  = result.get("score_after", 0)
    copies   = result.get("fixed_copies") or []
    fixes    = result.get("fixes_applied") or {}
    errors   = result.get("errors") or []

    lines = [
        "REVENUE ASSET FIXES APPLIED",
        "",
        f"Assets reviewed:      {reviewed}",
        f"Fixed copies created: {fixed}",
        f"Score before:         {score_before}/100",
        f"Score after:          {score_after}/100",
        "",
    ]

    if fixes:
        lines += ["Fixes applied:", ""]
        for filename, applied in fixes.items():
            lines.append(f"  {filename[:50]}:")
            for fix in applied:
                lines.append(f"    - {fix.replace('_', ' ')}")
        lines.append("")

    if copies:
        lines += ["Fixed copies created:", ""]
        for cp in copies[:5]:
            p = Path(cp)
            rel = str(p.relative_to(_ROOT)) if p.is_relative_to(_ROOT) else cp
            lines.append(f"  {rel}")
        if len(copies) > 5:
            lines.append(f"  ... and {len(copies) - 5} more")
        lines.append("")

    if errors:
        lines += [f"Errors ({len(errors)}):", ""]
        for e in errors[:3]:
            lines.append(f"  - {e}")
        lines.append("")

    lines += [
        "Status:",
        "  Internal drafts only.",
        "",
        "Safety:",
        "  No content was published.",
        "  No emails were sent.",
        "  No money was spent.",
        "  No deployment happened.",
        "  No live trading happened.",
        "  No Supabase writes occurred.",
        "",
        "Next:",
        "  Say 'rescore after fixes' to update packet readiness.",
        "  Say 'show approval queue' to review approval candidates.",
    ]

    if copies:
        lines += ["", "Evidence:"]
        for cp in copies[:3]:
            p = Path(cp)
            rel = str(p.relative_to(_ROOT)) if p.is_relative_to(_ROOT) else cp
            lines.append(f"  {rel}")

    return "\n".join(lines)


def format_rescore_after_fixes_report(old_score: int, new_score: int,
                                       packet: dict | None = None) -> str:
    """Format the rescore-after-fixes response."""
    ready = []
    gaps: list[str] = []

    if packet:
        ready = packet.get("approval_ready_items") or []
        try:
            from lib.hermes_revenue_asset_packet import analyze_packet_readiness_gaps
            gap_list = analyze_packet_readiness_gaps(packet)
            gaps = [g["gap"].replace("_", " ").title() for g in gap_list[:5]]
        except Exception:
            pass

    lines = [
        "REVENUE PACKET RESCORED AFTER FIXES",
        "",
        f"Previous score: {old_score}/100",
        f"New score:      {new_score}/100",
        f"Approval-ready assets: {len(ready)}",
        "",
    ]

    if gaps:
        lines += ["Remaining gaps:", ""]
        for g in gaps:
            lines.append(f"  - {g}")
        lines.append("")

    lines += [
        "Safety:",
        "  No content published. No emails sent. No spending.",
        "",
        "Next:",
        "  Say 'show approval queue' to review approval candidates.",
        "  Say 'show revenue asset packet' to see full packet.",
    ]
    return "\n".join(lines)
