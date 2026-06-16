"""Tests for hermes_monetization_today — phrase detection and content asset scoring."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_monetization_today as MT


class TestMonetizationToday(unittest.TestCase):

    def test_is_monetization_audit_phrase_detects_audit(self):
        self.assertTrue(MT.is_monetization_audit_phrase("run monetization audit"))
        self.assertTrue(MT.is_monetization_audit_phrase("monetization audit please"))
        self.assertTrue(MT.is_monetization_audit_phrase("run a monetization audit now"))

    def test_is_monetization_audit_phrase_rejects_unrelated(self):
        self.assertFalse(MT.is_monetization_audit_phrase("what is monetization?"))
        self.assertFalse(MT.is_monetization_audit_phrase("research affiliate offers"))

    def test_is_monetization_today_phrase_detects_today(self):
        self.assertTrue(MT.is_monetization_today_phrase("how do we make money today"))
        self.assertTrue(MT.is_monetization_today_phrase("what can make money today"))
        self.assertTrue(MT.is_monetization_today_phrase("monetization plan"))

    def test_is_monetization_today_phrase_rejects_unrelated(self):
        self.assertFalse(MT.is_monetization_today_phrase("run web research on credit repair"))
        self.assertFalse(MT.is_monetization_today_phrase("delegate research topic"))

    def test_score_content_asset_for_monetization_returns_int(self):
        score = MT.score_content_asset_for_monetization(Path("/tmp/test_content.md"))
        self.assertIsInstance(score, int)

    def test_score_content_asset_for_monetization_default(self):
        score = MT.score_content_asset_for_monetization(Path("/tmp/test_affiliate_offer.md"))
        self.assertIsInstance(score, int)

    def test_monetization_plan_type_is_typed_dict(self):
        plan = MT.build_today_monetization_plan()
        self.assertIsInstance(plan, dict)

    def test_format_monetization_response_returns_string(self):
        plan = MT.build_today_monetization_plan()
        formatted = MT.format_today_monetization_response(plan)
        self.assertIsInstance(formatted, str)

    def test_no_secrets_in_exported_functions(self):
        import inspect
        source = inspect.getsource(MT)
        self.assertNotIn("token=", source)
        self.assertNotIn("api_key", source)

    def test_no_paid_apis(self):
        import inspect
        source = inspect.getsource(MT)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("openai", source)

    def test_extract_type_from_stem(self):
        result = MT._extract_type("20260601_lead_magnet")
        self.assertEqual(result, "lead_magnet")

    def test_extract_type_unknown(self):
        result = MT._extract_type("random_file")
        self.assertEqual(result, "other")


if __name__ == "__main__":
    unittest.main()
