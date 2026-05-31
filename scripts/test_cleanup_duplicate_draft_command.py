"""
test_cleanup_duplicate_draft_command.py
"clean it up" creates a new artifact with duplicates removed.
"""
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_content_revision_engine as engine

DRAFT_WITH_DUPES = """\
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

*This checklist is for educational purposes only.*

*Internal draft — 20260531_120000_000 UTC — Simplified Edition — Pending Ray's review and approval before any use.*
"""


def test_cleanup_resolve_instruction():
    assert engine.resolve_revision_instruction("clean it up") == "cleaned"
    assert engine.resolve_revision_instruction("remove duplicates") == "cleaned"
    assert engine.resolve_revision_instruction("fix duplicate sections") == "cleaned"
    assert engine.resolve_revision_instruction("clean up the draft") == "cleaned"


def test_cleanup_creates_artifact():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
    assert result["created"] is True
    assert "cleaned" in result["path"]


def test_cleanup_removes_duplicate_start_here():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
            new_path = Path(tmp) / result["path"]
            cleaned_text = new_path.read_text()
    assert cleaned_text.count("## Start Here") == 1, \
        f"Expected 1 Start Here, got {cleaned_text.count('## Start Here')}"


def test_cleanup_removes_duplicate_subtitle():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
            new_path = Path(tmp) / result["path"]
            cleaned_text = new_path.read_text()
    assert cleaned_text.count("Simplified — Plain English Edition") == 1, \
        f"Expected 1 subtitle, got {cleaned_text.count('Simplified — Plain English Edition')}"


def test_cleanup_preserves_compliance():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
            new_path = Path(tmp) / result["path"]
            cleaned_text = new_path.read_text()
    assert "educational purposes only" in cleaned_text


def test_cleanup_preserves_internal_draft_notice():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
            new_path = Path(tmp) / result["path"]
            cleaned_text = new_path.read_text()
    assert "Pending Ray's review" in cleaned_text or "Not for publication" in cleaned_text


def test_cleanup_response_has_correct_wording():
    with tempfile.TemporaryDirectory() as tmp:
        content_dir = Path(tmp) / "docs" / "reports" / "content"
        content_dir.mkdir(parents=True)
        prev = content_dir / "credit_funding_readiness_checklist_draft_20260531_120000_000_simplified.md"
        prev.write_text(DRAFT_WITH_DUPES)
        with patch.object(engine, "_CONTENT_DIR", content_dir), \
             patch.object(engine, "_ROOT", Path(tmp)):
            result = engine.revise_content_draft(prev, "cleaned")
            resp = engine.format_revision_created_response(result)
    assert "CONTENT DRAFT VERSION CREATED" in resp
    assert "cleaned" in resp.lower()
    assert "Internal draft only" in resp
    assert "what changed" in resp.lower()


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
