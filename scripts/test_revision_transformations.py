"""
test_revision_transformations.py
Each revision type produces a distinct, correct artifact.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine

SAMPLE_DRAFT = """\
# Credit/Funding Readiness Checklist
*Internal Draft — 20260531_120000_000 UTC — Not for publication*

## Who This Checklist Is For
Business owners who want funding.

## 1. Business Setup Readiness
- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp registered with your state
- [ ] **EIN obtained** — Employer Identification Number from the IRS (free at irs.gov)

## Compliance Note
*Educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review and approval before any use.*
"""


def _revise(revision_type: str):
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, revision_type)
                new_path = Path(tmp) / result["path"]
                return result, new_path.read_text() if new_path.exists() else ""


def test_simplified_artifact():
    result, text = _revise("simplified")
    assert result["created"]
    assert "simplified" in result["path"]
    assert "Start Here" in text
    assert text != SAMPLE_DRAFT


def test_professional_artifact():
    result, text = _revise("professional")
    assert result["created"]
    assert "professional" in result["path"]
    assert "Professional Edition" in text or "Executive" in text
    assert text != SAMPLE_DRAFT


def test_improved_artifact():
    result, text = _revise("improved")
    assert result["created"]
    assert "improved" in result["path"]
    assert "Improved" in text
    assert text != SAMPLE_DRAFT


def test_lead_magnet_artifact():
    result, text = _revise("lead_magnet")
    assert result["created"]
    assert "lead_magnet" in result["path"]
    assert "Score" in text
    assert "Nexus" in text


def test_short_video_script_artifact():
    result, text = _revise("short_video_script")
    assert result["created"]
    assert "short_video_script" in result["path"]
    assert "Hook" in text or "hook" in text.lower()
    assert "CTA" in text or "cta" in text.lower()


def test_newsletter_artifact():
    result, text = _revise("newsletter")
    assert result["created"]
    assert "newsletter" in result["path"]
    assert "Subject" in text


def test_email_draft_artifact():
    result, text = _revise("email_draft")
    assert result["created"]
    assert "email_draft" in result["path"]
    assert "Subject" in text


def test_all_artifacts_have_compliance_note():
    for rev_type in ["simplified", "professional", "lead_magnet", "short_video_script", "newsletter", "email_draft"]:
        result, text = _revise(rev_type)
        assert "educational purposes" in text.lower() or "compliance" in text.lower(), \
            f"No compliance note in {rev_type} artifact"


def test_all_artifacts_are_internal_only():
    for rev_type in ["simplified", "professional", "lead_magnet", "short_video_script"]:
        result, text = _revise(rev_type)
        assert "INTERNAL ONLY" in text or "Internal Draft" in text or "internal draft" in text.lower(), \
            f"No internal draft note in {rev_type} artifact"


def test_revision_instruction_map_coverage():
    """All phrases in REVISION_INSTRUCTION_MAP must map to a valid revision type."""
    valid_types = {"simplified", "professional", "improved", "lead_magnet",
                   "short_video_script", "newsletter", "email_draft"}
    for phrase, rev_type in engine.REVISION_INSTRUCTION_MAP.items():
        assert rev_type in valid_types, f"Unknown revision type '{rev_type}' for phrase '{phrase}'"


def test_context_updated_after_revision():
    """extract_context_from_response sees new draft path after revision response."""
    from lib.hermes_conversation_context_resolver import extract_context_from_response
    result = {
        "created": True,
        "revision_type": "simplified",
        "path": "docs/reports/content/credit_funding_readiness_checklist_draft_20260531_130000_000_simplified.md",
        "previous_path": "docs/reports/content/credit_funding_readiness_checklist_draft_20260531_120000_000.md",
        "action_id": "act_aa99698ef8",
        "change_summary": ["Simplified intro"],
    }
    response = engine.format_revision_created_response(result)
    ctx = extract_context_from_response("make it simpler", response)
    assert ctx is not None
    assert ctx["primary_object_type"] == "content_draft"
    assert "simplified" in ctx["primary_object_path"]
    assert ctx["previous_object_path"] != ""


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
