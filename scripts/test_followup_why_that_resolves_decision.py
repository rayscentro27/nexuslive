"""
test_followup_why_that_resolves_decision.py
"why did you pick that" resolves to why_selected from the last context.
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


def test_resolve_why_after_review_first():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("what should i review first", REVIEW_FIRST_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("why did you pick that")
                assert result is not None
                assert result["action"] == "why"
                assert result["context"]["primary_object_type"] == "opportunity"
                assert "why_selected" in result["context"]


def test_resolve_why_variants():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("what should i review first", REVIEW_FIRST_RESPONSE)
                ccr.record_context_event(ctx)
                for phrase in ["why that one", "why that", "explain your choice", "why did you choose that"]:
                    result = ccr.resolve_reference(phrase)
                    assert result is not None and result["action"] == "why", f"Failed for: {phrase}"


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
