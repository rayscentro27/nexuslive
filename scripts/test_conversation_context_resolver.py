"""
test_conversation_context_resolver.py
Tests for hermes_conversation_context_resolver — storage and phrase detection.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr


def test_is_followup_phrase_view():
    assert ccr.is_followup_phrase("show it")
    assert ccr.is_followup_phrase("can i view it")
    assert ccr.is_followup_phrase("view it")
    assert ccr.is_followup_phrase("see it")


def test_is_followup_phrase_why():
    assert ccr.is_followup_phrase("why did you pick that")
    assert ccr.is_followup_phrase("why that one")
    assert ccr.is_followup_phrase("explain your choice")


def test_is_followup_phrase_status():
    assert ccr.is_followup_phrase("what is its status")
    assert ccr.is_followup_phrase("what happened with that")


def test_is_followup_phrase_action():
    assert ccr.is_followup_phrase("approve it")
    assert ccr.is_followup_phrase("who is working on it")


def test_not_followup_phrase():
    assert not ccr.is_followup_phrase("create first draft")
    assert not ccr.is_followup_phrase("what should i review first")
    assert not ccr.is_followup_phrase("show action queue")
    assert not ccr.is_followup_phrase("")


def test_record_and_get_context():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                event = {"primary_object_type": "content_draft", "primary_object_id": "act_aa99698ef8"}
                ccr.record_context_event(event)
                result = ccr.get_last_context()
                assert result is not None
                assert result["primary_object_type"] == "content_draft"
                assert result["primary_object_id"] == "act_aa99698ef8"
                assert "timestamp" in result


def test_get_last_context_missing():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "missing.json"):
            assert ccr.get_last_context() is None


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
