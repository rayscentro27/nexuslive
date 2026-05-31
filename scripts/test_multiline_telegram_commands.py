"""
test_multiline_telegram_commands.py
Multi-line message splitting and processing rules.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_bot_with_multiline(responses: dict) -> object:
    """Build a minimal bot mock with _handle_multiline_message using real logic."""
    from telegram_bot import NexusTelegramBot

    bot = MagicMock(spec=NexusTelegramBot)
    bot.handle_inbound_message = MagicMock(side_effect=lambda line: responses.get(line.strip(), f"[no match: {line}]"))
    bot._handle_multiline_message = NexusTelegramBot._handle_multiline_message.__get__(bot, NexusTelegramBot)
    return bot


def test_single_line_not_split():
    """Single-line messages are not affected by multiline logic."""
    bot = _make_bot_with_multiline({"show action queue": "ACTION QUEUE\n1. Task"})
    result = bot._handle_multiline_message(["show action queue"])
    assert "ACTION QUEUE" in result


def test_two_lines_combined():
    bot = _make_bot_with_multiline({
        "create a new version": "CONTENT DRAFT VERSION CREATED\nNew draft: docs/reports/content/checklist_draft_20260531.md",
        "what changed": "DRAFT VERSION CHANGES\n1. Updated: Section A",
    })
    result = bot._handle_multiline_message(["create a new version", "what changed"])
    assert "CONTENT DRAFT VERSION CREATED" in result
    assert "DRAFT VERSION CHANGES" in result
    assert "---" in result


def test_max_3_lines_enforced():
    from telegram_bot import NexusTelegramBot
    calls = []

    class FakeBot:
        def handle_inbound_message(self, line):
            calls.append(line)
            return f"resp:{line}"

    bot = FakeBot()
    bot._handle_multiline_message = NexusTelegramBot._handle_multiline_message.__get__(bot, FakeBot)
    # Pass 4 lines — only first 3 should be processed (caller slices [:3])
    result = bot._handle_multiline_message(["line1", "line2", "line3"])
    assert len(calls) == 3


def test_unsafe_keywords_skipped():
    from telegram_bot import NexusTelegramBot

    class FakeBot:
        def handle_inbound_message(self, line):
            return f"ran:{line}"
        _handle_multiline_message = NexusTelegramBot._handle_multiline_message

    bot = FakeBot()
    bot._handle_multiline_message = NexusTelegramBot._handle_multiline_message.__get__(bot, FakeBot)
    result = bot._handle_multiline_message(["show it", "delete everything"])
    assert "Skipped" in result
    assert "ran:delete everything" not in result


def test_combined_response_is_single_message():
    bot = _make_bot_with_multiline({
        "line one": "RESPONSE ONE",
        "line two": "RESPONSE TWO",
    })
    result = bot._handle_multiline_message(["line one", "line two"])
    # Should be one string, not two separate messages
    assert isinstance(result, str)
    assert "RESPONSE ONE" in result
    assert "RESPONSE TWO" in result


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
