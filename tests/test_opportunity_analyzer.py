"""Tests for opportunity_analyzer — input detection, scoring, classification."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import opportunity_analyzer as OA


class TestOpportunityAnalyzer(unittest.TestCase):

    def test_is_opportunity_input_detects_analysis_request(self):
        self.assertTrue(OA.is_opportunity_input("analyze this opportunity"))
        self.assertTrue(OA.is_opportunity_input("score this business idea"))
        self.assertTrue(OA.is_opportunity_input("could this make money?"))

    def test_is_opportunity_input_rejects_ordinary_chat(self):
        self.assertFalse(OA.is_opportunity_input("what's the weather like?"))
        self.assertFalse(OA.is_opportunity_input("run web research on credit repair"))

    def test_score_opportunity_returns_dict_with_scores(self):
        text = "A subscription-based credit monitoring service for small business owners."
        result = OA.score_opportunity(text)
        self.assertIsInstance(result, dict)
        self.assertIn("score", result)
        self.assertIn("category", result)
        self.assertIn("dimension_scores", result)
        dims = result["dimension_scores"]
        for key in ("startup_cost", "time_to_revenue", "automation",
                     "scalability", "recurring_revenue", "nexus_synergy", "operational_ease"):
            self.assertIn(key, dims)

    def test_score_returns_reasonable_range(self):
        text = "High-ticket coaching with recurring subscription model, easy to automate."
        result = OA.score_opportunity(text)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_score_low_for_vague_idea(self):
        vague = "full-time manual consulting work in-person requiring expensive hardware setup"
        result = OA.score_opportunity(vague)
        self.assertLess(result["score"], 50)

    def test_score_high_for_concrete_plan(self):
        concrete = (
            "Monthly subscription box for credit repair resources, $47/mo, "
            "automated fulfillment, scalable through affiliate partners, "
            "recurring revenue, easy to run from laptop."
        )
        result = OA.score_opportunity(concrete)
        self.assertGreater(result["score"], 30)

    def test_classify_low_score_as_avoid(self):
        result = OA.score_opportunity(
            "full-time manual in-person work requiring expensive hardware"
        )
        self.assertEqual(result["category"], "Avoid")

    def test_classify_high_score_as_quick_win(self):
        result = OA.score_opportunity(
            "a recurring high-ticket subscription service that is fully automated "
            "with scalable systems and recurring revenue"
        )
        self.assertIn(result["category"], ("Quick Win", "High Leverage", "Scalable Asset"))

    def test_no_paid_apis_at_module_level(self):
        import inspect
        source = inspect.getsource(OA)
        self.assertNotIn("openai", source)

    def test_generate_report_includes_sections(self):
        text = "A coaching program for credit repair professionals at $2k/month."
        report = OA.generate_opportunity_report(text)
        self.assertIn("NEXUS OPPORTUNITY REPORT", report)
        self.assertIn("RECOMMENDATION", report)

    def test_no_hardcoded_secrets(self):
        """Env var names are OK; secret values should not be hardcoded."""
        import inspect
        source = inspect.getsource(OA)
        self.assertNotIn("sk-", source)
        self.assertNotIn("secret_key", source)

    def test_detect_type_in_report(self):
        report = OA.generate_opportunity_report("youtube.com/watch?v=abc123 about AI automation")
        self.assertIn("TYPE", report)

    def test_score_is_deterministic(self):
        text = "A funding readiness review service for $97."
        r1 = OA.score_opportunity(text)
        r2 = OA.score_opportunity(text)
        self.assertEqual(r1["score"], r2["score"])
        self.assertEqual(r1["category"], r2["category"])


if __name__ == "__main__":
    unittest.main()
