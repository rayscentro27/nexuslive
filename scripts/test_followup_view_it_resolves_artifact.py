"""
test_followup_view_it_resolves_artifact.py
"can i view it" after a content_draft response resolves to the draft path.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr


CONTENT_DRAFT_RESPONSE = """\
CONTENT DRAFT CREATED

I created the first internal draft for review.

Draft:
Credit/Funding Readiness Checklist

Status:
Internal draft only.

Evidence:
- Draft: docs/reports/content/credit_funding_readiness_checklist_draft_20260530_120000.md
- Action: act_aa99698ef8
"""


def test_extract_content_draft_context():
    ctx = ccr.extract_context_from_response("create first draft", CONTENT_DRAFT_RESPONSE)
    assert ctx is not None
    assert ctx["primary_object_type"] == "content_draft"
    assert "content" in ctx["primary_object_path"]
    assert ctx["related_action_id"] == "act_aa99698ef8"


def test_resolve_view_after_draft():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("create first draft", CONTENT_DRAFT_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("can i view it")
                assert result is not None
                assert result["action"] == "view"
                assert result["context"]["primary_object_type"] == "content_draft"


def test_resolve_show_it_after_draft():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("create first draft", CONTENT_DRAFT_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("show it")
                assert result is not None
                assert result["action"] == "view"


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
