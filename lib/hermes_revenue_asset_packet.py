"""
hermes_revenue_asset_packet.py
Phase 6D: Revenue Asset Packet + Approval Candidate Generation

Discovers, classifies, scores, and packages current Nexus revenue assets
into a reviewable packet. Generates local approval queue candidates for
public/client-facing next steps.

Output directory: docs/reports/revenue_packets/

Safety rules:
  - Do NOT publish content
  - Do NOT email subscribers
  - Do NOT spend money
  - Do NOT apply to affiliate programs
  - Do NOT activate Stripe/payment
  - Do NOT deploy production changes
  - Do NOT run live trading
  - Do NOT use client-facing content without Ray approval
  - Do NOT write to Supabase (read hermes_memory_v2 only)
  - Do NOT modify old Supabase tables
  - Do NOT store secrets, tokens, raw client data
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR     = _ROOT / "docs" / "reports" / "content"
_PACKET_DIR      = _ROOT / "docs" / "reports" / "revenue_packets"
_LATEST_FILE     = _PACKET_DIR / "latest_revenue_asset_packet.json"
_WRITE_ENABLED   = os.environ.get("HERMES_REVENUE_PACKET_WRITE", "false").lower() == "true"

SAFETY_BOUNDARY = (
    "Hermes will not publish, email subscribers, sell, deploy, spend money, "
    "apply to affiliate programs, activate Stripe, run live trading, or use "
    "client-facing content without explicit Ray approval."
)

REVENUE_GOAL = "Generate $1,000/week in recurring or repeatable revenue."

PRIMARY_OFFER = (
    "Credit/Funding Readiness lead magnet → "
    "readiness audit / consultation / Nexus membership"
)

TARGET_AUDIENCE = (
    "Small business owners who want to apply for business funding "
    "(credit lines, SBA loans, revenue-based financing) and need to "
    "know what to prepare."
)

# ── Asset category constants ────────────────────────────────────────────────

ASSET_CATEGORIES = (
    "lead_magnet",
    "checklist",
    "newsletter",
    "short_video_script",
    "cta_copy",
    "compliance_note",
    "launch_checklist",
    "approval_checklist",
    "youtube_script",
    "tiktok_hook",
    "seo_article",
    "linkedin_post",
    "x_post",
    "other",
)

# Readiness status values
READINESS_STATUSES = (
    "internal_draft",
    "needs_revision",
    "approval_ready",
    "approved",
    "blocked",
)

# CTA options for the packet
CTA_OPTIONS = {
    "short":        "Start your funding readiness check",
    "newsletter":   "See if your business is funding-ready",
    "video":        "Fix your funding gaps before you apply",
    "landing_page": "Download the free checklist",
    "soft":         "Join Nexus to track your readiness",
    "direct":       "Get your free Business Funding Readiness Score",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    _PACKET_DIR.mkdir(parents=True, exist_ok=True)


def _stable_packet_id(name: str) -> str:
    h = hashlib.md5(name.encode(), usedforsecurity=False).hexdigest()[:10]
    return f"pkt_{h}"


# ── Classification helpers ───────────────────────────────────────────────────

_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("lead_magnet",       ["lead_magnet", "scorecard", "lead magnet"]),
    ("newsletter",        ["newsletter", "_newsletter"]),
    ("short_video_script",["short_video_script", "short_video", "video_script", "tiktok"]),
    ("youtube_script",    ["yt_script", "youtube", "youtube_script"]),
    ("seo_article",       ["seo_article", "seo"]),
    ("linkedin_post",     ["linkedin"]),
    ("x_post",            ["x_posts"]),
    ("cta_copy",          ["cta_copy", "_cta"]),
    ("compliance_note",   ["compliance", "disclaimer"]),
    ("launch_checklist",  ["launch_checklist"]),
    ("approval_checklist",["approval_checklist"]),
    ("checklist",         ["checklist", "scorecard"]),
]

_READINESS_SIGNALS = {
    "internal_only_marker": re.compile(
        r"INTERNAL ONLY|Internal Draft|internal draft|not for publication",
        re.IGNORECASE,
    ),
    "unsafe_promise": re.compile(
        r"guaranteed|guarantee|I promise|we promise|100% success|risk.free guarantee",
        re.IGNORECASE,
    ),
    "cta_present": re.compile(
        r"start your|download|sign up|join|check your|fix your|get your",
        re.IGNORECASE,
    ),
    "revenue_connected": re.compile(
        r"revenue|funding|credit|lead magnet|consultation|membership|Nexus",
        re.IGNORECASE,
    ),
}


def classify_revenue_asset(path: Path | str) -> str:
    """Classify a file into an asset category based on filename and content."""
    path = Path(path)
    name_lower = path.stem.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in name_lower for kw in keywords):
            return category
    # Fallback: peek at content
    try:
        text = path.read_text(errors="replace")[:500].lower()
        for category, keywords in _CATEGORY_KEYWORDS:
            if any(kw in text for kw in keywords):
                return category
    except Exception:
        pass
    return "other"


def _has_internal_marker(text: str) -> bool:
    return bool(_READINESS_SIGNALS["internal_only_marker"].search(text))


def _has_unsafe_promise(text: str) -> bool:
    return bool(_READINESS_SIGNALS["unsafe_promise"].search(text))


def _has_cta(text: str) -> bool:
    return bool(_READINESS_SIGNALS["cta_present"].search(text))


def _revenue_connected(text: str) -> bool:
    return bool(_READINESS_SIGNALS["revenue_connected"].search(text))


def score_asset_readiness(asset: dict) -> dict:
    """Score an asset dict and return updated dict with readiness_score and status.

    An asset is approval_ready only if:
      1. It exists (file is present)
      2. It has an internal-only/compliance note
      3. It has a CTA or clear next step
      4. It is connected to the 30-Day Revenue Goal
      5. It does not contain unsafe promises or guarantees
      6. It is not already rejected/deprecated
    """
    score = 0
    flags: list[str] = []

    file_exists = bool(asset.get("path") and Path(asset["path"]).exists())
    text = ""
    if file_exists:
        try:
            text = Path(asset["path"]).read_text(errors="replace")[:3000]
        except Exception:
            pass

    # Criteria scoring
    if file_exists:
        score += 25
    else:
        flags.append("file_not_found")

    has_internal = _has_internal_marker(text)
    if has_internal:
        score += 20
    else:
        flags.append("no_internal_marker")

    has_cta = _has_cta(text)
    if has_cta:
        score += 20
    else:
        flags.append("no_cta_detected")

    rev_connected = _revenue_connected(text)
    if rev_connected:
        score += 20
    else:
        flags.append("not_revenue_connected")

    has_unsafe = _has_unsafe_promise(text)
    if not has_unsafe:
        score += 15
    else:
        flags.append("unsafe_promise_detected")

    # Bonus for being a primary revenue format
    primary_cats = {"lead_magnet", "newsletter", "checklist", "short_video_script"}
    if asset.get("category") in primary_cats:
        score = min(100, score + 5)

    # Determine status
    if not file_exists:
        status = "blocked"
    elif has_unsafe:
        status = "needs_revision"
    elif score >= 75 and has_internal and has_cta and rev_connected:
        status = "approval_ready"
    elif score >= 40:
        status = "internal_draft"
    else:
        status = "needs_revision"

    return {
        **asset,
        "readiness_score": score,
        "readiness_status": status,
        "readiness_flags": flags,
        "text_preview": text[:200].strip() if text else "",
    }


# ── Asset discovery ──────────────────────────────────────────────────────────

def discover_revenue_assets() -> list[dict]:
    """Find all content assets across reports/content and docs/content directories.

    Returns list of asset dicts with path, category, filename, modified_at.
    Picks the most recent version of each logical asset type.
    """
    search_dirs = [
        _CONTENT_DIR,
        _ROOT / "docs" / "content",
    ]

    raw: list[dict] = []
    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for fpath in search_dir.rglob("*.md"):
            try:
                stat = fpath.stat()
                raw.append({
                    "filename":    fpath.name,
                    "path":        str(fpath),
                    "category":    classify_revenue_asset(fpath),
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "size_bytes":  stat.st_size,
                })
            except Exception:
                continue

    if not raw:
        return []

    # Deduplicate: keep most recent per category
    by_category: dict[str, dict] = {}
    for asset in raw:
        cat = asset["category"]
        existing = by_category.get(cat)
        if existing is None or asset["modified_at"] > existing["modified_at"]:
            by_category[cat] = asset

    result = list(by_category.values())
    result.sort(key=lambda a: a.get("modified_at", ""), reverse=True)
    return result


# ── Packet builders ──────────────────────────────────────────────────────────

def build_cta_options(packet: dict | None = None) -> dict:
    """Return the CTA options dict."""
    return dict(CTA_OPTIONS)


def build_launch_checklist(packet: dict | None = None) -> dict:
    """Build the launch checklist dict."""
    return {
        "ray_approval_required": [
            "Ray approves lead magnet",
            "Ray approves newsletter draft",
            "Ray approves short video script",
            "CTA selected and approved",
            "Compliance note reviewed and approved",
            "Opt-in destination confirmed",
            "Tracking method selected",
            "Approval queue items cleared",
        ],
        "safe_internal_work": [
            "Improve CTA copy",
            "Revise content drafts",
            "Generate video captions",
            "Create posting schedule",
            "Create approval checklist",
            "Assign scouts to research tasks",
            "Score and review knowledge gaps",
            "Update action queue with current status",
        ],
        "blocked_until_ray_approves": [
            "Publish content",
            "Email subscribers",
            "Post to social media",
            "Activate Stripe/payment",
            "Affiliate signup",
            "Deploy production changes",
            "Use client-facing copy without approval",
        ],
    }


def build_approval_checklist(packet: dict | None = None) -> dict:
    """Build the approval checklist dict."""
    return {
        "checklist": [
            "Review lead magnet for accuracy and compliance",
            "Review newsletter for unsafe promises or guarantees",
            "Review short video script for misleading claims",
            "Review CTA copy for clarity and compliance",
            "Confirm compliance note is present in all public-facing assets",
            "Confirm opt-in mechanism is in place before publishing",
            "Confirm no Stripe/payment activation without explicit command",
            "Confirm no subscriber emails sent without explicit command",
            "Confirm approval queue items are all pending (not auto-approved)",
            "Confirm memory v2 primary mode is active",
        ],
        "approval_boundary": SAFETY_BOUNDARY,
    }


def build_revenue_asset_packet() -> dict:
    """Build the full revenue asset packet from all sources."""
    assets = discover_revenue_assets()
    scored = [score_asset_readiness(a) for a in assets]

    approval_ready  = [a for a in scored if a["readiness_status"] == "approval_ready"]
    needs_revision  = [a for a in scored if a["readiness_status"] == "needs_revision"]
    internal_drafts = [a for a in scored if a["readiness_status"] == "internal_draft"]
    blocked         = [a for a in scored if a["readiness_status"] == "blocked"]

    overall_score = (
        int(sum(a["readiness_score"] for a in scored) / len(scored))
        if scored else 0
    )

    # Build blockers list
    blockers: list[str] = []
    if not any(a["category"] == "lead_magnet" for a in scored):
        blockers.append("No lead magnet found in content directory")
    if not any(a["category"] == "newsletter" for a in scored):
        blockers.append("No newsletter draft found")
    if not any(a["category"] in ("checklist", "lead_magnet") for a in scored):
        blockers.append("No checklist found")

    # Determine best asset paths for evidence
    evidence_paths: list[str] = []
    for a in scored[:5]:
        p = a.get("path", "")
        if p:
            evidence_paths.append(
                str(Path(p).relative_to(_ROOT)) if Path(p).is_relative_to(_ROOT) else p
            )

    packet_id = _stable_packet_id(f"nexus_revenue_packet_{_now_iso()[:10]}")
    cta_opts  = build_cta_options()
    launch_cl = build_launch_checklist()
    approval_cl = build_approval_checklist()

    approval_candidates = generate_approval_candidates({
        "assets": scored, "packet_id": packet_id,
    })

    next_best_step = (
        "Say 'show approval queue' to review and approve assets."
        if approval_ready else
        "Say 'show revenue asset packet' to review assets needing revision."
    )

    return {
        "packet_id":             packet_id,
        "created_at":            _now_iso(),
        "goal":                  REVENUE_GOAL,
        "summary":               (
            f"Nexus revenue asset packet — {len(scored)} asset(s) found, "
            f"{len(approval_ready)} approval-ready, "
            f"{len(needs_revision)} needing revision."
        ),
        "primary_offer":         PRIMARY_OFFER,
        "target_audience":       TARGET_AUDIENCE,
        "assets":                scored,
        "readiness_score":       overall_score,
        "approval_ready_items":  approval_ready,
        "needs_revision_items":  needs_revision,
        "internal_draft_items":  internal_drafts,
        "blocked_items":         blocked,
        "blockers":              blockers,
        "cta_options":           cta_opts,
        "launch_checklist":      launch_cl,
        "approval_checklist":    approval_cl,
        "approval_candidates":   approval_candidates,
        "evidence_paths":        evidence_paths,
        "safety_boundary":       SAFETY_BOUNDARY,
        "next_best_step":        next_best_step,
    }


def generate_approval_candidates(packet: dict) -> list[dict]:
    """Generate local approval queue candidates from packet assets.

    Does NOT approve them. Does NOT publish anything.
    Returns list of approval candidate dicts for injection into approval queue.

    Deduplicates by category — one candidate per category.
    """
    assets = packet.get("assets") or []
    candidates: list[dict] = []
    seen_cats: set[str] = set()

    # Map asset categories to approval candidates
    candidate_specs = [
        {
            "trigger_cats":  {"lead_magnet"},
            "title":         "Approve lead magnet for public use",
            "category":      "client_facing_content",
            "risk_level":    "medium",
            "approval_for":  "Lead magnet must be reviewed and approved before public distribution.",
            "if_approved":   "Lead magnet enters internal review queue for final prep.",
            "if_rejected":   "Lead magnet stays internal-draft; no public use.",
            "safe_next":     "Review lead magnet text, compliance note, and CTA.",
        },
        {
            "trigger_cats":  {"newsletter"},
            "title":         "Approve newsletter for subscriber email",
            "category":      "subscriber_email",
            "risk_level":    "high",
            "approval_for":  "Newsletter must be approved before sending to any subscribers.",
            "if_approved":   "Newsletter enters scheduling queue; send still requires explicit Ray command.",
            "if_rejected":   "Newsletter stays in draft; no email send.",
            "safe_next":     "Review newsletter subject, preview text, and body for compliance.",
        },
        {
            "trigger_cats":  {"short_video_script", "youtube_script"},
            "title":         "Approve short video script for social posting",
            "category":      "content_publish",
            "risk_level":    "medium",
            "approval_for":  "Video script must be approved before recording or posting.",
            "if_approved":   "Script enters production prep; no posting without separate Ray command.",
            "if_rejected":   "Script stays in draft; no recording or posting.",
            "safe_next":     "Review video script for claims, hooks, and CTA compliance.",
        },
        {
            "trigger_cats":  {"cta_copy"},
            "title":         "Approve CTA copy for opt-in / landing page",
            "category":      "client_facing_content",
            "risk_level":    "medium",
            "approval_for":  "CTA copy must be approved before placing on any landing page or opt-in.",
            "if_approved":   "CTA copy available for landing page prep; no publishing without Ray.",
            "if_rejected":   "CTA stays internal; no opt-in placement.",
            "safe_next":     "Review CTA language for clarity and no unsafe promises.",
        },
        {
            "trigger_cats":  {"checklist", "lead_magnet"},
            "title":         "Approve launch checklist for internal execution",
            "category":      "internal_review",
            "risk_level":    "low",
            "approval_for":  "Launch checklist should be reviewed before beginning pre-launch work.",
            "if_approved":   "Hermes proceeds with internal pre-launch checklist items.",
            "if_rejected":   "Launch checklist stays blocked; pre-launch work paused.",
            "safe_next":     "Review launch checklist items and confirm all Ray-approval gates are listed.",
        },
    ]

    for spec in candidate_specs:
        trigger_cats = spec["trigger_cats"]
        matching_assets = [a for a in assets if a.get("category") in trigger_cats]
        if not matching_assets:
            continue

        # Use most recent matching asset
        asset = max(matching_assets, key=lambda a: a.get("modified_at", ""))
        cat_key = spec["category"]
        if cat_key in seen_cats:
            continue
        seen_cats.add(cat_key)

        rel_path = ""
        try:
            p = Path(asset["path"])
            rel_path = str(p.relative_to(_ROOT)) if p.is_relative_to(_ROOT) else str(p)
        except Exception:
            rel_path = asset.get("path", "")

        candidates.append({
            "_source_type":          "revenue_packet",
            "title":                  spec["title"],
            "summary":                (
                f"Asset: {asset['filename']} | "
                f"Readiness: {asset.get('readiness_score', 0)}/100 | "
                f"Status: {asset.get('readiness_status', 'unknown')}"
            )[:200],
            "category":               cat_key,
            "source":                 "revenue_asset_packet",
            "source_path":            rel_path,
            "related_artifact":       rel_path,
            "related_action_id":      f"rap_{packet.get('packet_id', '')}_{cat_key[:8]}",
            "risk_level":             spec["risk_level"],
            "approval_required_for":  spec["approval_for"],
            "if_approved":            spec["if_approved"],
            "if_rejected":            spec["if_rejected"],
            "safe_internal_next_step": spec["safe_next"],
            "evidence_paths":         [rel_path] if rel_path else [],
            "created_at":             _now_iso(),
            "approval_boundary":      SAFETY_BOUNDARY,
        })

    return candidates


def save_revenue_asset_packet(packet: dict) -> dict:
    """Save packet to docs/reports/revenue_packets/ as both JSON and Markdown.

    Returns dict with saved_json, saved_md, latest_updated.
    Respects HERMES_REVENUE_PACKET_WRITE env var — but saves latest pointer always.
    """
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = f"nexus_revenue_asset_packet_{ts}"

    json_path = _PACKET_DIR / f"{base}.json"
    md_path   = _PACKET_DIR / f"{base}.md"

    # Always save
    try:
        # Strip large text_preview from assets for clean storage
        packet_clean = {
            k: v for k, v in packet.items() if k != "assets"
        }
        packet_clean["assets"] = [
            {kk: vv for kk, vv in a.items() if kk != "text_preview"}
            for a in (packet.get("assets") or [])
        ]
        json_path.write_text(json.dumps(packet_clean, indent=2, default=str))
    except Exception as exc:
        logger.warning("save packet json error: %s", exc)

    try:
        md_path.write_text(format_revenue_asset_packet(packet))
    except Exception as exc:
        logger.warning("save packet md error: %s", exc)

    # Update latest pointer
    try:
        _LATEST_FILE.write_text(json.dumps({
            "packet_id":    packet.get("packet_id"),
            "created_at":   packet.get("created_at"),
            "json_path":    str(json_path.relative_to(_ROOT)),
            "md_path":      str(md_path.relative_to(_ROOT)),
            "readiness_score": packet.get("readiness_score", 0),
        }, indent=2))
    except Exception as exc:
        logger.warning("save latest pointer error: %s", exc)

    return {
        "saved_json":      str(json_path),
        "saved_md":        str(md_path),
        "latest_updated":  str(_LATEST_FILE),
    }


def load_latest_revenue_asset_packet() -> dict | None:
    """Load the latest saved packet JSON."""
    if not _LATEST_FILE.exists():
        return None
    try:
        ptr = json.loads(_LATEST_FILE.read_text())
        json_path = _ROOT / ptr.get("json_path", "")
        if json_path.exists():
            return json.loads(json_path.read_text())
    except Exception as exc:
        logger.debug("load_latest_revenue_asset_packet error: %s", exc)
    return None


# ── Formatters ───────────────────────────────────────────────────────────────

def format_revenue_asset_packet(packet: dict) -> str:
    """Full Ray-readable packet markdown/text."""
    score  = packet.get("readiness_score", 0)
    assets = packet.get("assets") or []
    ready  = packet.get("approval_ready_items") or []
    needs_rev = packet.get("needs_revision_items") or []
    blockers  = packet.get("blockers") or []
    candidates = packet.get("approval_candidates") or []

    lines = [
        "NEXUS REVENUE ASSET PACKET",
        "",
        "Goal:",
        f"  {packet.get('goal', REVENUE_GOAL)}",
        "",
        "Primary offer:",
        f"  {packet.get('primary_offer', PRIMARY_OFFER)}",
        "",
        "Target audience:",
        f"  {packet.get('target_audience', TARGET_AUDIENCE)}",
        "",
        f"Overall readiness: {score}/100",
        "",
    ]

    if assets:
        lines += ["Assets included:", ""]
        for i, a in enumerate(assets, 1):
            status = a.get("readiness_status", "unknown")
            cat    = a.get("category", "other").replace("_", " ")
            ascore = a.get("readiness_score", 0)
            lines.append(f"  {i}. {cat} — {status} ({ascore}/100)")
        lines.append("")

    if ready:
        lines += ["Launch-ready assets:", ""]
        for a in ready:
            lines.append(f"  - {a.get('category','').replace('_',' ')}: {a['filename']}")
        lines.append("")

    if needs_rev:
        lines += ["Needs revision:", ""]
        for a in needs_rev:
            flags = ", ".join(a.get("readiness_flags", []))
            lines.append(f"  - {a.get('category','').replace('_',' ')}: {a['filename']}")
            if flags:
                lines.append(f"    ({flags})")
        lines.append("")

    if blockers:
        lines += ["Blockers:", ""]
        for b in blockers:
            lines.append(f"  - {b}")
        lines.append("")

    if candidates:
        lines += [f"Approval candidates ({len(candidates)}):", ""]
        for c in candidates:
            lines.append(f"  - {c['title']} [{c['category'].replace('_',' ')}]")
        lines.append("")

    # Launch checklist summary
    lc = packet.get("launch_checklist") or {}
    approval_steps = lc.get("ray_approval_required") or []
    if approval_steps:
        lines += ["Before publishing (Ray approval required):", ""]
        for step in approval_steps[:5]:
            lines.append(f"  - {step}")
        lines.append("")

    lines += [
        "Approval boundary:",
        "  Hermes will not publish, email subscribers, sell, deploy, spend",
        "  money, or use client-facing content without Ray approval.",
        "",
        f"Next best step:",
        f"  {packet.get('next_best_step', '')}",
        "",
        "Evidence:",
    ]
    for ep in (packet.get("evidence_paths") or [])[:3]:
        lines.append(f"  {ep}")
    if _LATEST_FILE.exists():
        lines.append(f"  {str(_LATEST_FILE.relative_to(_ROOT))}")

    return "\n".join(lines)


def format_launch_ready_assets(packet: dict | None = None) -> str:
    """Format only the launch-ready assets."""
    if packet is None:
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()

    ready = packet.get("approval_ready_items") or []
    score = packet.get("readiness_score", 0)

    lines = ["LAUNCH-READY ASSETS", ""]
    if not ready:
        lines += [
            f"No assets are fully approval-ready yet. (Overall score: {score}/100)",
            "",
            "What to do:",
            "  1. Say 'build revenue asset packet' to refresh the assessment.",
            "  2. Say 'show revenue asset packet' to review all assets.",
            "  3. Say 'generate approval candidates' to queue items for Ray approval.",
        ]
        return "\n".join(lines)

    lines += [f"Assets ready for Ray approval ({len(ready)}):", ""]
    for a in ready:
        cat   = a.get("category", "").replace("_", " ")
        score_a = a.get("readiness_score", 0)
        lines += [
            f"  {cat}: {a['filename']}",
            f"  Readiness score: {score_a}/100",
            "",
        ]
    lines += [
        "Next step:",
        "  Say 'generate approval candidates' to create approval queue items.",
        "  Say 'show approval queue' to review and approve.",
    ]
    return "\n".join(lines)


def format_content_awaiting_approval(packet: dict | None = None) -> str:
    """Format assets that need revision or approval."""
    if packet is None:
        packet = load_latest_revenue_asset_packet() or build_revenue_asset_packet()

    ready     = packet.get("approval_ready_items") or []
    needs_rev = packet.get("needs_revision_items") or []
    candidates = packet.get("approval_candidates") or []

    lines = ["CONTENT AWAITING APPROVAL", ""]

    if ready:
        lines += [f"Ready for Ray approval ({len(ready)}):", ""]
        for a in ready:
            cat = a.get("category", "").replace("_", " ")
            lines.append(f"  - {cat}: {a['filename']}")
        lines.append("")

    if needs_rev:
        lines += [f"Needs revision before approval ({len(needs_rev)}):", ""]
        for a in needs_rev:
            cat   = a.get("category", "").replace("_", " ")
            flags = ", ".join(a.get("readiness_flags", []))
            lines.append(f"  - {cat}: {a['filename']}")
            if flags:
                lines.append(f"    Issues: {flags}")
        lines.append("")

    if candidates:
        lines += [f"Approval queue candidates ({len(candidates)}):", ""]
        for c in candidates:
            lines.append(f"  - {c['title']}")
        lines.append("")
        lines += [
            "Say 'show approval queue' to review and act on these items.",
        ]
    else:
        lines += [
            "No approval candidates in queue yet.",
            "Say 'generate approval candidates' to create them.",
        ]

    lines += [
        "",
        "Approval boundary:",
        "  Nothing is published or sent until Ray explicitly approves.",
    ]
    return "\n".join(lines)


# ── Approval candidate injection ─────────────────────────────────────────────

def inject_approval_candidates(candidates: list[dict]) -> dict:
    """Inject approval candidates into the approval queue (local state only).

    Deduplicates by approval_id — won't add the same candidate twice.
    Returns summary of what was added vs skipped.
    """
    if not candidates:
        return {"added": 0, "skipped": 0, "total": 0}

    try:
        from lib.hermes_approval_queue import (
            normalize_approval_item, _load_state, _save_state, _append_history,
        )
    except ImportError as exc:
        logger.warning("inject_approval_candidates import error: %s", exc)
        return {"added": 0, "skipped": 0, "total": 0, "error": str(exc)}

    state = _load_state()
    existing_ids = {
        item["approval_id"]
        for item in (state.get("items") or [])
        if item.get("approval_id")
    }

    added = 0
    skipped = 0
    new_items = list(state.get("items") or [])
    next_index = max((i.get("index", 0) for i in new_items), default=0) + 1

    for raw in candidates:
        item = normalize_approval_item(raw, index=next_index)
        if item["approval_id"] in existing_ids:
            skipped += 1
            continue
        item["status"] = "pending"
        new_items.append(item)
        existing_ids.add(item["approval_id"])
        next_index += 1
        added += 1
        _append_history({
            "event":       "candidate_added",
            "approval_id": item["approval_id"],
            "title":       item["title"],
            "source":      "revenue_asset_packet",
            "timestamp":   _now_iso(),
        })

    # Re-index
    for i, item in enumerate(new_items, start=1):
        item["index"] = i

    state["items"] = new_items
    _save_state(state)

    return {"added": added, "skipped": skipped, "total": len(candidates)}
