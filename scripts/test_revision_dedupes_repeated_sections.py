"""
test_revision_dedupes_repeated_sections.py
dedupe_repeated_sections and normalize_revision_output remove duplicate ## sections.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_content_revision_engine import (
    dedupe_repeated_sections,
    normalize_revision_output,
    _remove_duplicate_lines,
    cleanup_draft,
)

DRAFT_WITH_DUP_SECTIONS = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*
*(Simplified — Plain English Edition)*

## Start Here

Step 1. Register your business.

## Who This Checklist Is For

Business owners.

## Start Here

Step 1. Register your business.

## Compliance Note

*For educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Simplified Edition — Pending Ray's review and approval before any use.*
"""

DRAFT_WITH_DUP_SUBTITLE = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*
*(Simplified — Plain English Edition)*

## Who This Checklist Is For

Business owners.
"""


def test_dedupe_removes_duplicate_section():
    result = dedupe_repeated_sections(DRAFT_WITH_DUP_SECTIONS)
    assert result.count("## Start Here") == 1, f"Expected 1, got {result.count('## Start Here')}"


def test_dedupe_keeps_other_sections():
    result = dedupe_repeated_sections(DRAFT_WITH_DUP_SECTIONS)
    assert "## Who This Checklist Is For" in result
    assert "## Compliance Note" in result


def test_dedupe_preserves_compliance():
    result = dedupe_repeated_sections(DRAFT_WITH_DUP_SECTIONS)
    assert "educational purposes only" in result


def test_remove_duplicate_lines_collapses_subtitle():
    result = _remove_duplicate_lines(DRAFT_WITH_DUP_SUBTITLE)
    assert result.count("Simplified — Plain English Edition") == 1


def test_normalize_removes_both_dup_subtitle_and_section():
    result = normalize_revision_output(DRAFT_WITH_DUP_SECTIONS)
    assert result.count("Simplified — Plain English Edition") == 1
    assert result.count("## Start Here") == 1


def test_cleanup_draft_removes_duplicates():
    result = cleanup_draft(DRAFT_WITH_DUP_SECTIONS, "20260531_130000_000")
    assert result.count("## Start Here") == 1
    assert result.count("Simplified — Plain English Edition") == 1


def test_cleanup_draft_updates_timestamp():
    result = cleanup_draft(DRAFT_WITH_DUP_SECTIONS, "20260531_130000_000")
    assert "20260531_130000_000" in result


def test_cleanup_draft_adds_cleaned_edition_note():
    result = cleanup_draft(DRAFT_WITH_DUP_SECTIONS, "20260531_130000_000")
    assert "Cleaned Edition" in result


def test_cleanup_clean_draft_is_no_op_structurally():
    """Cleaning a draft with no duplicates should not alter its section count."""
    clean_draft = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*

## Start Here

Step 1. Register your business.

## Who This Checklist Is For

Business owners.

## Compliance Note

*For educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Pending Ray's review.*
"""
    result = cleanup_draft(clean_draft, "20260531_130000_000")
    assert result.count("## Start Here") == 1
    assert result.count("## Who This Checklist Is For") == 1
    assert result.count("## Compliance Note") == 1


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
