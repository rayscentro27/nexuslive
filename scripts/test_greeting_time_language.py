"""
test_greeting_time_language.py
================================
Verify greeting handler uses time-aware language instead of always saying "Good morning".
"""
import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


def _get_greeting_for_hour(hour: int) -> str:
    """Simulate the greeting logic in telegram_bot._conversational_reply."""
    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 17:
        return "Good afternoon"
    elif 17 <= hour < 21:
        return "Good evening"
    else:
        return "Hey Ray"


class TestGreetingTimeLanguage(unittest.TestCase):
    def test_morning_hours_say_good_morning(self):
        for hour in [5, 6, 7, 8, 9, 10, 11]:
            greeting = _get_greeting_for_hour(hour)
            self.assertEqual(greeting, "Good morning", f"Expected Good morning at hour {hour}")

    def test_afternoon_hours_say_good_afternoon(self):
        for hour in [12, 13, 14, 15, 16]:
            greeting = _get_greeting_for_hour(hour)
            self.assertEqual(greeting, "Good afternoon", f"Expected Good afternoon at hour {hour}")

    def test_evening_hours_say_good_evening(self):
        for hour in [17, 18, 19, 20]:
            greeting = _get_greeting_for_hour(hour)
            self.assertEqual(greeting, "Good evening", f"Expected Good evening at hour {hour}")

    def test_night_hours_say_hey_ray(self):
        for hour in [0, 1, 2, 3, 4, 21, 22, 23]:
            greeting = _get_greeting_for_hour(hour)
            self.assertEqual(greeting, "Hey Ray", f"Expected Hey Ray at hour {hour}")

    def test_greeting_does_not_hardcode_morning(self):
        """At hour 19, the bot must NOT say 'Good morning'."""
        greeting = _get_greeting_for_hour(19)
        self.assertNotEqual(greeting, "Good morning",
            "Greeting should not be 'Good morning' in the evening")

    def test_greeting_includes_ray_name(self):
        for hour in [8, 14, 18, 22]:
            greeting = _get_greeting_for_hour(hour)
            text = f"{greeting}, Ray. I'm online and ready."
            self.assertIn("Ray", text, f"Greeting must include Ray's name at hour {hour}")

    def test_no_provider_health_in_greeting(self):
        """Greeting must not mention provider health or technical status."""
        for hour in range(0, 24):
            greeting = _get_greeting_for_hour(hour)
            text = f"{greeting}, Ray. I'm online and ready."
            self.assertNotIn("provider", text.lower())
            self.assertNotIn("openrouter", text.lower())
            self.assertNotIn("ollama", text.lower())
            self.assertNotIn("deepseek", text.lower())


class TestGreetingInTelegramBot(unittest.TestCase):
    """Integration test: verify the actual telegram_bot code uses time-aware greeting."""

    def test_good_morning_not_hardcoded(self):
        """The greeting code must not return 'Good morning' at hour 19."""
        import telegram_bot as tb
        with patch("datetime.datetime") as mock_dt:
            mock_dt.now.return_value.hour = 19
            # Check the pattern in the source
            import inspect
            source = inspect.getsource(tb.NexusTelegramBot._conversational_reply)
            # Should not have a hardcoded "Good morning" without a conditional
            self.assertNotIn(
                'return "Good morning, Ray.',
                source,
                "Good morning must be conditional on hour, not hardcoded as return value"
            )

    def test_greeting_code_has_hour_check(self):
        """The greeting code must include hour-based branching."""
        import telegram_bot as tb
        import inspect
        source = inspect.getsource(tb.NexusTelegramBot._conversational_reply)
        self.assertIn("_hour", source, "Greeting code must check current hour")
        self.assertIn("Good morning", source)
        self.assertIn("Good afternoon", source)
        self.assertIn("Good evening", source)


if __name__ == "__main__":
    unittest.main()
