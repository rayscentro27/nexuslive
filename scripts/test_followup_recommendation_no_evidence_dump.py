"""
test_followup_recommendation_no_evidence_dump.py
Recommendation follow-ups must never return generic evidence dumps.
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
    "i can answer from verified artifacts",
    "artifact inventory",
    "handoff dump",
    "OFFLINE",
    "Beehiiv",
    "YouTube Studio",
]


def _has_evidence_dump(text: str) -> bool:
    t = text.lower()
    return any(m.lower() in t for m in EVIDENCE_DUMP_MARKERS)


def test_recommend_phrases_are_followup():
    for phrase in [
        "what do you recommend",
        "what do you recommend next",
        "what should i do next",
        "what is your recommendation",
        "should we keep this",
        "is this good",
        "what would you improve",
        "what is the next best move",
    ]:
        assert is_followup_phrase(phrase), f"Not a followup: {phrase}"


def test_fallback_what_do_you_recommend_no_stale_memory():
    result = _fallback_data_block("what do you recommend", STALE_EXEC)
    assert not _has_evidence_dump(result), f"Evidence dump: {result[:200]}"


def test_fallback_what_should_i_do_next_no_stale_memory():
    result = _fallback_data_block("what should i do next", STALE_EXEC)
    assert "OFFLINE" not in result
    assert not _has_evidence_dump(result)


def test_fallback_is_this_good_no_evidence_dump():
    result = _fallback_data_block("is this good", STALE_EXEC)
    assert not _has_evidence_dump(result)


def test_fallback_what_is_the_next_best_move_no_evidence_dump():
    result = _fallback_data_block("what is the next best move", STALE_EXEC)
    assert not _has_evidence_dump(result)


def test_unresolved_recommendation_gives_guidance():
    resp = format_unresolved_reference_response("what do you recommend")
    assert resp
    assert not _has_evidence_dump(resp)
    assert "error" not in resp.lower()


def test_no_recommendation_phrase_dumps_beehiiv():
    for phrase in [
        "what do you recommend",
        "what is your recommendation",
        "should we keep this",
        "is this good",
        "what would you improve",
        "what is the next best move",
        "what should i do next",
    ]:
        result = _fallback_data_block(phrase, STALE_EXEC)
        assert "Beehiiv" not in result, f"Beehiiv in result for '{phrase}'"
        assert "OFFLINE" not in result, f"OFFLINE in result for '{phrase}'"


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
