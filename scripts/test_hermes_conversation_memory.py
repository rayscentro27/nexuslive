#!/usr/bin/env python3
"""Tests for hermes_conversation_memory — short-term Telegram session memory."""
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import hermes_conversation_memory as cm

CHAT = "test_chat_123"
CHAT2 = "test_chat_456"


def _fresh():
    """Clear all sessions before each test."""
    with cm._lock:
        cm._sessions.clear()


class TestRecordAndRetrieve(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_record_and_get_history(self):
        cm.record_turn(CHAT, "user", "What AI providers are available?")
        cm.record_turn(CHAT, "assistant", "Nexus has OpenRouter, local Ollama, Claude Code, and OpenClaw.")
        history = cm.get_history(CHAT)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")

    def test_history_excludes_current_message(self):
        cm.record_turn(CHAT, "user", "First message")
        cm.record_turn(CHAT, "assistant", "First reply")
        history = cm.get_history(CHAT)
        # caller appends current message separately; history should have 2 prior turns
        self.assertEqual(len(history), 2)

    def test_empty_chat_returns_empty_history(self):
        self.assertEqual(cm.get_history("nonexistent_chat"), [])

    def test_rolling_window_truncates_at_max_turns(self):
        for i in range(25):
            cm.record_turn(CHAT, "user", f"message {i}")
            cm.record_turn(CHAT, "assistant", f"reply {i}")
        history = cm.get_history(CHAT)
        self.assertLessEqual(len(history), cm.MAX_TURNS)

    def test_different_chats_are_isolated(self):
        cm.record_turn(CHAT, "user", "Nexus question")
        cm.record_turn(CHAT2, "user", "Different question")
        self.assertEqual(len(cm.get_history(CHAT)), 1)
        self.assertEqual(len(cm.get_history(CHAT2)), 1)

    def test_empty_content_not_recorded(self):
        cm.record_turn(CHAT, "user", "")
        self.assertEqual(cm.get_history(CHAT), [])

    def test_empty_chat_id_not_recorded(self):
        cm.record_turn("", "user", "some message")
        # No sessions created
        with cm._lock:
            self.assertNotIn("", cm._sessions)


class TestTTLExpiration(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_expired_session_cleared(self):
        cm.record_turn(CHAT, "user", "Hello")
        # Manually backdate the turn's timestamp
        with cm._lock:
            for turn in cm._sessions[CHAT]:
                turn["ts"] = time.monotonic() - (cm.SESSION_TTL_SECONDS + 10)
        # Trigger prune via get_history
        history = cm.get_history(CHAT)
        self.assertEqual(history, [])

    def test_active_session_not_expired(self):
        cm.record_turn(CHAT, "user", "Recent message")
        history = cm.get_history(CHAT)
        self.assertEqual(len(history), 1)

    def test_idle_session_pruned_on_next_record(self):
        cm.record_turn(CHAT, "user", "Old message")
        with cm._lock:
            for turn in cm._sessions[CHAT]:
                turn["ts"] = time.monotonic() - (cm.SESSION_TTL_SECONDS + 10)
        # Recording a new turn to a different chat triggers prune
        cm.record_turn(CHAT2, "user", "New message")
        with cm._lock:
            self.assertNotIn(CHAT, cm._sessions)


class TestClearSession(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_clear_removes_history(self):
        cm.record_turn(CHAT, "user", "Some message")
        cm.record_turn(CHAT, "assistant", "Some reply")
        cm.clear_session(CHAT)
        self.assertEqual(cm.get_history(CHAT), [])

    def test_clear_nonexistent_session_noop(self):
        cm.clear_session("nonexistent")  # should not raise

    def test_clear_empty_chat_id_noop(self):
        cm.clear_session("")  # should not raise


class TestFollowupDetection(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_followup_detected_with_history(self):
        cm.record_turn(CHAT, "user", "What AI providers are available?")
        cm.record_turn(CHAT, "assistant", "OpenRouter, Ollama, Claude Code, OpenClaw.")
        self.assertTrue(cm.is_followup("which one should I use?", CHAT))

    def test_no_followup_without_history(self):
        self.assertFalse(cm.is_followup("which one should I use?", CHAT))

    def test_long_message_not_followup(self):
        cm.record_turn(CHAT, "user", "First message")
        long_msg = "Tell me all about the AI providers available and which ones are best for coding tasks in detail"
        self.assertFalse(cm.is_followup(long_msg, CHAT))

    def test_continue_is_followup(self):
        cm.record_turn(CHAT, "user", "What are the providers?")
        cm.record_turn(CHAT, "assistant", "OpenRouter and Ollama.")
        self.assertTrue(cm.is_followup("continue", CHAT))

    def test_compare_them_is_followup(self):
        cm.record_turn(CHAT, "user", "What providers do we have?")
        cm.record_turn(CHAT, "assistant", "Two main ones.")
        self.assertTrue(cm.is_followup("compare them", CHAT))

    def test_what_about_is_followup(self):
        cm.record_turn(CHAT, "user", "What AI providers are available?")
        cm.record_turn(CHAT, "assistant", "OpenRouter is primary.")
        self.assertTrue(cm.is_followup("what about Claude?", CHAT))

    def test_expand_is_followup(self):
        cm.record_turn(CHAT, "user", "What are the priorities?")
        cm.record_turn(CHAT, "assistant", "Three priorities.")
        self.assertTrue(cm.is_followup("expand", CHAT))

    def test_why_is_followup(self):
        cm.record_turn(CHAT, "user", "Focus on the launch.")
        cm.record_turn(CHAT, "assistant", "The launch is closest to revenue.")
        self.assertTrue(cm.is_followup("why?", CHAT))

    def test_fresh_operational_question_not_followup(self):
        cm.record_turn(CHAT, "user", "Previous question")
        cm.record_turn(CHAT, "assistant", "Previous answer")
        # "what should I focus on today" is a fresh operational question, not referential
        self.assertFalse(cm.is_followup("what should I focus on today", CHAT))


class TestGetLastAssistantReply(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_returns_last_assistant_reply(self):
        cm.record_turn(CHAT, "user", "q1")
        cm.record_turn(CHAT, "assistant", "answer1")
        cm.record_turn(CHAT, "user", "q2")
        cm.record_turn(CHAT, "assistant", "answer2")
        self.assertEqual(cm.get_last_assistant_reply(CHAT), "answer2")

    def test_empty_when_no_history(self):
        self.assertEqual(cm.get_last_assistant_reply(CHAT), "")

    def test_empty_when_only_user_turns(self):
        cm.record_turn(CHAT, "user", "just asking")
        self.assertEqual(cm.get_last_assistant_reply(CHAT), "")


class TestSessionSummary(unittest.TestCase):
    def setUp(self):
        _fresh()

    def test_summary_keys(self):
        cm.record_turn(CHAT, "user", "hello")
        cm.record_turn(CHAT, "assistant", "hi")
        summary = cm.session_summary(CHAT)
        self.assertIn("total_turns", summary)
        self.assertIn("user_turns", summary)
        self.assertIn("idle_seconds", summary)
        self.assertEqual(summary["total_turns"], 2)
        self.assertEqual(summary["user_turns"], 1)

    def test_empty_session_summary(self):
        summary = cm.session_summary("nobody")
        self.assertEqual(summary["total_turns"], 0)


class TestProviderContinuity(unittest.TestCase):
    """Simulate the AI-provider follow-up conversation flow."""

    def setUp(self):
        _fresh()

    def test_provider_conversation_history_builds(self):
        # Turn 1: initial question
        cm.record_turn(CHAT, "user", "What AI providers are available?")
        cm.record_turn(CHAT, "assistant",
                       "Nexus has OpenRouter (primary), local Ollama (qwen3:8b), Claude Code CLI, and OpenClaw.")
        # Turn 2: follow-up
        self.assertTrue(cm.is_followup("Which one should I use for coding?", CHAT))
        history = cm.get_history(CHAT)
        self.assertEqual(len(history), 2)
        # The history passes prior context so the LLM can answer "which one"
        roles = [h["role"] for h in history]
        self.assertEqual(roles, ["user", "assistant"])

    def test_low_cost_followup_continues(self):
        cm.record_turn(CHAT, "user", "What AI providers are available?")
        cm.record_turn(CHAT, "assistant", "OpenRouter primary, Ollama local, Claude Code, OpenClaw.")
        cm.record_turn(CHAT, "user", "Which one should I use for coding?")
        cm.record_turn(CHAT, "assistant", "Claude Code is best for coding tasks in Nexus context.")
        self.assertTrue(cm.is_followup("What about low-cost options?", CHAT))
        history = cm.get_history(CHAT)
        self.assertEqual(len(history), 4)


if __name__ == "__main__":
    result = unittest.main(verbosity=2, exit=False)
    passed = result.result.testsRun - len(result.result.failures) - len(result.result.errors)
    total = result.result.testsRun
    print(f"\n{'='*50}")
    print(f"Session memory tests: {passed}/{total} passed")
    sys.exit(0 if result.result.wasSuccessful() else 1)
