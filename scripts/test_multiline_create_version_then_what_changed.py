"""
test_multiline_create_version_then_what_changed.py
Simulates: "create a new version\nwhat changed?" as a single Telegram message.
Context from line 1 must be available to line 2.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_artifact_builder as cab
import lib.hermes_artifact_version_compare as avc
import lib.hermes_conversation_context_resolver as ccr


def test_new_version_response_includes_both_paths():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                # First draft
                cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                time.sleep(0.01)
                # New version
                result = cab.create_credit_funding_readiness_checklist_draft(new_version=True)
                response = cab.format_content_created_response(result)
                assert "New draft:" in response
                assert "Previous draft:" in response
                assert "what changed" in response.lower()


def test_context_after_new_version_has_previous_path():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        with patch.object(cab, "_CONTENT_DIR", content_dir):
            with patch.object(cab, "_ROOT", Path(tmp)):
                with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
                    with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                        cab.create_credit_funding_readiness_checklist_draft(new_version=False)
                        time.sleep(0.01)
                        result = cab.create_credit_funding_readiness_checklist_draft(new_version=True)
                        response = cab.format_content_created_response(result)
                        # Simulate _dispatch_continuity recording context
                        ctx = ccr.extract_context_from_response("create a new version", response)
                        assert ctx is not None
                        ccr.record_context_event(ctx)
                        # Now "what changed?" should resolve
                        ref = ccr.resolve_reference("what changed")
                        assert ref is not None
                        assert ref["action"] == "compare"
                        assert ref["context"].get("previous_object_path"), "Previous path must be in context"


def test_comparison_finds_two_drafts():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        slug = "credit_funding_readiness_checklist"
        older = content_dir / f"{slug}_draft_20260528_100000.md"
        newer = content_dir / f"{slug}_draft_20260531_120000.md"
        older.write_text("# Old\n## Section A\n- [ ] item1\n")
        newer.write_text("# New\n## Section A\n- [ ] item1\n- [ ] item2\n## Section B\n- [ ] item3\n")
        with patch.object(avc, "_CONTENT_DIR", content_dir):
            with patch.object(avc, "_ROOT", Path(tmp)):
                latest, previous = avc.find_two_latest_drafts()
                assert latest == newer
                assert previous == older
                result = avc.format_version_comparison_response(previous, latest)
                assert "DRAFT VERSION CHANGES" in result
                assert "Section B" in result or "Added" in result


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
