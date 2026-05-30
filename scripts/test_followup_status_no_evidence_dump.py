"""
test_followup_status_no_evidence_dump.py
Status follow-ups must not produce generic evidence dumps or stale memory.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_conversation_context_resolver import is_followup_phrase
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


def _is_evidence_dump(text: str) -> bool:
    t = text.lower()
    return any(m.lower() in t for m in EVIDENCE_DUMP_MARKERS)


def test_status_is_followup():
    for phrase in ["what is its status", "what is its status?", "status", "who has it", "is it done"]:
        assert is_followup_phrase(phrase), f"Expected followup: {phrase}"


def test_fallback_status_no_stale_memory():
    result = _fallback_data_block("what is its status", STALE_EXEC)
    assert "OFFLINE" not in result
    assert "Beehiiv" not in result
    assert "YouTube Studio" not in result


def test_fallback_status_question_mark_no_stale_memory():
    result = _fallback_data_block("what is its status?", STALE_EXEC)
    assert "OFFLINE" not in result


def test_fallback_who_has_it_no_dump():
    result = _fallback_data_block("who has it", STALE_EXEC)
    assert not _is_evidence_dump(result), f"Evidence dump in response: {result[:200]}"


def test_fallback_is_it_done_no_dump():
    result = _fallback_data_block("is it done", STALE_EXEC)
    assert not _is_evidence_dump(result)


def test_fallback_what_is_next_no_dump():
    result = _fallback_data_block("what is next", STALE_EXEC)
    assert not _is_evidence_dump(result)


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
