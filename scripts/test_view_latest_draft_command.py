"""
test_view_latest_draft_command.py
find_latest_content_draft returns the newest draft by filename sort.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_artifact_viewer as av


def test_find_latest_draft_returns_newest():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        older = content_dir / "credit_funding_readiness_checklist_draft_20260528_100000.md"
        newer = content_dir / "credit_funding_readiness_checklist_draft_20260530_120000.md"
        older.write_text("old")
        newer.write_text("new")
        with patch.object(av, "_CONTENT_DIR", content_dir):
            result = av.find_latest_content_draft()
            assert result == newer


def test_find_latest_draft_empty_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        with patch.object(av, "_CONTENT_DIR", content_dir):
            assert av.find_latest_content_draft() is None


def test_find_latest_draft_missing_dir_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        missing_dir = Path(tmp) / "does_not_exist"
        with patch.object(av, "_CONTENT_DIR", missing_dir):
            assert av.find_latest_content_draft() is None


def test_read_artifact_preview():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "draft.md"
        p.write_text("# Hello\nContent here.")
        result = av.read_artifact_preview(p)
        assert "Hello" in result


def test_read_artifact_preview_missing():
    p = Path("/tmp/does_not_exist_xyz.md")
    result = av.read_artifact_preview(p)
    assert "Could not read" in result


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
