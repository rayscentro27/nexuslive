"""
test_content_draft_new_version_language.py
New-version creation uses VERSION wording; first-draft uses CREATED wording.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_artifact_builder as cab


def _make_content_dir(tmp: str) -> Path:
    d = Path(tmp) / "docs" / "reports" / "content"
    d.mkdir(parents=True)
    return d


def test_first_draft_uses_created_wording():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = _make_content_dir(tmp)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                response = cab.format_content_created_response(result)
                assert "CONTENT DRAFT CREATED" in response
                assert "first internal draft" in response
                assert "VERSION" not in response


def test_new_version_uses_version_wording():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = _make_content_dir(tmp)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                # Create first draft so there's a "previous" to compare
                cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                import time; time.sleep(0.01)
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=True)
                response = cab.format_content_created_response(result)
                assert "CONTENT DRAFT VERSION CREATED" in response
                assert "new internal version" in response
                assert "first internal draft" not in response


def test_new_version_includes_previous_path():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = _make_content_dir(tmp)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                import time; time.sleep(0.01)
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=True)
                assert result.get("is_new_version") is True
                assert result.get("previous_path"), "Expected previous_path in result"
                response = cab.format_content_created_response(result)
                assert "Previous draft" in response


def test_new_version_includes_what_changed_prompt():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = _make_content_dir(tmp)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                import time; time.sleep(0.01)
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=True)
                response = cab.format_content_created_response(result)
                assert "what changed" in response.lower()


def test_first_draft_no_previous_path():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = _make_content_dir(tmp)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                assert not result.get("is_new_version")
                assert result.get("previous_path", "") == ""


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
