"""Monetization task price-range preservation (no truncation at en-dash).
Run: python3 tests/test_monetization_price_preservation.py

Root cause covered: telegram_bot._normalize_telegram_command used to strip an
em/en dash and everything after it, truncating "$97–$297" -> "$97".
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Self-contained branch: the normalizer is ported as a standalone module
# (full telegram_bot.py carries a large platform tree). Behaviour is identical to
# telegram_bot._normalize_telegram_command on the feature branch.
from lib import telegram_command_normalizer as TB          # noqa: E402
from lib import thechosenone_command_delegation as D       # noqa: E402


def _goal(resp: str) -> str:
    for ln in resp.splitlines():
        if ln.startswith("Goal:"):
            return ln
    return ""


def _live(text: str) -> str:
    """Simulate the live inbound path: normalize then delegate."""
    return D.maybe_handle(TB._normalize_telegram_command(text))


class TestPricePreservation(unittest.TestCase):
    # 1) en-dash price range preserved end-to-end
    def test_en_dash_price_preserved(self):
        resp = _live("create monetization task from package proof_credit: "
                     "Turn this into a $97–$297 offer.")
        self.assertIn("$97–$297", _goal(resp))
        self.assertIn("$297", resp)
        self.assertIn("Price band: $97–$297", resp)

    # 2) hyphen price range preserved (not touched by dash-stripper)
    def test_hyphen_price_preserved(self):
        resp = _live("create monetization task from package proof_credit: "
                     "Turn this into a $97-$297 offer.")
        self.assertIn("$97-$297", _goal(resp))
        self.assertIn("$297", resp)

    # 2b) spaced en-dash price range also preserved (bonus robustness)
    def test_spaced_en_dash_preserved(self):
        norm = TB._normalize_telegram_command(
            "create monetization task from package proof_credit: "
            "Turn this into a $97 – $297 offer.")
        self.assertIn("$297", norm)

    # 3) default (no colon) goal names the $97–$297 readiness review
    def test_default_goal_includes_price(self):
        resp = _live("turn package proof_credit into offer")
        self.assertIn("$97–$297", _goal(resp))
        self.assertIn("manual Credit/Funding Readiness Review", _goal(resp))

    # 4) no secrets leak via the drafted prompt / receipt path
    def test_no_secrets_in_draft(self):
        resp = _live("create monetization task from package proof_credit: "
                     "Turn this into a $97–$297 offer token=SECRETZZ9 chat_id 99887766")
        self.assertNotIn("SECRETZZ9", resp)
        self.assertNotIn("99887766", resp)

    # the dash-stripper still cleans REAL menu suffixes (no regression)
    def test_menu_suffix_still_stripped(self):
        self.assertEqual(TB._normalize_telegram_command("status — shows system status"), "status")
        self.assertEqual(TB._normalize_telegram_command("approve package – description"), "approve package")


if __name__ == "__main__":
    unittest.main(verbosity=2)
