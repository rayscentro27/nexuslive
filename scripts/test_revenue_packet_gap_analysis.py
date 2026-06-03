"""
test_revenue_packet_gap_analysis.py
Tests: analyze_packet_readiness_gaps returns correct gap categories;
       each gap has required fields; projected score makes sense.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_revenue_packet_gap_analysis ===\n")

from lib.hermes_revenue_asset_packet import (
    analyze_packet_readiness_gaps, GAP_CATEGORIES,
)

# ── GAP_CATEGORIES completeness ───────────────────────────────────────────────
print("-- GAP_CATEGORIES constants --")
EXPECTED = {
    "missing_lead_magnet", "missing_internal_marker", "missing_cta",
    "not_revenue_connected", "unsafe_promise_detected", "low_overall_score",
    "missing_newsletter", "missing_video_script", "missing_compliance_note",
    "no_approval_ready_assets",
}
for cat in EXPECTED:
    check(f"'{cat}' in GAP_CATEGORIES", cat in GAP_CATEGORIES)

# ── Empty packet → produces expected gaps ─────────────────────────────────────
print("\n-- empty packet produces gaps --")
empty_packet = {
    "assets": [], "readiness_score": 0,
    "approval_ready_items": [], "needs_revision_items": [],
}
gaps = analyze_packet_readiness_gaps(empty_packet)
check("gaps list is non-empty for empty packet", len(gaps) > 0)

gap_names = {g["gap"] for g in gaps}
check("missing_lead_magnet detected in empty packet", "missing_lead_magnet" in gap_names)
check("missing_newsletter detected in empty packet", "missing_newsletter" in gap_names)
check("low_overall_score detected in empty packet", "low_overall_score" in gap_names)
check("no_approval_ready_assets detected in empty packet", "no_approval_ready_assets" in gap_names)

# ── Each gap has required fields ───────────────────────────────────────────────
print("\n-- each gap has required fields --")
for gap in gaps:
    check(f"[{gap['gap'][:30]}] has 'gap' field", "gap" in gap)
    check(f"[{gap['gap'][:30]}] has 'detail' field", "detail" in gap)
    check(f"[{gap['gap'][:30]}] has 'score_impact' field", "score_impact" in gap)
    check(f"[{gap['gap'][:30]}] has 'remediation' field", "remediation" in gap)
    check(f"[{gap['gap'][:30]}] score_impact > 0", gap.get("score_impact", 0) > 0)

# ── Asset with no_internal_marker flag → missing_internal_marker gap ──────────
print("\n-- asset flags drive gap detection --")
packet_with_flagged_asset = {
    "assets": [
        {
            "filename": "test_asset.md",
            "path": "/nonexistent/test.md",
            "category": "lead_magnet",
            "readiness_score": 40,
            "readiness_status": "needs_revision",
            "readiness_flags": ["no_internal_marker", "no_cta_detected"],
        }
    ],
    "readiness_score": 40,
    "approval_ready_items": [],
    "needs_revision_items": [],
}
flagged_gaps = analyze_packet_readiness_gaps(packet_with_flagged_asset)
flagged_names = {g["gap"] for g in flagged_gaps}
check("missing_internal_marker gap from flagged asset", "missing_internal_marker" in flagged_names)
check("missing_cta gap from flagged asset", "missing_cta" in flagged_names)

# ── Perfect packet → no low_overall_score gap ────────────────────────────────
print("\n-- perfect packet: no low_overall_score --")
perfect_packet = {
    "assets": [
        {
            "filename": "lead_magnet.md", "path": "/nonexistent/lm.md",
            "category": "lead_magnet", "readiness_score": 95,
            "readiness_status": "approval_ready", "readiness_flags": [],
        },
        {
            "filename": "newsletter.md", "path": "/nonexistent/nl.md",
            "category": "newsletter", "readiness_score": 90,
            "readiness_status": "approval_ready", "readiness_flags": [],
        },
        {
            "filename": "video.md", "path": "/nonexistent/vid.md",
            "category": "short_video_script", "readiness_score": 85,
            "readiness_status": "approval_ready", "readiness_flags": [],
        },
        {
            "filename": "compliance.md", "path": "/nonexistent/comp.md",
            "category": "compliance_note", "readiness_score": 80,
            "readiness_status": "approval_ready", "readiness_flags": [],
        },
    ],
    "readiness_score": 88,
    "approval_ready_items": [{"filename": "lead_magnet.md"}],
}
perfect_gaps = analyze_packet_readiness_gaps(perfect_packet)
perfect_names = {g["gap"] for g in perfect_gaps}
check("no low_overall_score in perfect packet", "low_overall_score" not in perfect_names)
check("no missing_lead_magnet in perfect packet", "missing_lead_magnet" not in perfect_names)
check("no missing_newsletter in perfect packet", "missing_newsletter" not in perfect_names)
check("no missing_video_script in perfect packet", "missing_video_script" not in perfect_names)
check("no no_approval_ready_assets in perfect packet", "no_approval_ready_assets" not in perfect_names)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
