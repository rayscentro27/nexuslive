"""
test_followup_status_unresolved_clarification.py
When context is absent, status follow-ups return a clarifying question, not an error or evidence dump.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr
from lib.hermes_response_quality import _fallback_data_block


def test_no_context_returns_clarification_not_error():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "missing.json"):
            resp = ccr.format_unresolved_reference_response("status")
            assert resp
            assert "error" not in resp.lower()
            assert "exception" not in resp.lower()


def test_no_context_clarification_is_actionable():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "missing.json"):
            resp = ccr.format_unresolved_reference_response("status")
            assert "checklist" in resp.lower() or "say" in resp.lower() or "which" in resp.lower()


def test_no_context_fallback_still_no_stale_memory():
    result = _fallback_data_block("status", "Ollama OFFLINE\nBeehiiv pending")
    assert "OFFLINE" not in result


def test_with_action_context_mentions_title():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ccr.record_context_event({
                    "primary_object_type": "action",
                    "primary_object_id": "act_b5b81b3d5e",
                    "primary_object_title": "Build a Credit/Funding Readiness Checklist lead magnet",
                    "status": "assigned",
                })
                resp = ccr.format_unresolved_reference_response("status")
                assert "Credit" in resp or "action" in resp.lower()


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
