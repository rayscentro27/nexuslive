"""
test_recommendation_after_cleanup_workflow.py
Full workflow: show it → clean it up → what changed → what do you recommend.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine
import lib.hermes_content_artifact_builder as cab
import lib.hermes_artifact_version_compare as avc
import lib.hermes_conversation_context_resolver as ccr
from lib.hermes_draft_recommendation_engine import (
    recommend_next_step_for_draft,
    format_draft_recommendation_response,
)


def _run_full_workflow(tmp: str):
    """Run create → simplify → clean workflow and return paths."""
    content_dir = Path(tmp) / "docs" / "reports" / "content"
    content_dir.mkdir(parents=True)

    with patch.object(cab, "_CONTENT_DIR", content_dir), \
         patch.object(cab, "_ROOT", Path(tmp)):
        r0 = cab.create_credit_funding_readiness_checklist_draft(new_version=False)

    first_draft = sorted(content_dir.glob("*_draft_*.md"), reverse=True)[0]

    with patch.object(engine, "_CONTENT_DIR", content_dir), \
         patch.object(engine, "_ROOT", Path(tmp)):
        r1 = engine.revise_content_draft(first_draft, "simplified")
        simplified_path = Path(tmp) / r1["path"]
        r2 = engine.revise_content_draft(simplified_path, "cleaned")
        cleaned_path = Path(tmp) / r2["path"]

    return content_dir, first_draft, simplified_path, cleaned_path


def test_recommendation_after_cleanup_is_specific():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir, first_draft, simplified_path, cleaned_path = _run_full_workflow(tmp)
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)
    assert "lead magnet" in resp.lower() or "video script" in resp.lower() or "recommend" in resp.lower()
    assert "Next best move:" in resp


def test_recommendation_after_cleanup_not_evidence_dump():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir, first_draft, simplified_path, cleaned_path = _run_full_workflow(tmp)
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)
    assert "strategic context from evidence" not in resp.lower()
    assert "artifact_inventory" not in resp.lower()
    assert "OFFLINE" not in resp
    assert "Beehiiv" not in resp


def test_recommendation_has_approval_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        _, _, _, cleaned_path = _run_full_workflow(tmp)
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)
    assert "Approval" in resp
    assert "publishing" in resp.lower() or "required" in resp.lower()


def test_recommendation_has_evidence_path():
    with tempfile.TemporaryDirectory() as tmp:
        _, _, _, cleaned_path = _run_full_workflow(tmp)
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)
    assert "Evidence:" in resp


def test_recommendation_has_reply_options():
    with tempfile.TemporaryDirectory() as tmp:
        _, _, _, cleaned_path = _run_full_workflow(tmp)
        result = recommend_next_step_for_draft(cleaned_path)
        resp = format_draft_recommendation_response(result)
    assert "Reply options:" in resp
    assert "turn it into a lead magnet" in resp.lower() or "create a short video script" in resp.lower()


def test_what_changed_before_recommendation_works():
    """what changed? before recommendation should still give comparison, not recommendation."""
    with tempfile.TemporaryDirectory() as tmp:
        content_dir, _, simplified_path, cleaned_path = _run_full_workflow(tmp)
        with patch.object(avc, "_CONTENT_DIR", content_dir), \
             patch.object(avc, "_ROOT", Path(tmp)):
            latest, previous = avc.find_two_latest_drafts()
            comp = avc.format_version_comparison_response(previous, latest)
    assert "DRAFT VERSION CHANGES" in comp
    assert "RECOMMENDATION" not in comp


def test_recommend_after_context_recorded():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir, _, simplified_path, cleaned_path = _run_full_workflow(tmp)
        ctx_file = Path(tmp) / "ctx.json"

        # Record context after cleanup
        resp2 = engine.format_revision_created_response({
            "created": True,
            "revision_type": "cleaned",
            "path": str(cleaned_path.relative_to(Path(tmp))),
            "previous_path": str(simplified_path.relative_to(Path(tmp))),
            "action_id": "act_test",
            "change_summary": ["Removed duplicates"],
        })
        with patch.object(ccr, "_CONTEXT_FILE", ctx_file):
            ctx = ccr.extract_context_from_response("clean it up", resp2)
            ccr.record_context_event(ctx)
            ref = ccr.resolve_reference("what do you recommend")

    assert ref is not None
    assert ref["action"] == "recommend"
    assert ref["context"]["primary_object_type"] == "content_draft"


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
