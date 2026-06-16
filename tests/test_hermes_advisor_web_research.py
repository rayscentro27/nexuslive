"""Tests for Hermes web research (Mode A live / Mode B handoff).
Run: python3 tests/test_hermes_advisor_web_research.py"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_advisor_web_research as WR  # noqa: E402


class TestWebResearch(unittest.TestCase):
    def test_mode_b_handoff_when_web_disabled(self):
        os.environ["HERMES_ADVISOR_WEB_ENABLED"] = "false"
        out = WR.respond("best affiliate offers for the funding checklist")
        self.assertIn("can't browse directly", out)
        self.assertIn("run web research:", out)
        self.assertIn("do not use paid apis", out.lower())

    def test_draft_research_task_is_safe_and_scrubbed(self):
        # (6.3) drafts a TheChoseone research task for affiliate offers
        draft = WR.draft_research_task("best affiliate offers for funding checklist")
        self.assertTrue(draft.startswith("run web research:"))
        self.assertIn("source links", draft)
        self.assertIn("risk", draft)

    def test_query_sanitization_strips_secrets(self):
        q = WR.sanitize_query("find token=ABC123 and chat_id 998877 affiliate offers")
        self.assertNotIn("ABC123", q)
        self.assertIn("[redacted]", q)

    def test_no_fabricated_results_in_handoff(self):
        res = WR.research("anything")
        self.assertEqual(res["mode"], "handoff")
        self.assertEqual(res["results"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
