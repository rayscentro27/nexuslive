"""
test_content_revision_engine.py
Tests for the hermes_content_revision_engine module.
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

> **INTERNAL ONLY.**

---

## Who This Checklist Is For

Business owners who want to apply for business funding.

---

## 1. Business Setup Readiness

- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp registered with your state
- [ ] **EIN obtained** — Employer Identification Number from the IRS (free at irs.gov)
- [ ] **NAICS code** — industry classification code; know yours before applying

---

## 2. Credit Profile Readiness

- [ ] **Know your score** — check current FICO 8 score (FICO SBSS matters for SBA)
- [ ] **Credit utilization** — revolving balances below 30% of limits
- [ ] **DUNS number** — register with D&B if you don't have one (free)

---

## Compliance Note

*This checklist is for educational purposes only.*

---

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review and approval before any use.*
"""


def test_simplify_adds_start_here():
    result = engine.simplify_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Start Here" in result


def test_simplify_applies_jargon_replacements():
    result = engine.simplify_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    # Check some replacements happened
    assert "business Tax ID" in result or "tax ID" in result.lower()


def test_simplify_notes_simplified_edition():
    result = engine.simplify_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Simplified" in result


def test_simplify_preserves_compliance():
    result = engine.simplify_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "educational purposes only" in result


def test_professionalize_adds_executive_section():
    result = engine.professionalize_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Executive Summary" in result or "Professional Edition" in result


def test_professionalize_notes_edition():
    result = engine.professionalize_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Professional Edition" in result


def test_improve_adds_items():
    result = engine.improve_checklist_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Improved Edition" in result


def test_lead_magnet_has_score_section():
    result = engine.convert_to_lead_magnet(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Score" in result
    assert "What Your Score Means" in result


def test_lead_magnet_has_nexus_cta():
    result = engine.convert_to_lead_magnet(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Nexus" in result


def test_video_script_has_hook():
    result = engine.convert_to_short_video_script(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Hook" in result or "hook" in result.lower()
    assert "CTA" in result or "cta" in result.lower()


def test_video_script_has_on_screen_text():
    result = engine.convert_to_short_video_script(SAMPLE_DRAFT, "20260531_130000_000")
    assert "On-Screen" in result or "on-screen" in result.lower()


def test_newsletter_has_subject_line():
    result = engine.convert_to_newsletter(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Subject" in result


def test_email_draft_has_subject():
    result = engine.convert_to_email_draft(SAMPLE_DRAFT, "20260531_130000_000")
    assert "Subject" in result


def test_revise_content_draft_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000.md"
        prev.write_text(SAMPLE_DRAFT)
        with patch.object(engine, "_CONTENT_DIR", content_dir):
            with patch.object(engine, "_ROOT", Path(tmp)):
                result = engine.revise_content_draft(prev, "simplified")
                assert result["created"] is True
                new_path = Path(tmp) / result["path"]
                assert new_path.exists()
                assert new_path.read_text() != SAMPLE_DRAFT


def test_revise_missing_file_returns_error():
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "missing.md"
        result = engine.revise_content_draft(missing, "simplified")
        assert result["created"] is False
        assert "error" in result


def test_format_revision_response_no_evidence_dump():
    result = {
        "created": True,
        "revision_type": "simplified",
        "path": "docs/reports/content/checklist_draft_20260531_simplified.md",
        "previous_path": "docs/reports/content/checklist_draft_20260530.md",
        "action_id": "act_aa99698ef8",
        "change_summary": ["Simplified intro", "Replaced jargon"],
    }
    resp = engine.format_revision_created_response(result)
    assert "CONTENT DRAFT VERSION CREATED" in resp
    assert "simplified" in resp.lower()
    assert "strategic context from evidence" not in resp.lower()
    assert "OFFLINE" not in resp


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
