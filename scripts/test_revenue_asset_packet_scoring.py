"""
test_revenue_asset_packet_scoring.py
Tests: readiness scoring logic for each criterion.
"""
import sys, os, tempfile
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


print("=== test_revenue_asset_packet_scoring ===\n")

from lib.hermes_revenue_asset_packet import score_asset_readiness, READINESS_STATUSES


def _write_tmp(content: str) -> Path:
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    tf.write(content)
    tf.flush()
    return Path(tf.name)


# ── missing file → blocked ─────────────────────────────────────────────────────
print("-- missing file → blocked --")
asset_missing = {
    "filename": "missing_asset.md",
    "path": "/nonexistent/path/missing.md",
    "category": "lead_magnet",
    "modified_at": "2026-06-02T10:00:00+00:00",
}
scored = score_asset_readiness(asset_missing)
check("status == blocked", scored["readiness_status"] == "blocked")
check("score < 25 (no file_exists bonus)", scored["readiness_score"] < 25)
check("file_not_found in flags", "file_not_found" in scored["readiness_flags"])

# ── full compliance asset → approval_ready ────────────────────────────────────
print("\n-- full compliance asset → approval_ready --")
good_content = """
# Credit/Funding Readiness Checklist
*Internal Draft — Lead Magnet Format — Not for publication*

> **INTERNAL ONLY.** Do not share until approved by Ray.

## Are You Ready for Business Funding?

This checklist helps you prepare for funding applications.

Revenue goal: Generate $1,000/week through the Nexus membership.

Download the free checklist and start your funding readiness check.
"""
good_path = _write_tmp(good_content)
asset_good = {
    "filename": good_path.name, "path": str(good_path),
    "category": "lead_magnet",
    "modified_at": "2026-06-02T10:00:00+00:00",
}
scored_good = score_asset_readiness(asset_good)
check("score >= 75", scored_good["readiness_score"] >= 75)
check("status == approval_ready", scored_good["readiness_status"] == "approval_ready")
check("no unsafe_promise flag", "unsafe_promise_detected" not in scored_good["readiness_flags"])
good_path.unlink(missing_ok=True)

# ── unsafe promise → needs_revision ──────────────────────────────────────────
print("\n-- unsafe promise → needs_revision --")
unsafe_content = """
# Credit Funding Guide
**INTERNAL ONLY.** Not for publication.

Download the free checklist. Revenue goal aligned with Nexus membership.

We guarantee 100% success and promise results!
"""
unsafe_path = _write_tmp(unsafe_content)
asset_unsafe = {
    "filename": unsafe_path.name, "path": str(unsafe_path),
    "category": "checklist",
    "modified_at": "2026-06-02T10:00:00+00:00",
}
scored_unsafe = score_asset_readiness(asset_unsafe)
check("status == needs_revision", scored_unsafe["readiness_status"] == "needs_revision")
check("unsafe_promise_detected in flags", "unsafe_promise_detected" in scored_unsafe["readiness_flags"])
unsafe_path.unlink(missing_ok=True)

# ── no internal marker → lower score ─────────────────────────────────────────
print("\n-- no internal marker → internal_draft or needs_revision --")
no_marker = """
# Business Funding Checklist
Here are the steps to get funding-ready. Download the free checklist and join Nexus.
"""
no_marker_path = _write_tmp(no_marker)
asset_no_marker = {
    "filename": no_marker_path.name, "path": str(no_marker_path),
    "category": "checklist",
    "modified_at": "2026-06-02T10:00:00+00:00",
}
scored_no_marker = score_asset_readiness(asset_no_marker)
check("no_internal_marker in flags", "no_internal_marker" in scored_no_marker["readiness_flags"])
check("status is not approval_ready", scored_no_marker["readiness_status"] != "approval_ready")
no_marker_path.unlink(missing_ok=True)

# ── READINESS_STATUSES constants ──────────────────────────────────────────────
print("\n-- READINESS_STATUSES constants --")
check("approval_ready in statuses", "approval_ready" in READINESS_STATUSES)
check("needs_revision in statuses", "needs_revision" in READINESS_STATUSES)
check("internal_draft in statuses", "internal_draft" in READINESS_STATUSES)
check("blocked in statuses", "blocked" in READINESS_STATUSES)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
