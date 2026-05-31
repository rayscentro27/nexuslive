"""
test_archived_memory_commands.py
Verifies the archived memory command route works correctly.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import _run_archived_executive_memory


def test_archived_memory_intent_classified():
    phrases = [
        "show archived memory",
        "load archived defaults",
        "what were the old defaults",
        "archived executive memory",
    ]
    for phrase in phrases:
        intent, _, _ = classify_intent(phrase)
        assert intent == "archived_executive_memory", (
            f"Phrase '{phrase}' classified as {intent}, expected archived_executive_memory"
        )


def test_archived_memory_handler_returns_evidence():
    status, evidence, rec = _run_archived_executive_memory()
    assert status == "healthy"
    assert isinstance(evidence, list)
    assert len(evidence) > 0
    assert "Archived" in str(evidence) or "ORIGINAL" in str(evidence)


def test_archived_memory_contains_stale_markers():
    status, evidence, rec = _run_archived_executive_memory()
    text = " ".join(evidence)
    assert "Ollama" in text or "Beehiiv" in text, (
        "Archived memory output should reference known stale defaults"
    )


def test_none_archived_phrases():
    phrases = [
        "system health",
        "show archived memory",
    ]
    for phrase in phrases:
        intent, _, _ = classify_intent(phrase)
        if phrase == "show archived memory":
            assert intent == "archived_executive_memory"
        else:
            assert intent != "archived_executive_memory"


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
