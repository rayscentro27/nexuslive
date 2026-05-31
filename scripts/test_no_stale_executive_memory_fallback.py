"""
test_no_stale_executive_memory_fallback.py
_fallback_data_block must NOT dump stale executive memory when message is a follow-up phrase.
"""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_response_quality as rq
import lib.hermes_conversation_context_resolver as ccr


STALE_EXEC_MEMORY = (
    "Ollama (netcup, localhost:11555) — OFFLINE\n"
    "Beehiiv newsletter — login session pending\n"
    "YouTube Studio — 6 profile links not yet added manually\n"
    "OpenRouter as content-tier provider — not yet in model_routing_rules\n"
)


def test_followup_not_stale_memory():
    result = rq._fallback_data_block("show it", STALE_EXEC_MEMORY)
    assert "OFFLINE" not in result, "Stale Ollama status leaked into follow-up response"
    assert "Beehiiv" not in result, "Stale Beehiiv status leaked into follow-up response"
    assert "YouTube Studio" not in result, "Stale YouTube Studio status leaked into follow-up response"


def test_followup_view_it_returns_clarification():
    result = rq._fallback_data_block("can i view it", STALE_EXEC_MEMORY)
    assert "OFFLINE" not in result
    assert len(result) > 5


def test_followup_why_that_returns_clarification():
    result = rq._fallback_data_block("why did you pick that", STALE_EXEC_MEMORY)
    assert "OFFLINE" not in result


def test_non_followup_returns_clean_clarification():
    result = rq._fallback_data_block("something totally random", STALE_EXEC_MEMORY)
    assert "specific question" in result.lower() or "nexus ceo briefing" in result.lower()
    assert "OFFLINE" not in result, "Stale exec context must not be dumped in fallback"
    assert "Quality escalation fallback" not in result


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
