"""
test_review_first_specific_recommendation.py
=============================================
Verify that 'what should I review first' returns a specific asset name,
NOT routing instructions like "Route to content_intelligence_scout."
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROUTING_PHRASES = [
    "route to content_intelligence_scout",
    "route to affiliate_monetization_scout",
    "route to product_scout",
    "build draft for ray review",
]


class TestReviewFirstSpecificRecommendation(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_review_first_returns_result(self):
        result = self._call("what should I review first")
        self.assertIsNotNone(result)
        self.assertIsInstance(result.text, str)
        self.assertGreater(len(result.text.strip()), 20)

    def test_review_first_not_routing_instructions(self):
        result = self._call("what should I review first")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for phrase in _ROUTING_PHRASES:
            self.assertNotIn(phrase.lower(), text,
                f"'what should I review first' must not contain routing phrase '{phrase}'")

    def test_review_first_names_specific_asset(self):
        result = self._call("what should I review first")
        self.assertIsNotNone(result)
        text = result.text.lower()
        # Must reference a specific thing to review
        has_specific = any(kw in text for kw in [
            "review this", "review:", "checklist", "newsletter", "guide", "draft",
            "template", "credit", "youtube", "content", "affiliate", "article",
            "score", "report", "product",
        ])
        self.assertTrue(has_specific,
            f"'what should I review first' must name a specific asset. Got:\n{result.text[:300]}")

    def test_review_first_has_approval_boundary(self):
        result = self._call("what should I review first")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_boundary = any(kw in text for kw in [
            "approval", "approve", "approve before", "needs your",
            "your call", "daily research review",
        ])
        self.assertTrue(has_boundary,
            "Review-first response must include approval boundary or next step")

    def test_alternate_phrases_route_to_review_first(self):
        for phrase in [
            "what is the next thing i should review",
            "what should i look at first",
            "what needs my review",
        ]:
            result = self._call(phrase)
            self.assertIsNotNone(result, f"'{phrase}' returned None")
            if result:
                text = result.text.lower()
                for bad in _ROUTING_PHRASES:
                    self.assertNotIn(bad.lower(), text,
                        f"'{phrase}' response must not contain routing phrase '{bad}'")

    def test_response_not_only_routing(self):
        """Response must contain a noun referencing what to actually review."""
        result = self._call("what should I review first")
        self.assertIsNotNone(result)
        text = result.text
        # More than just routing: must be longer than a typical routing label
        self.assertGreater(len(text.strip()), 50,
            "Review-first response must be substantive, not just a routing label")


if __name__ == "__main__":
    unittest.main()
