"""Tests for affiliate_engine — opportunity lookups and recommendations."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import affiliate_engine as AE


class TestAffiliateEngine(unittest.TestCase):

    def test_get_top_opportunities_returns_list(self):
        opps = AE.get_top_opportunities(n=3)
        self.assertIsInstance(opps, list)
        self.assertLessEqual(len(opps), 3)

    def test_get_top_opportunities_with_category(self):
        opps = AE.get_top_opportunities(n=5, category="funding")
        self.assertIsInstance(opps, list)

    def test_get_top_opportunities_respects_limit(self):
        opps = AE.get_top_opportunities(n=1)
        self.assertLessEqual(len(opps), 1)

    def test_get_top_opportunities_no_category(self):
        opps = AE.get_top_opportunities(n=10)
        self.assertIsInstance(opps, list)

    def test_get_immediately_applicable_returns_list(self):
        applicable = AE.get_immediately_applicable()
        self.assertIsInstance(applicable, list)

    def test_affiliate_registry_has_entries(self):
        self.assertGreater(len(AE.AFFILIATE_REGISTRY), 0)

    def test_registry_entries_have_required_fields(self):
        for entry in AE.AFFILIATE_REGISTRY:
            with self.subTest(name=entry.get("name", "unknown")):
                self.assertIn("name", entry)
                self.assertIn("category", entry)
                self.assertIn("roi_score", entry)

    def test_roi_score_is_in_expected_range(self):
        for entry in AE.AFFILIATE_REGISTRY:
            score = entry["roi_score"]
            self.assertIsInstance(score, (int, float))
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_generate_recommendations_returns_list(self):
        recs = AE.generate_affiliate_recommendations()
        self.assertIsInstance(recs, list)

    def test_no_secrets_in_registry(self):
        import json
        dump = json.dumps(AE.AFFILIATE_REGISTRY)
        self.assertNotIn("token=", dump)
        self.assertNotIn("api_key", dump)

    def test_no_paid_apis_at_module_level(self):
        import inspect
        source = inspect.getsource(AE)
        module_imports = [l for l in source.split("\n") if l.strip().startswith(("import ", "from ")) and not l.strip().startswith(("#", '"', "'"))]
        module_imports = [l for l in module_imports if l[0] != " "]
        for imp in module_imports:
            if "urllib" in imp:
                self.fail(f"Module-level import of network lib: {imp}")


if __name__ == "__main__":
    unittest.main()
