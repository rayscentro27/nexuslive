"""
test_find_latest_checklist_draft.py
Verify find_latest_checklist_draft and find_latest_checklist_draft_pair behave correctly.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_artifact_version_compare as avc

DRAFT_A = "# Credit/Funding Readiness Checklist\n*Draft A*\n"
DRAFT_B = "# Credit/Funding Readiness Checklist\n*Draft B*\n"


def test_find_latest_returns_none_when_no_drafts():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            result = avc.find_latest_checklist_draft()
    assert result is None


def test_find_latest_returns_none_when_dir_missing():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "does" / "not" / "exist"
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            result = avc.find_latest_checklist_draft()
    assert result is None


def test_find_latest_returns_newest_draft():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        older = content_dir / "credit_funding_readiness_checklist_draft_20260531_100000_000.md"
        newer = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        older.write_text(DRAFT_A)
        newer.write_text(DRAFT_B)
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            result = avc.find_latest_checklist_draft()
    assert result == newer


def test_find_pair_returns_previous_and_latest():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        older = content_dir / "credit_funding_readiness_checklist_draft_20260531_100000_000.md"
        newer = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        older.write_text(DRAFT_A)
        newer.write_text(DRAFT_B)
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            previous, latest = avc.find_latest_checklist_draft_pair()
    assert latest == newer
    assert previous == older


def test_find_pair_returns_none_previous_when_only_one_draft():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        only = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        only.write_text(DRAFT_A)
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            previous, latest = avc.find_latest_checklist_draft_pair()
    assert latest == only
    assert previous is None


def test_find_latest_ignores_non_draft_files():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        (content_dir / "credit_funding_readiness_checklist_notes.md").write_text("notes")
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            result = avc.find_latest_checklist_draft()
    assert result is None


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
