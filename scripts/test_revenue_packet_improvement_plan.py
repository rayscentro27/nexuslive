"""
test_revenue_packet_improvement_plan.py
Tests: build_packet_improvement_plan returns required fields;
       recommend_packet_improvements returns non-empty list;
       projected score >= current score.
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


print("=== test_revenue_packet_improvement_plan ===\n")

from lib.hermes_revenue_asset_packet import (
    build_packet_improvement_plan, recommend_packet_improvements,
    SAFETY_BOUNDARY,
)

# ── Empty packet improvement plan ─────────────────────────────────────────────
print("-- improvement plan for empty packet --")
empty_packet = {
    "assets": [], "readiness_score": 0,
    "approval_ready_items": [], "needs_revision_items": [],
}
plan = build_packet_improvement_plan(empty_packet)

check("plan has current_score", "current_score" in plan)
check("plan has target_score", "target_score" in plan)
check("plan has projected_score", "projected_score" in plan)
check("plan has gap_count", "gap_count" in plan)
check("plan has gaps list", "gaps" in plan and isinstance(plan["gaps"], list))
check("plan has improvements list", "improvements" in plan and isinstance(plan["improvements"], list))
check("plan has safe_next_steps", "safe_next_steps" in plan)
check("plan has blocked_until_ray_approves", "blocked_until_ray_approves" in plan)
check("plan has safety_boundary", "safety_boundary" in plan)
check("plan has created_at", "created_at" in plan)

check("target_score == 80", plan["target_score"] == 80)
check("current_score == 0", plan["current_score"] == 0)
check("projected_score >= current_score", plan["projected_score"] >= plan["current_score"])
check("projected_score <= 100", plan["projected_score"] <= 100)
check("gap_count > 0 for empty packet", plan["gap_count"] > 0)
check("improvements non-empty", len(plan["improvements"]) > 0)

# ── Safety boundary present ────────────────────────────────────────────────────
print("\n-- safety boundary in plan --")
check("safety_boundary contains 'publish'", "publish" not in plan["safety_boundary"].lower()
      or "will not publish" in plan["safety_boundary"].lower())
check("SAFETY_BOUNDARY constant used", plan["safety_boundary"] == SAFETY_BOUNDARY)
check("blocked_until_ray_approves non-empty", len(plan["blocked_until_ray_approves"]) > 0)
check("safe_next_steps non-empty", len(plan["safe_next_steps"]) > 0)

# ── recommend_packet_improvements ─────────────────────────────────────────────
print("\n-- recommend_packet_improvements --")
improvements = recommend_packet_improvements(empty_packet)
check("improvements is a list", isinstance(improvements, list))
check("improvements non-empty", len(improvements) > 0)
check("improvements are strings", all(isinstance(i, str) for i in improvements))

# ── Packet with score >= 80: projected stays bounded ──────────────────────────
print("\n-- high-score packet: projected <= 100 --")
good_packet = {
    "assets": [
        {
            "filename": "lead_magnet.md", "path": "/nonexistent/lm.md",
            "category": "lead_magnet", "readiness_score": 90,
            "readiness_status": "approval_ready", "readiness_flags": [],
        },
    ],
    "readiness_score": 85,
    "approval_ready_items": [{"filename": "lead_magnet.md"}],
}
good_plan = build_packet_improvement_plan(good_packet)
check("projected_score <= 100", good_plan["projected_score"] <= 100)
check("current_score == 85", good_plan["current_score"] == 85)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
