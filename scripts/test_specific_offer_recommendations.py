"""
test_specific_offer_recommendations.py
========================================
Verify _format_opportunity_specific and _format_opportunity_detail
produce specific product/offer recommendations, not routing labels.

Bad: "Route to content_intelligence_scout. Build draft for Ray review."
Good: "Build a Credit/Funding Readiness Checklist lead magnet..."
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# These phrases should NOT appear as the primary numbered recommendation line.
# They are acceptable in "Next:", "Scout:", or tag positions, but not as the offer itself.
ROUTING_PHRASES_AS_LEAD = [
    "route to content_intelligence_scout",
    "build draft for ray review",
    "send to scout",
]


class TestRoutingInstructionsSkipped(unittest.TestCase):
    def _fmt(self, op: dict) -> str:
        from lib.hermes_internal_first import _format_opportunity_specific
        return _format_opportunity_specific(op)

    def test_routing_recommended_action_not_used_as_specific(self):
        op = {
            "title": "Monetization opportunity: Paid template/tool product",
            "status": "product_candidate",
            "monetization_score": 56,
            "recommended_action": "Route to content_intelligence_scout. Build draft for Ray review.",
        }
        result = self._fmt(op)
        for phrase in ROUTING_PHRASES_AS_LEAD:
            self.assertNotIn(phrase, result.lower(),
                f"Routing instruction '{phrase}' must not appear as main recommendation: {result}")

    def test_routing_action_replaced_with_category_expansion(self):
        op = {
            "title": "Monetization opportunity: Paid template/tool product",
            "status": "product_candidate",
            "monetization_score": 56,
            "recommended_action": "Route to content_intelligence_scout. Build draft for Ray review.",
        }
        result = self._fmt(op)
        # Should expand via _CATEGORY_ACTIONS to something about credit/funding
        self.assertTrue(
            any(w in result.lower() for w in ["checklist", "build", "create", "credit", "funding", "lead magnet"]),
            f"Should derive a product recommendation, got: {result}"
        )

    def test_specific_recommended_action_preserved(self):
        op = {
            "title": "Monetization opportunity: Affiliate",
            "status": "affiliate_candidate",
            "monetization_score": 48,
            "recommended_action": "Sign up for Credit Karma affiliate program and integrate into funnel",
        }
        result = self._fmt(op)
        self.assertIn("Credit Karma", result,
            "Specific recommended_action (non-routing) must be preserved")

    def test_newsletter_expands_to_specific_offer(self):
        op = {
            "title": "Newsletter premium tier",
            "status": "content_candidate",
            "monetization_score": 52,
        }
        result = self._fmt(op)
        self.assertFalse(
            result.strip().lower() == "newsletter premium tier",
            "Must expand to specific offer description, not just repeat title"
        )
        self.assertGreater(len(result), 25)

    def test_funding_title_expands(self):
        op = {
            "title": "Funding readiness checklist",
            "status": "product_candidate",
            "monetization_score": 60,
        }
        result = self._fmt(op)
        self.assertGreater(len(result), 20)
        self.assertFalse(
            result.lower().startswith("funding readiness checklist"),
            "Should expand the title to a specific action"
        )

    def test_affiliate_program_research_expands(self):
        op = {
            "title": "Affiliate program research",
            "status": "affiliate_candidate",
            "monetization_score": 46,
        }
        result = self._fmt(op)
        self.assertFalse(
            result.strip().lower() == "affiliate program research",
            "Should expand to specific offer, not just repeat title"
        )


class TestDetailBlockQuality(unittest.TestCase):
    def _detail(self, op: dict, i: int = 1) -> list:
        from lib.hermes_internal_first import _format_opportunity_detail
        return _format_opportunity_detail(op, i)

    def _all_text(self, lines: list) -> str:
        return " ".join(lines).lower()

    def test_detail_first_line_not_routing_instruction(self):
        op = {
            "title": "Monetization opportunity: Paid template/tool product",
            "status": "product_candidate",
            "monetization_score": 56,
            "recommended_action": "Route to content_intelligence_scout. Build draft for Ray review.",
        }
        lines = self._detail(op)
        first_line = lines[0].lower()
        for phrase in ROUTING_PHRASES_AS_LEAD:
            self.assertNotIn(phrase, first_line,
                f"First line must not be routing instruction: {lines[0]}")

    def test_detail_has_why_line(self):
        op = {"title": "Credit repair content", "status": "content_candidate",
              "monetization_score": 60}
        lines = self._detail(op)
        self.assertTrue(any("why:" in l.lower() for l in lines),
            "Detail must contain 'Why:' line")

    def test_detail_has_next_line(self):
        op = {"title": "Credit repair content", "status": "content_candidate",
              "monetization_score": 60}
        lines = self._detail(op)
        self.assertTrue(any("next:" in l.lower() for l in lines),
            "Detail must contain 'Next:' line")

    def test_detail_approval_boundary_present(self):
        op = {"title": "Publish affiliate links", "status": "affiliate_candidate",
              "monetization_score": 55, "requires_ray_approval": True}
        lines = self._detail(op)
        self.assertTrue(any("approval" in l.lower() for l in lines),
            "Detail must include approval boundary")

    def test_detail_approval_boundary_always_present(self):
        """Even for autonomous actions, must note when approval IS required before publishing."""
        op = {"title": "Internal draft", "status": "content_candidate",
              "monetization_score": 60, "requires_ray_approval": False}
        lines = self._detail(op)
        all_text = self._all_text(lines)
        self.assertIn("approval", all_text,
            "Must always include approval boundary note")

    def test_detail_product_candidate_why_mentions_audience(self):
        op = {"title": "Paid template product", "status": "product_candidate",
              "monetization_score": 70}
        lines = self._detail(op)
        all_text = self._all_text(lines)
        self.assertTrue(
            "audience" in all_text or "goal" in all_text or "revenue" in all_text,
            "Why line should reference audience or goal"
        )

    def test_detail_affiliate_why_mentions_free(self):
        op = {"title": "Affiliate program research", "status": "affiliate_candidate",
              "monetization_score": 46}
        lines = self._detail(op)
        all_text = self._all_text(lines)
        self.assertTrue(
            "free" in all_text or "cost" in all_text or "no approval" in all_text,
            "Affiliate Why should note it is free to set up"
        )


class TestMonetizationActionsLiveQuery(unittest.TestCase):
    """Integration: 'what can make money this week' must return specific offers."""

    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_response_is_not_routing_labels(self):
        result = self._call("what can make money this week")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for phrase in ROUTING_PHRASES_AS_LEAD:
            self.assertNotIn(phrase, text,
                f"Numbered items must not start with routing instruction '{phrase}'")

    def test_response_has_why_and_next(self):
        result = self._call("show top monetization actions")
        self.assertIsNotNone(result)
        text = result.text
        self.assertIn("Why:", text, "Response must include 'Why:' for each opportunity")
        self.assertIn("Next:", text, "Response must include 'Next:' for each opportunity")

    def test_response_has_approval_boundary(self):
        result = self._call("what can make money this week")
        self.assertIsNotNone(result)
        self.assertIn("Approval:", result.text,
            "Response must include approval boundary for each item")


if __name__ == "__main__":
    unittest.main()
