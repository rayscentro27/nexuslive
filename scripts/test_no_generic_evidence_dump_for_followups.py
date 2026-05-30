"""
test_no_generic_evidence_dump_for_followups.py
Follow-up phrases must NOT produce a generic evidence inventory dump.
They should produce a targeted reply or a clarification question.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_conversation_context_resolver import (
    is_followup_phrase,
    format_unresolved_reference_response,
)


EVIDENCE_DUMP_MARKERS = [
    "verified-artifact inventory",
    "artifact inventory",
    "docs/reports/runtime",
    "handoff dump",
]


def _is_evidence_dump(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in EVIDENCE_DUMP_MARKERS)


def test_show_it_not_evidence_dump():
    assert is_followup_phrase("show it")
    response = format_unresolved_reference_response("show it")
    assert not _is_evidence_dump(response), f"Got evidence dump: {response[:200]}"


def test_can_i_view_it_not_evidence_dump():
    assert is_followup_phrase("can i view it")
    response = format_unresolved_reference_response("can i view it")
    assert not _is_evidence_dump(response)


def test_why_that_not_evidence_dump():
    assert is_followup_phrase("why that one")
    response = format_unresolved_reference_response("why that one")
    assert not _is_evidence_dump(response)


def test_status_not_evidence_dump():
    assert is_followup_phrase("what is its status")
    response = format_unresolved_reference_response("what is its status")
    assert not _is_evidence_dump(response)


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
