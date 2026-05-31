"""
test_revision_followup_no_evidence_dump.py
Revision instructions must never return generic evidence dumps or stale memory.
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


def test_revision_phrases_are_followup():
    for phrase in [
        "make it simpler", "simplify it", "make it more professional",
        "make it better", "improve it", "revise it",
        "turn it into a lead magnet", "create a short video script from this",
        "create a newsletter from this",
    ]:
        assert is_followup_phrase(phrase), f"Expected revision phrase to be followup: {phrase}"


def test_revision_phrases_with_question_mark():
    for phrase in ["make it simpler?", "improve it?"]:
        assert is_followup_phrase(phrase), f"With trailing ?: {phrase}"


def test_fallback_make_it_simpler_no_stale_memory():
    result = _fallback_data_block("make it simpler", STALE_EXEC)
    assert not _has_evidence_dump(result), f"Evidence dump: {result[:200]}"


def test_fallback_lead_magnet_no_stale_memory():
    result = _fallback_data_block("turn it into a lead magnet", STALE_EXEC)
    assert "OFFLINE" not in result


def test_fallback_video_script_no_stale_memory():
    result = _fallback_data_block("create a short video script from this", STALE_EXEC)
    assert not _has_evidence_dump(result)


def test_unresolved_revision_gives_guidance():
    resp = format_unresolved_reference_response("make it simpler")
    assert resp
    assert not _has_evidence_dump(resp)
    assert "error" not in resp.lower()


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
