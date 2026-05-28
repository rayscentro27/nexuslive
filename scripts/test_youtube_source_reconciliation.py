"""
test_youtube_source_reconciliation.py
========================================
Verify the YouTube source reconciliation script discovers URLs correctly.
"""
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_youtube_source_reconciliation ===\n")

import lib.youtube_source_registry as _regmod
from scripts.run_youtube_source_reconciliation import (
    scan_for_youtube_urls,
    YOUTUBE_URL_RE,
)

# 1. Regex tests
check("watch URL detected",    bool(YOUTUBE_URL_RE.search("https://www.youtube.com/watch?v=abc123")))
check("channel URL detected",  bool(YOUTUBE_URL_RE.search("https://www.youtube.com/channel/UCxyz")))
check("handle URL detected",   bool(YOUTUBE_URL_RE.search("https://www.youtube.com/@CreditSweep")))
check("short URL detected",    bool(YOUTUBE_URL_RE.search("https://youtu.be/abc123")))
check("non-YT URL ignored",    not YOUTUBE_URL_RE.search("https://www.google.com/search?q=test"))

# 2. scan_for_youtube_urls scans in our reports dir
# Create fake MD files with YouTube URLs in a temp reports dir
orig_reports_dir = None
with tempfile.TemporaryDirectory() as tmpdir:
    import scripts.run_youtube_source_reconciliation as _script
    orig_reports_dir = _script.REPORTS_DIR

    reports_dir = Path(tmpdir)
    _script.REPORTS_DIR = reports_dir

    ceo_dir = reports_dir / "ceo_review"
    ceo_dir.mkdir()
    (ceo_dir / "NEXUS_CEO_PACKET_test.md").write_text(
        "See https://www.youtube.com/@CreditSweep for research\n"
        "Also https://youtu.be/dQw4w9WgXcQ was useful\n"
        "And https://www.youtube.com/channel/UCabc123 is a great channel"
    )
    (reports_dir / "test_report.md").write_text(
        "Duplicate: https://www.youtube.com/@CreditSweep\n"
        "New: https://www.youtube.com/watch?v=newvideo123"
    )

    discovered = scan_for_youtube_urls()
    urls_found = [d["url"] for d in discovered]

    check("@handle URL discovered",   any("@CreditSweep" in u for u in urls_found))
    check("youtu.be URL discovered",  any("youtu.be" in u for u in urls_found))
    check("channel URL discovered",   any("UCabc123" in u for u in urls_found))
    check("watch URL discovered",     any("newvideo123" in u for u in urls_found))
    check("no duplicates in scan",    len(set(u for u in urls_found)) == len(urls_found))

    _script.REPORTS_DIR = orig_reports_dir

# 3. _detect_source_type
from scripts.run_youtube_source_reconciliation import _detect_source_type
check("watch → video",   _detect_source_type("https://youtube.com/watch?v=abc") == "video")
check("youtu.be → video", _detect_source_type("https://youtu.be/abc") == "video")
check("@handle → channel", _detect_source_type("https://youtube.com/@SomeChannel") == "channel")
check("channel/ → channel", _detect_source_type("https://youtube.com/channel/UCabc") == "channel")

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
