"""
test_followup_action_reference.py
"show the first one" after ACTION QUEUE response resolves to the first action.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr


ACTION_QUEUE_RESPONSE = """\
ACTION QUEUE

1. Create Credit/Funding Readiness Checklist (act_aa99698ef8)
   Status: open
   Scout: content_intelligence_scout

2. Build Nexus onboarding sequence
   Status: open

Evidence: docs/reports/actions/hermes_action_queue.jsonl
"""


def test_extract_action_queue_context():
    ctx = ccr.extract_context_from_response("show action queue", ACTION_QUEUE_RESPONSE)
    assert ctx is not None
    assert ctx["primary_object_type"] == "action"
    assert ctx["related_action_id"] == "act_aa99698ef8"


def test_resolve_action_reference():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("show action queue", ACTION_QUEUE_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_action_reference("show the first one")
                assert result is not None
                assert result["primary_object_type"] == "action"


def test_resolve_status_after_action():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("show action queue", ACTION_QUEUE_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("what is its status")
                assert result is not None
                assert result["action"] == "status"


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
