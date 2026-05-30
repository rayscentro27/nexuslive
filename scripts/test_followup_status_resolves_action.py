"""
test_followup_status_resolves_action.py
Sequence: show action queue -> show the first one -> what is its status resolves to first action.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr

ACTION_PREVIEW_RESPONSE = """\
ACTION: Build a Credit/Funding Readiness Checklist lead magnet

Status: assigned
Scout: content_intelligence_scout
Next: Ray review — approve before publishing
ID: act_b5b81b3d5e

Evidence:
docs/reports/actions/hermes_action_queue.jsonl
"""


def test_extract_action_preview_context():
    """format_action_preview_response output is now recognized as action context."""
    ctx = ccr.extract_context_from_response("show the first one", ACTION_PREVIEW_RESPONSE)
    assert ctx is not None, "Expected context from ACTION: ... response"
    assert ctx["primary_object_type"] == "action"
    assert ctx["primary_object_id"] == "act_b5b81b3d5e"
    assert "Credit" in ctx["primary_object_title"]
    assert ctx["related_scout"] == "content_intelligence_scout"
    assert ctx["status"] == "assigned"


def test_resolve_status_after_action_preview():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("show the first one", ACTION_PREVIEW_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("what is its status")
                assert result is not None
                assert result["action"] == "status"
                assert result["context"]["primary_object_id"] == "act_b5b81b3d5e"


def test_resolve_status_question_mark_phrase():
    """is_followup_phrase strips trailing ? so 'what is its status?' is detected."""
    assert ccr.is_followup_phrase("what is its status?")
    assert ccr.is_followup_phrase("status?")
    assert ccr.is_followup_phrase("is it done?")
    assert ccr.is_followup_phrase("who has it?")


def test_new_status_phrases_detected():
    for phrase in [
        "status",
        "where are we with it",
        "what happened with it",
        "is it done",
        "is it assigned",
        "who has it",
        "what is next for it",
        "what is next",
    ]:
        assert ccr.is_followup_phrase(phrase), f"Expected '{phrase}' to be a followup phrase"


def test_direct_context_record_then_resolve():
    """_cmd_show_first_action records context directly; resolve_reference works afterward."""
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                # Simulate what _cmd_show_first_action does
                ccr.record_context_event({
                    "primary_object_type": "action",
                    "primary_object_id": "act_b5b81b3d5e",
                    "primary_object_title": "Build a Credit/Funding Readiness Checklist lead magnet",
                    "primary_object_path": "docs/reports/actions/hermes_action_queue.jsonl",
                    "related_action_id": "act_b5b81b3d5e",
                    "related_scout": "content_intelligence_scout",
                    "status": "assigned",
                    "evidence_path": "docs/reports/actions/hermes_action_queue.jsonl",
                })
                result = ccr.resolve_reference("what is its status")
                assert result is not None
                assert result["action"] == "status"
                assert result["context"]["status"] == "assigned"
                assert result["context"]["related_scout"] == "content_intelligence_scout"


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
