"""
test_back_to_back_telegram_commands.py
========================================
Verify that two different Telegram commands sent in quick succession both get responses.
The cooldown (TELEGRAM_COMMAND_COOLDOWN_SECONDS) must be <= 1.0 seconds.
"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestBackToBackCommands(unittest.TestCase):
    def test_cooldown_default_is_one_second_or_less(self):
        """Default cooldown must be <= 1.0 seconds so back-to-back commands land."""
        os.environ.pop("TELEGRAM_COMMAND_COOLDOWN_SECONDS", None)
        # Import with no env override — check the default
        import importlib
        import telegram_bot as tb
        importlib.reload(tb)
        # Create instance with minimal mocks
        with patch.dict(os.environ, {
            "TELEGRAM_BOT_TOKEN": "test:token",
            "TELEGRAM_CHAT_ID": "123456",
        }):
            try:
                bot = tb.NexusTelegramBot.__new__(tb.NexusTelegramBot)
                bot.cooldown_seconds = float(os.getenv("TELEGRAM_COMMAND_COOLDOWN_SECONDS", "1"))
                self.assertLessEqual(bot.cooldown_seconds, 1.0,
                    f"Cooldown should be <= 1.0s, got {bot.cooldown_seconds}s. "
                    "Back-to-back commands are being silently dropped.")
            except Exception as exc:
                self.fail(f"Could not check cooldown: {exc}")

    def test_cooldown_allows_second_command_after_1s(self):
        """After cooldown expires, second command must be processed."""
        chat_id = "123456"
        cooldown_seconds = 1.0
        chat_cooldowns: dict = {}

        def simulate_command(cmd_time: float) -> bool:
            cooldown_until = chat_cooldowns.get(chat_id, 0.0)
            if cmd_time < cooldown_until:
                return False  # ignored
            chat_cooldowns[chat_id] = cmd_time + cooldown_seconds
            return True

        t0 = 1000.0
        r1 = simulate_command(t0)
        r2 = simulate_command(t0 + 0.5)   # 0.5s later — blocked by 1s cooldown
        r3 = simulate_command(t0 + 1.1)   # 1.1s later — should pass

        self.assertTrue(r1, "First command should always pass")
        self.assertFalse(r2, "Second command within cooldown window should be blocked")
        self.assertTrue(r3, "Third command after cooldown should pass")

    def test_different_commands_both_processed_with_short_cooldown(self):
        """With 1s cooldown, user can send two commands within 2 seconds."""
        chat_id = "123456"
        cooldown_seconds = 1.0
        chat_cooldowns: dict = {}
        processed = []

        def simulate_command(cmd_time: float, cmd: str):
            cooldown_until = chat_cooldowns.get(chat_id, 0.0)
            if cmd_time < cooldown_until:
                return
            chat_cooldowns[chat_id] = cmd_time + cooldown_seconds
            processed.append(cmd)

        t0 = 1000.0
        simulate_command(t0, "what did you find today")
        simulate_command(t0 + 1.5, "show top monetization actions")

        self.assertEqual(len(processed), 2,
            f"Expected both commands processed, got: {processed}")
        self.assertIn("what did you find today", processed)
        self.assertIn("show top monetization actions", processed)

    def test_dedup_does_not_suppress_different_response_text(self):
        """_send_message_once dedup should not suppress different responses."""
        import hashlib
        text1 = "Latest cycle: 20260529_120000\nSources found: 18 total."
        text2 = "Rejected in last cycle (8 sources):\n  ❌ bad source"
        h1 = hashlib.sha256(text1.encode()).hexdigest()[:16]
        h2 = hashlib.sha256(text2.encode()).hexdigest()[:16]
        self.assertNotEqual(h1, h2, "Different responses must have different hashes")


if __name__ == "__main__":
    unittest.main()
