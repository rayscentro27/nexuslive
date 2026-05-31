"""
test_followup_recommendation_resolves_draft.py
"what do you recommend" after showing/cleaning a draft resolves to the latest draft.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_conversation_context_resolver as ccr
import lib.hermes_content_revision_engine as engine
import lib.hermes_content_artifact_builder as cab
from lib.hermes_draft_recommendation_engine import (
    recommend_next_step_for_draft,
    format_draft_recommendation_response,
)

SIMPLIFIED_DRAFT = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*

## Start Here

Work through these in order.

## Who This Checklist Is For

Business owners.

## 1. Business Setup Readiness

- [ ] **Business entity formed**
- [ ] **EIN obtained**

## Compliance Note

*Educational purposes only.*

*Internal draft — 20260531_130000_000 UTC — Simplified Edition — Pending Ray's review.*
"""


def test_recommend_phrases_are_followup():
    for phrase in [
        "what do you recommend",
        "what do you recommend next",
        "what should i do next",
        "what is your recommendation",
        "should we keep this",
        "is this good",
        "what would you improve",
        "what is the next best move",
        "what should we do with it",
        "what should i do with it",
    ]:
        assert ccr.is_followup_phrase(phrase), f"Expected followup: {phrase}"


def test_recommend_phrases_with_question_mark():
    for phrase in ["what do you recommend?", "is this good?", "is it ready?"]:
        assert ccr.is_followup_phrase(phrase), f"With trailing ?: {phrase}"


def test_resolve_reference_returns_recommend_action():
    with tempfile.TemporaryDirectory() as tmp:
        ctx_file = Path(tmp) / "ctx.json"
        with patch.object(ccr, "_CONTEXT_FILE", ctx_file):
            ccr.record_context_event({
                "primary_object_type": "content_draft",
                "primary_object_path": "docs/reports/content/checklist_draft_20260531.md",
                "primary_object_title": "Credit checklist",
            })
            ref = ccr.resolve_reference("what do you recommend")
    assert ref is not None
    assert ref["action"] == "recommend"
    assert ref["context"]["primary_object_type"] == "content_draft"


def test_resolve_reference_is_this_good():
    with tempfile.TemporaryDirectory() as tmp:
        ctx_file = Path(tmp) / "ctx.json"
        with patch.object(ccr, "_CONTEXT_FILE", ctx_file):
            ccr.record_context_event({
                "primary_object_type": "content_draft",
                "primary_object_path": "docs/reports/content/checklist_draft_20260531.md",
            })
            ref = ccr.resolve_reference("is this good")
    assert ref is not None
    assert ref["action"] == "recommend"


def test_recommend_after_draft_context_gives_draft_recommendation():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        draft_path = content_dir / "credit_funding_readiness_checklist_draft_20260531_130000_000_simplified.md"
        draft_path.write_text(SIMPLIFIED_DRAFT)
        ctx_file = Path(tmp) / "ctx.json"
        with patch.object(ccr, "_CONTEXT_FILE", ctx_file):
            ccr.record_context_event({
                "primary_object_type": "content_draft",
                "primary_object_path": str(draft_path.relative_to(tmp)),
                "primary_object_title": "Simplified checklist",
            })
            result = recommend_next_step_for_draft(draft_path)
            resp = format_draft_recommendation_response(result)
    assert "RECOMMENDATION" in resp
    assert "Next best move:" in resp
    assert "Approval" in resp


def test_recommend_response_references_draft_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "credit_funding_readiness_checklist_draft_20260531_simplified.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Evidence:" in resp


def test_recommend_after_cleanup_workflow():
    """Full workflow: create draft → simplify → clean → recommend."""
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        ctx_file = Path(tmp) / "ctx.json"

        # Create first draft
        with patch.object(cab, "_CONTENT_DIR", content_dir), \
             patch.object(cab, "_ROOT", Path(tmp)):
            r0 = cab.create_credit_funding_readiness_checklist_draft(new_version=False)
            resp0 = cab.format_content_created_response(r0)

        first_draft = sorted(content_dir.glob("*_draft_*.md"), reverse=True)[0]

        # Simplify
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            r1 = engine.revise_content_draft(first_draft, "simplified")
        simplified_path = Path(tmp) / r1["path"]

        # Clean
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            r2 = engine.revise_content_draft(simplified_path, "cleaned")
        cleaned_path = Path(tmp) / r2["path"]

        # Recommend from cleaned
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)

    assert "RECOMMENDATION" in resp
    assert "Next best move:" in resp
    assert "lead magnet" in resp.lower() or "recommend" in resp.lower()
    assert "strategic context from evidence" not in resp.lower()


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
