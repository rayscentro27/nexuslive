"""
test_followup_what_changed_resolves_latest_version.py
"what changed?" after new version creation resolves to the new content_draft context.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr

NEW_VERSION_RESPONSE = """\
CONTENT DRAFT VERSION CREATED

I created a new internal version for review.

Draft:
Credit/Funding Readiness Checklist — New Version

Status:
Internal draft only.

Evidence:
- New draft: docs/reports/content/credit_funding_readiness_checklist_draft_20260531_120001.md
- Previous draft: docs/reports/content/credit_funding_readiness_checklist_draft_20260530_100000.md
- Action: act_aa99698ef8
- Decision log: docs/reports/decisions/hermes_decision_log.jsonl

Next:
Ask 'what changed?' to compare this version with the previous draft.
"""


def test_extract_new_version_context():
    ctx = ccr.extract_context_from_response("create a new version", NEW_VERSION_RESPONSE)
    assert ctx is not None
    assert ctx["primary_object_type"] == "content_draft"
    assert ctx["is_new_version"] is True
    assert "20260531" in ctx["primary_object_path"]
    assert "20260530" in ctx["previous_object_path"]


def test_what_changed_is_compare_followup():
    for phrase in ["what changed", "what changed?", "compare it", "compare versions", "show differences"]:
        assert ccr.is_followup_phrase(phrase), f"Expected compare followup: {phrase}"


def test_resolve_compare_after_new_version():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
            with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                ctx = ccr.extract_context_from_response("create a new version", NEW_VERSION_RESPONSE)
                ccr.record_context_event(ctx)
                result = ccr.resolve_reference("what changed")
                assert result is not None
                assert result["action"] == "compare"
                assert result["context"]["is_new_version"] is True
                assert result["context"]["previous_object_path"] != ""


def test_compare_phrases_in_all_followup_phrases():
    for phrase in ["what changed", "compare it", "show differences", "what improved"]:
        assert phrase in ccr.ALL_FOLLOWUP_PHRASES, f"Missing from ALL_FOLLOWUP_PHRASES: {phrase}"


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
