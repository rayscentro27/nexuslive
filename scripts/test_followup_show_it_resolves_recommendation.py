"""
test_followup_show_it_resolves_recommendation.py
"show it" after a review_first recommendation resolves to the opportunity context.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr


REVIEW_FIRST_RESPONSE = """\
Review this first: Credit/Funding Readiness Checklist

Why: fastest reviewable revenue asset — free to produce, aligns with 30-day goal.

Action: act_aa99698ef8
Evidence: docs/reports/actions/hermes_action_queue.jsonl
"""


def test_extract_review_first_context():
    ctx = ccr.extract_context_from_response("what should i review first", REVIEW_FIRST_RESPONSE)
    assert ctx is not None
    assert ctx["primary_object_type"] == "opportunity"
    assert "Credit" in ctx["primary_object_title"]


def test_resolve_show_it_after_review_first():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("what should i review first", REVIEW_FIRST_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("show it")
                assert result is not None
                assert result["action"] == "view"
                assert result["context"]["primary_object_type"] == "opportunity"


def test_resolve_recommendation_reference():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("what should i review first", REVIEW_FIRST_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_recommendation_reference("show it")
                assert result is not None
                assert result["primary_object_type"] == "opportunity"


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
