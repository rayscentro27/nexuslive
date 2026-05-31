"""
test_revision_followup_make_it_simpler.py
'make it simpler' routes to revision engine and creates a simplified artifact.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine
import lib.hermes_content_artifact_builder as cab
import lib.hermes_conversation_context_resolver as ccr


def _make_first_draft(tmp: str) -> Path:
    content_dir = Path(tmp) / "docs" / "reports" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    with patch.object(cab, "_CONTENT_DIR", content_dir):
        with patch.object(cab, "_ROOT", Path(tmp)):
            cab.create_credit_funding_readiness_checklist_draft(new_version=False)
    drafts = sorted(content_dir.glob("*_draft_*.md"), reverse=True)
    return drafts[0]


def test_resolve_revision_instruction():
    assert engine.resolve_revision_instruction("make it simpler") == "simplified"
    assert engine.resolve_revision_instruction("make it more professional") == "professional"
    assert engine.resolve_revision_instruction("turn it into a lead magnet") == "lead_magnet"
    assert engine.resolve_revision_instruction("create a short video script from this") == "short_video_script"
    assert engine.resolve_revision_instruction("what changed") is None


def test_make_it_simpler_creates_new_artifact():
    with tempfile.TemporaryDirectory() as tmp:
        prev = _make_first_draft(tmp)
        content_dir = prev.parent
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, "simplified")
                assert result["created"] is True
                assert result["revision_type"] == "simplified"
                new_path = Path(tmp) / result["path"]
                assert new_path.exists()
                assert "simplified" in result["path"]


def test_simplified_draft_differs_from_original():
    with tempfile.TemporaryDirectory() as tmp:
        prev = _make_first_draft(tmp)
        content_dir = prev.parent
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, "simplified")
                new_path = Path(tmp) / result["path"]
                original_text = prev.read_text()
                simplified_text = new_path.read_text()
                assert simplified_text != original_text, "Simplified draft must differ from original"
                assert "Start Here" in simplified_text, "Simplified draft must have Start Here section"
                assert "Simplified" in simplified_text, "Simplified draft must note it is simplified"


def test_revision_response_has_correct_wording():
    with tempfile.TemporaryDirectory() as tmp:
        prev = _make_first_draft(tmp)
        content_dir = prev.parent
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, "simplified")
                response = engine.format_revision_created_response(result)
                assert "CONTENT DRAFT VERSION CREATED" in response
                assert "simplified" in response.lower()
                assert "Internal draft only" in response
                assert "what changed" in response.lower()
                assert "first internal draft" not in response


def test_revision_response_has_both_paths():
    with tempfile.TemporaryDirectory() as tmp:
        prev = _make_first_draft(tmp)
        content_dir = prev.parent
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, "simplified")
                response = engine.format_revision_created_response(result)
                assert "New draft:" in response
                assert "Previous draft:" in response


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
