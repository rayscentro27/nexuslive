"""
test_followup_unresolved_clarification.py
When context is stale or missing, format_unresolved_reference_response asks a clarifying question.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr


def test_no_context_returns_clarification():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "missing.json"):
            response = ccr.format_unresolved_reference_response("show it")
            assert "checklist" in response.lower() or "say" in response.lower()
            assert len(response) > 10


def test_with_context_mentions_object_title():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ccr.record_context_event({
                    "primary_object_type": "content_draft",
                    "primary_object_title": "Credit/Funding Readiness Checklist",
                })
                response = ccr.format_unresolved_reference_response("show it")
                assert "Credit" in response or "content draft" in response


def test_resolve_reference_no_context_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "missing.json"):
            result = ccr.resolve_reference("show it")
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
