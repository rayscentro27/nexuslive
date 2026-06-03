"""
test_revenue_asset_fixer_no_overwrite.py
Tests: write_fixed_asset_copy never overwrites originals;
       fixed copies go to the fixed/ subdirectory;
       original file mtime is unchanged after fix.
"""
import sys, os, tempfile, time
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


print("=== test_revenue_asset_fixer_no_overwrite ===\n")

from lib.hermes_revenue_asset_fixer import write_fixed_asset_copy, _FIXED_DIR

SAMPLE = "# Test Asset\n\nSample content.\n"

# ── Write fixed copy into a temp dir simulating a real asset ─────────────────
print("-- write_fixed_asset_copy creates file in fixed/ --")
with tempfile.NamedTemporaryFile(suffix=".md", delete=False, dir=ROOT / "docs" / "reports" / "content",
                                  mode="w") as f:
    f.write(SAMPLE)
    orig_path = Path(f.name)

try:
    orig_mtime = orig_path.stat().st_mtime

    fixed_path = write_fixed_asset_copy(orig_path, SAMPLE + "\n\nFixed content.")
    check("fixed copy created", fixed_path.exists())
    check("fixed path is in _FIXED_DIR", str(fixed_path).startswith(str(_FIXED_DIR)))
    check("fixed filename contains '_safe_fixed_'", "_safe_fixed_" in fixed_path.name)
    check("fixed path != original path", fixed_path != orig_path)

    # Original untouched
    new_mtime = orig_path.stat().st_mtime
    check("original mtime unchanged", orig_mtime == new_mtime)
    check("original content unchanged", orig_path.read_text() == SAMPLE)

    # Fixed copy has new content
    fixed_content = fixed_path.read_text()
    check("fixed copy has new content", "Fixed content." in fixed_content)

    # Clean up fixed copy
    fixed_path.unlink(missing_ok=True)

finally:
    orig_path.unlink(missing_ok=True)

# ── apply_safe_asset_fixes does not modify original files ────────────────────
print("\n-- apply_safe_asset_fixes: originals not modified --")
from lib.hermes_revenue_asset_fixer import apply_safe_asset_fixes
from lib.hermes_revenue_asset_packet import build_revenue_asset_packet

packet = build_revenue_asset_packet()
assets = packet.get("assets") or []

# Record original mtimes
orig_mtimes = {}
for asset in assets:
    p = Path(asset.get("path", ""))
    if p.exists():
        orig_mtimes[str(p)] = p.stat().st_mtime

# Apply fixes
apply_safe_asset_fixes()

# Check originals are unchanged
for path_str, orig_mt in orig_mtimes.items():
    p = Path(path_str)
    if p.exists():
        check(f"[{p.name[:40]}] original not modified", p.stat().st_mtime == orig_mt)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
