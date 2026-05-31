"""
test_artifact_version_compare.py
Tests for hermes_artifact_version_compare — find, compare, and format.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_artifact_version_compare as avc

PREV_MD = """\
# Checklist
## Who This Is For
Business owners.
## 1. Business Setup
- [ ] Entity formed
- [ ] EIN obtained
## Compliance Note
Educational only.
"""

CURR_MD = """\
# Checklist
## Who This Is For
Business owners who want funding.
## 1. Business Setup
- [ ] Entity formed
- [ ] EIN obtained
- [ ] Business phone number
## 2. Credit Profile
- [ ] Know your score
## Compliance Note
Educational only.
"""


def test_extract_sections():
    sections = avc._extract_sections(CURR_MD)
    assert "Who This Is For" in sections
    assert "1. Business Setup" in sections
    assert "2. Credit Profile" in sections
    assert "Compliance Note" in sections


def test_summarize_changes_added():
    changes = avc.summarize_markdown_changes(PREV_MD, CURR_MD)
    assert "2. Credit Profile" in changes["added"]


def test_summarize_changes_changed():
    changes = avc.summarize_markdown_changes(PREV_MD, CURR_MD)
    assert "1. Business Setup" in changes["changed"] or "Who This Is For" in changes["changed"]


def test_summarize_checklist_item_count():
    changes = avc.summarize_markdown_changes(PREV_MD, CURR_MD)
    assert changes["prev_item_count"] == 2
    assert changes["curr_item_count"] == 4


def test_compliance_unchanged():
    changes = avc.summarize_markdown_changes(PREV_MD, CURR_MD)
    assert changes["compliance_unchanged"]
    assert not changes["compliance_changed"]


def test_compare_text_artifacts_from_files():
    with tempfile.TemporaryDirectory() as tmp:
        prev = Path(tmp) / "prev.md"
        curr = Path(tmp) / "curr.md"
        prev.write_text(PREV_MD)
        curr.write_text(CURR_MD)
        result = avc.compare_text_artifacts(prev, curr)
        assert "error" not in result
        assert "2. Credit Profile" in result["added"]


def test_format_no_prior_version():
    result = avc.format_version_comparison_response(None, Path("/tmp/latest.md"))
    assert "one draft version" in result.lower() or "nothing to compare" in result.lower()


def test_format_response_includes_paths():
    with tempfile.TemporaryDirectory() as tmp:
        prev = Path(tmp) / "prev.md"
        curr = Path(tmp) / "curr.md"
        prev.write_text(PREV_MD)
        curr.write_text(CURR_MD)
        with patch.object(avc, "_ROOT", Path(tmp)):
            result = avc.format_version_comparison_response(prev, curr)
            assert "DRAFT VERSION CHANGES" in result
            assert "Previous" in result
            assert "Latest" in result


def test_format_response_no_evidence_dump():
    with tempfile.TemporaryDirectory() as tmp:
        prev = Path(tmp) / "prev.md"
        curr = Path(tmp) / "curr.md"
        prev.write_text(PREV_MD)
        curr.write_text(CURR_MD)
        with patch.object(avc, "_ROOT", Path(tmp)):
            result = avc.format_version_comparison_response(prev, curr)
            assert "strategic context from evidence" not in result.lower()
            assert "artifact inventory" not in result.lower()


def test_find_prior_artifact_version():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        slug = "credit_funding_readiness_checklist"
        older = content_dir / f"{slug}_draft_20260528_100000.md"
        newer = content_dir / f"{slug}_draft_20260530_120000.md"
        older.write_text("old")
        newer.write_text("new")
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            prior = avc.find_prior_artifact_version(newer)
            assert prior == older


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
