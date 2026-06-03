"""
test_revenue_packet_rescore.py
Tests: rescore_packet_after_improvements rescores all assets;
       apply_internal_packet_improvements updates packet;
       improved packet score is bounded 0–100.
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


print("=== test_revenue_packet_rescore ===\n")

from lib.hermes_revenue_asset_packet import (
    rescore_packet_after_improvements, apply_internal_packet_improvements,
)


def _write_tmp(content: str) -> Path:
    tf = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False)
    tf.write(content)
    tf.flush()
    return Path(tf.name)


# ── rescore empty packet ────────────────────────────────────────────────────
print("-- rescore empty packet --")
empty_packet = {
    "assets": [], "readiness_score": 50,
    "approval_ready_items": [], "needs_revision_items": [],
}
rescored = rescore_packet_after_improvements(empty_packet)
check("rescored has readiness_score", "readiness_score" in rescored)
check("rescored has rescored_at", "rescored_at" in rescored)
check("rescored score == 0 for empty assets", rescored["readiness_score"] == 0)

# ── rescore with real assets ────────────────────────────────────────────────
print("\n-- rescore with real asset file --")
good_content = """
# Credit Funding Readiness Guide
*Internal Draft — Not for publication*
> INTERNAL ONLY. Do not share until approved by Ray.

Download the free checklist for your funding readiness check.
Revenue goal: $1,000/week through Nexus membership.
"""
tmp = _write_tmp(good_content)
packet_with_asset = {
    "assets": [
        {
            "filename": tmp.name,
            "path": str(tmp),
            "category": "lead_magnet",
            "readiness_score": 0,
            "readiness_status": "blocked",
            "readiness_flags": [],
        }
    ],
    "readiness_score": 0,
    "approval_ready_items": [],
}
rescored2 = rescore_packet_after_improvements(packet_with_asset)
check("rescored2 score > 0 for existing file", rescored2["readiness_score"] > 0)
check("rescored2 has assets", len(rescored2.get("assets") or []) == 1)
check("rescored2 score <= 100", rescored2["readiness_score"] <= 100)
check("rescored2 has approval_ready_items key", "approval_ready_items" in rescored2)
tmp.unlink(missing_ok=True)

# ── apply_internal_packet_improvements ────────────────────────────────────
print("\n-- apply_internal_packet_improvements --")
packet_for_improvement = {
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
improved = apply_internal_packet_improvements(packet_for_improvement)
check("improved packet has assets", "assets" in improved)
check("improved packet has improved_at", "improved_at" in improved)
check("improved packet has improvement_applied=True", improved.get("improvement_applied") is True)
check("improved packet readiness_score is int", isinstance(improved.get("readiness_score"), int))
check("improved assets have improvement_note field",
      all("improvement_note" in a for a in (improved.get("assets") or [])))

# ── Score is always bounded ───────────────────────────────────────────────
print("\n-- score always bounded 0-100 --")
for score_val in [0, 50, 100, -5, 120]:
    bounded_packet = {"assets": [], "readiness_score": score_val, "approval_ready_items": []}
    r = rescore_packet_after_improvements(bounded_packet)
    check(f"empty assets rescore always 0 (input={score_val})", r["readiness_score"] == 0)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
