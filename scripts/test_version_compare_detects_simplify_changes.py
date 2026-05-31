"""
test_version_compare_detects_simplify_changes.py
The comparison engine detects meaningful changes introduced by simplify.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine
from lib.hermes_artifact_version_compare import (
    summarize_markdown_changes,
    format_version_comparison_response,
)

ORIGINAL = """\
# Credit/Funding Readiness Checklist
*Internal Draft — 20260531_120000_000 UTC — Not for publication*

## Who This Checklist Is For

Business owners who want to apply for business funding.

## 1. Business Setup Readiness

- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp registered with your state
- [ ] **EIN obtained** — Employer Identification Number from the IRS (free at irs.gov)
- [ ] **NAICS code** — industry classification code; know yours before applying

## Compliance Note

*This checklist is for educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review and approval before any use.*
"""


def test_simplify_adds_start_here_detected():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    changes = summarize_markdown_changes(ORIGINAL, simplified)
    assert changes["curr_start_here"] is True
    assert changes["prev_start_here"] is False


def test_simplify_adds_simplified_marker_detected():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    changes = summarize_markdown_changes(ORIGINAL, simplified)
    assert changes["curr_simplified"] is True
    assert changes["prev_simplified"] is False


def test_word_count_captured():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    changes = summarize_markdown_changes(ORIGINAL, simplified)
    assert "prev_word_count" in changes
    assert "curr_word_count" in changes
    assert changes["prev_word_count"] > 0
    assert changes["curr_word_count"] > 0


def test_no_duplicate_sections_in_first_simplify():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    changes = summarize_markdown_changes(ORIGINAL, simplified)
    assert changes["curr_dup_headings"] == []
    assert changes["curr_dup_subtitle"] is False


def test_comparison_response_mentions_simplified_marker():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "original.md"
        curr_path = Path(tmp) / "simplified.md"
        prev_path.write_text(ORIGINAL)
        curr_path.write_text(simplified)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "Simplified edition marker" in resp


def test_comparison_response_mentions_start_here():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "original.md"
        curr_path = Path(tmp) / "simplified.md"
        prev_path.write_text(ORIGINAL)
        curr_path.write_text(simplified)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "Start Here" in resp


def test_comparison_response_mentions_word_count():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "original.md"
        curr_path = Path(tmp) / "simplified.md"
        prev_path.write_text(ORIGINAL)
        curr_path.write_text(simplified)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "Word count" in resp or "word count" in resp.lower()


def test_comparison_response_has_draft_version_changes_header():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "original.md"
        curr_path = Path(tmp) / "simplified.md"
        prev_path.write_text(ORIGINAL)
        curr_path.write_text(simplified)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "DRAFT VERSION CHANGES" in resp
    assert "strategic context from evidence" not in resp.lower()


def test_comparison_response_no_evidence_dump():
    simplified = engine.simplify_checklist_draft(ORIGINAL, "20260531_130000_000")
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        prev_path = Path(tmp) / "original.md"
        curr_path = Path(tmp) / "simplified.md"
        prev_path.write_text(ORIGINAL)
        curr_path.write_text(simplified)
        resp = format_version_comparison_response(prev_path, curr_path)
    assert "OFFLINE" not in resp
    assert "Beehiiv" not in resp
    assert "artifact_inventory" not in resp.lower()


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
