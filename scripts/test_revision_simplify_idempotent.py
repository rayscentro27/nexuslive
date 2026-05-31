"""
test_revision_simplify_idempotent.py
Simplifying an already-simplified draft must not duplicate any content.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine

ORIGINAL_DRAFT = """\
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

---

## Compliance Note

*This checklist is for educational purposes only.*

---

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review and approval before any use.*
"""


def test_first_simplify_adds_marker():
    result = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert result.count("Simplified — Plain English Edition") == 1


def test_first_simplify_adds_start_here():
    result = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert result.count("## Start Here") == 1


def test_second_simplify_does_not_duplicate_marker():
    first = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    second = engine.simplify_checklist_draft(first, "20260531_140000_000")
    count = second.count("Simplified — Plain English Edition")
    assert count == 1, f"Expected 1 Simplified marker, got {count}"


def test_second_simplify_does_not_duplicate_start_here():
    first = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    second = engine.simplify_checklist_draft(first, "20260531_140000_000")
    count = second.count("## Start Here")
    assert count == 1, f"Expected 1 Start Here section, got {count}"


def test_third_simplify_still_idempotent():
    first = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    second = engine.simplify_checklist_draft(first, "20260531_140000_000")
    third = engine.simplify_checklist_draft(second, "20260531_150000_000")
    assert third.count("Simplified — Plain English Edition") == 1
    assert third.count("## Start Here") == 1


def test_simplify_preserves_compliance_note():
    result = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert "educational purposes only" in result


def test_simplify_preserves_internal_draft_notice():
    result = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert "Internal" in result
    assert "Not for publication" in result or "Pending Ray's review" in result


def test_simplify_updates_timestamp():
    result = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert "20260531_130000_000" in result


def test_has_simplified_marker_helper():
    assert not engine.has_simplified_marker(ORIGINAL_DRAFT)
    simplified = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert engine.has_simplified_marker(simplified)


def test_has_start_here_section_helper():
    assert not engine.has_start_here_section(ORIGINAL_DRAFT)
    simplified = engine.simplify_checklist_draft(ORIGINAL_DRAFT, "20260531_130000_000")
    assert engine.has_start_here_section(simplified)


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
