"""
test_version_compare_detects_duplicates.py
The comparison engine flags duplicate sections and subtitles in the latest draft.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_artifact_version_compare import (
    summarize_markdown_changes,
    format_version_comparison_response,
    _count_duplicate_headings,
)

CLEAN = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*

## Start Here

Step 1.

## Who This Checklist Is For

Business owners.

## Compliance Note

*Educational purposes only.*
"""

DUPLICATE_SECTIONS = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*
*(Simplified — Plain English Edition)*

## Start Here

Step 1.

## Who This Checklist Is For

Business owners.

## Start Here

Step 1.

## Compliance Note

*Educational purposes only.*
"""


def test_count_duplicate_headings_finds_dupes():
    dupes = _count_duplicate_headings(DUPLICATE_SECTIONS)
    assert "## Start Here" in dupes


def test_count_duplicate_headings_clean_doc():
    dupes = _count_duplicate_headings(CLEAN)
    assert dupes == []


def test_summarize_detects_dup_subtitle_in_current():
    changes = summarize_markdown_changes(CLEAN, DUPLICATE_SECTIONS)
    assert changes["curr_dup_subtitle"] is True
    assert changes["prev_dup_subtitle"] is False


def test_summarize_detects_dup_headings_in_current():
    changes = summarize_markdown_changes(CLEAN, DUPLICATE_SECTIONS)
    assert len(changes["curr_dup_headings"]) > 0


def test_comparison_response_warns_about_duplicates():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "clean.md"
        curr_path = Path(tmp) / "dup.md"
        prev_path.write_text(CLEAN)
        curr_path.write_text(DUPLICATE_SECTIONS)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "Warning" in resp or "duplicate" in resp.lower()


def test_comparison_response_suggests_clean_it_up():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "clean.md"
        curr_path = Path(tmp) / "dup.md"
        prev_path.write_text(CLEAN)
        curr_path.write_text(DUPLICATE_SECTIONS)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "clean it up" in resp.lower()


def test_comparison_clean_to_dup_shows_warning():
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "clean.md"
        curr_path = Path(tmp) / "dup.md"
        prev_path.write_text(CLEAN)
        curr_path.write_text(DUPLICATE_SECTIONS)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "DRAFT VERSION CHANGES" in resp
    assert "strategic context from evidence" not in resp.lower()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(failed)
