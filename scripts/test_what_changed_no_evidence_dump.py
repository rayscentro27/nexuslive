"""
test_what_changed_no_evidence_dump.py
'what changed?' must never return strategic evidence dumps or stale memory.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_conversation_context_resolver import is_followup_phrase, format_unresolved_reference_response
from lib.hermes_response_quality import _fallback_data_block

STALE_EXEC = (
    "Ollama (netcup, localhost:11555) — OFFLINE\n"
    "Beehiiv newsletter — login session pending\n"
    "YouTube Studio — 6 profile links not yet added\n"
)

EVIDENCE_DUMP_MARKERS = [
    "strategic context from evidence",
    "verified artifacts",
    "artifact inventory",
    "handoff dump",
    "OFFLINE",
    "Beehiiv",
    "YouTube Studio",
]


def _has_evidence_dump(text: str) -> bool:
    t = text.lower()
    return any(m.lower() in t for m in EVIDENCE_DUMP_MARKERS)


def test_what_changed_is_followup():
    for phrase in ["what changed", "what changed?", "compare it", "show differences", "what improved"]:
        assert is_followup_phrase(phrase), f"Expected followup: {phrase}"


def test_fallback_what_changed_no_stale_memory():
    result = _fallback_data_block("what changed", STALE_EXEC)
    assert not _has_evidence_dump(result), f"Evidence dump leaked: {result[:200]}"


def test_fallback_compare_it_no_stale_memory():
    result = _fallback_data_block("compare it", STALE_EXEC)
    assert "OFFLINE" not in result


def test_fallback_show_differences_no_stale_memory():
    result = _fallback_data_block("show differences", STALE_EXEC)
    assert not _has_evidence_dump(result)


def test_unresolved_compare_asks_clarification():
    resp = format_unresolved_reference_response("what changed")
    assert resp
    assert "OFFLINE" not in resp
    assert "Beehiiv" not in resp


def test_format_unresolved_no_error():
    resp = format_unresolved_reference_response("compare versions")
    assert "error" not in resp.lower()
    assert "exception" not in resp.lower()


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
