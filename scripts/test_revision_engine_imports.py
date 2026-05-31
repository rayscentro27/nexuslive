"""
test_revision_engine_imports.py
Verify all imports used by the revision pipeline resolve without error.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_revision_engine_imports_cleanly():
    import lib.hermes_content_revision_engine as engine
    assert hasattr(engine, "revise_content_draft")
    assert hasattr(engine, "format_revision_created_response")
    assert hasattr(engine, "resolve_revision_instruction")
    assert hasattr(engine, "REVISION_INSTRUCTION_MAP")
    assert hasattr(engine, "find_latest_checklist_draft")


def test_artifact_version_compare_exports_find_latest():
    from lib.hermes_artifact_version_compare import find_latest_checklist_draft
    assert callable(find_latest_checklist_draft)


def test_artifact_version_compare_exports_find_pair():
    from lib.hermes_artifact_version_compare import find_latest_checklist_draft_pair
    assert callable(find_latest_checklist_draft_pair)


def test_telegram_bot_revision_import_chain():
    """Simulate the exact import chain _cmd_revise_draft uses."""
    from lib.hermes_content_revision_engine import (
        revise_content_draft, format_revision_created_response,
    )
    from lib.hermes_conversation_context_resolver import get_last_context
    from lib.hermes_artifact_version_compare import find_latest_checklist_draft as _find_latest
    assert callable(revise_content_draft)
    assert callable(format_revision_created_response)
    assert callable(get_last_context)
    assert callable(_find_latest)


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
