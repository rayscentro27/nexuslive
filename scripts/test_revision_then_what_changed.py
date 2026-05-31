"""
test_revision_then_what_changed.py
After 'make it simpler', 'what changed?' compares simplified draft against previous.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine
import lib.hermes_artifact_version_compare as avc
import lib.hermes_conversation_context_resolver as ccr

SAMPLE_DRAFT = """\
# Credit/Funding Readiness Checklist
*Internal Draft — 20260531_120000_000 UTC — Not for publication*

## Who This Checklist Is For

Business owners who want to apply for business funding.

## 1. Business Setup Readiness

- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp registered with your state
- [ ] **EIN obtained** — Employer Identification Number from the IRS (free at irs.gov)
- [ ] **NAICS code** — industry classification code; know yours before applying

## 2. Credit Profile Readiness

- [ ] **Know your score** — check current FICO 8 score (FICO SBSS matters for SBA)
- [ ] **Credit utilization** — revolving balances below 30% of limits

## Compliance Note

*This checklist is for educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review and approval before any use.*
"""


def test_simplified_draft_comparison_detects_changes():
    """summarize_markdown_changes must find differences between original and simplified."""
    from lib.hermes_artifact_version_compare import summarize_markdown_changes
    simplified = engine.simplify_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    changes = summarize_markdown_changes(SAMPLE_DRAFT, simplified)
    # Start Here section should be added, and sections should be changed (jargon replaced)
    assert changes["added"] or changes["changed"], f"No changes detected: {changes}"


def test_revision_context_has_previous_path():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
                    with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                        result = engine.revise_content_draft(prev, "simplified")
                        response = engine.format_revision_created_response(result)
                        ctx = ccr.extract_context_from_response("make it simpler", response)
                        assert ctx is not None, "Context must be extracted from revision response"
                        assert ctx["primary_object_type"] == "content_draft"
                        assert ctx["previous_object_path"] != ""


def test_what_changed_after_revision_resolves():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                with patch.object(ccr, "_RUNTIME_DIR", Path(tmp)):
                    with patch.object(ccr, "_CONTEXT_FILE", Path(tmp) / "ctx.json"):
                        result = engine.revise_content_draft(prev, "simplified")
                        response = engine.format_revision_created_response(result)
                        ctx = ccr.extract_context_from_response("make it simpler", response)
                        ccr.record_context_event(ctx)
                        ref = ccr.resolve_reference("what changed")
                        assert ref is not None
                        assert ref["action"] == "compare"
                        assert ref["context"]["previous_object_path"] != ""


def test_find_two_drafts_after_revision():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                with patch.object(avc, "_CONTENT_DIR", content_dir):
                    result = engine.revise_content_draft(prev, "simplified")
                    latest, previous = avc.find_two_latest_drafts()
                    assert latest is not None
                    assert previous is not None
                    assert latest != previous


def test_comparison_response_after_simplification():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                with patch.object(avc, "_CONTENT_DIR", content_dir):
                    with patch.object(avc, "_ROOT", Path(tmp)):
                        engine.revise_content_draft(prev, "simplified")
                        latest, previous = avc.find_two_latest_drafts()
                        comp = avc.format_version_comparison_response(previous, latest)
                        assert "DRAFT VERSION CHANGES" in comp
                        assert "Previous" in comp
                        assert "Latest" in comp
                        assert "strategic context from evidence" not in comp.lower()


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
