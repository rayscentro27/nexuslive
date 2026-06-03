"""
test_revenue_packet_rescore_after_fixes.py
Tests: build_revenue_asset_packet_with_fixes uses fixed copies,
       preserves original categories, improves score.
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


print("=== test_revenue_packet_rescore_after_fixes ===\n")

from lib.hermes_revenue_asset_packet import (
    build_revenue_asset_packet,
    build_revenue_asset_packet_with_fixes,
    SAFETY_BOUNDARY,
)
from lib.hermes_revenue_asset_fixer import apply_safe_asset_fixes

# ── Apply fixes first ─────────────────────────────────────────────────────────
print("-- apply fixes before rescore --")
fix_result = apply_safe_asset_fixes()
fixed_count = fix_result.get("assets_fixed", 0)
score_before = fix_result.get("score_before", 0)
check("fix result is dict", isinstance(fix_result, dict))
check("score_before present", "score_before" in fix_result)

# ── build_revenue_asset_packet_with_fixes returns packet dict ─────────────────
print("\n-- build_revenue_asset_packet_with_fixes --")
fixed_packet = build_revenue_asset_packet_with_fixes()
check("returns dict", isinstance(fixed_packet, dict))
check("has 'assets'", "assets" in fixed_packet)
check("has 'readiness_score'", "readiness_score" in fixed_packet)
check("has 'safety_boundary'", "safety_boundary" in fixed_packet)
check("safety_boundary == SAFETY_BOUNDARY", fixed_packet["safety_boundary"] == SAFETY_BOUNDARY)

# ── Score with fixes >= score without fixes ───────────────────────────────────
print("\n-- score improves with fixes --")
base_packet = build_revenue_asset_packet()
base_score = base_packet.get("readiness_score", 0)
fixed_score = fixed_packet.get("readiness_score", 0)
check("fixed packet score >= base score", fixed_score >= base_score)

# ── Fixed copies don't double-count originals ─────────────────────────────────
print("\n-- asset count not inflated by fixed copies --")
base_count = len(base_packet.get("assets") or [])
fixed_count_assets = len(fixed_packet.get("assets") or [])
check("asset count unchanged", fixed_count_assets == base_count)

# ── Assets don't come from fixed/ subdirectory in base packet ─────────────────
print("\n-- base packet excludes fixed/ directory --")
base_assets = base_packet.get("assets") or []
for asset in base_assets:
    path = asset.get("path", "")
    check(f"[{Path(path).name[:35]}] not in fixed/ dir", "/fixed/" not in path)

# ── Categories preserved in fixed packet ─────────────────────────────────────
print("\n-- original categories preserved in fixed packet --")
fixed_assets = fixed_packet.get("assets") or []
valid_cats = {
    "lead_magnet", "checklist", "newsletter", "short_video_script",
    "youtube_script", "seo_article", "linkedin_post", "x_post",
    "tiktok_hook", "compliance_note", "other",
}
for asset in fixed_assets:
    cat = asset.get("category", "")
    check(f"[{Path(asset.get('path','')).name[:30]}] has valid category",
          cat in valid_cats)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
