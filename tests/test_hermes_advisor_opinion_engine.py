"""Tests for the Hermes opinion engine. Run: python3 tests/test_hermes_advisor_opinion_engine.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_advisor_opinion_engine as OE  # noqa: E402


class TestOpinionEngine(unittest.TestCase):
    def test_nexus_opinion_uses_format(self):
        # (6.1) "What do you think about Nexus?" -> opinion format
        out = OE.render("What do you think about Nexus?")
        self.assertIn("My take:", out)
        self.assertIn("Why:", out)
        self.assertIn("1.", out)
        self.assertIn("Risk:", out)
        self.assertIn("Best next move:", out)

    def test_monetization_credit_funding_first(self):
        # (6.2) "How do we make money in 30 days?" -> Credit/Funding first
        op = OE.form_opinion("How do we make money in 30 days?")
        self.assertTrue(OE.is_monetization("How do we make money in 30 days?"))
        self.assertIn("Credit/Funding", op["my_take"])
        # priority order is intact and credit/funding is #1
        self.assertIn("Credit/Funding", OE.MONETIZATION_PRIORITY[0])
        self.assertTrue(any("funding" in w.lower() for w in op["why"]))

    def test_no_fabricated_live_data_hands_off(self):
        # live-data questions must hand off, not invent numbers
        op = OE.form_opinion("How much did we make today?")
        self.assertTrue(OE.needs_live_data("How much did we make today?"))
        self.assertIsNotNone(op["command_for_thechosenone"])
        self.assertIn("Safety:", op["command_for_thechosenone"])

    def test_engine_only_advises_never_executes(self):
        # (6.5) opinion engine exposes no execute/send/run side-effect API
        for forbidden in ("execute", "send", "publish", "trade", "deploy", "approve"):
            self.assertFalse(hasattr(OE, forbidden),
                             f"opinion engine must not expose {forbidden}()")
        # monetization opinion delegates via a drafted command, not an action
        op = OE.form_opinion("turn the credit pack into an offer to make money")
        self.assertIn("Do not publish.", op["command_for_thechosenone"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
