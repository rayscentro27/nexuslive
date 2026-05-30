"""
test_specific_monetization_recommendations.py
===============================================
Verify top monetization opportunities are specific and actionable,
not just generic category labels.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest

GENERIC_LABELS = [
    "monetization opportunity:",
    "content opportunity:",
    "affiliate opportunity:",
    "product opportunity:",
]


class TestFormatOpportunitySpecific(unittest.TestCase):
    def _fmt(self, op: dict) -> str:
        from lib.hermes_internal_first import _format_opportunity_specific
        return _format_opportunity_specific(op)

    def test_generic_title_derives_specific_action(self):
        op = {"title": "Monetization opportunity: Paid template/tool product",
              "status": "product_candidate", "monetization_score": 56}
        result = self._fmt(op)
        # Must not just repeat the generic label
        self.assertFalse(
            result.lower().startswith("monetization opportunity:"),
            f"Should derive specific action, got: {result}"
        )

    def test_newsletter_title_becomes_specific(self):
        op = {"title": "Newsletter premium tier",
              "status": "content_candidate", "monetization_score": 52}
        result = self._fmt(op)
        self.assertGreater(len(result), 20)
        self.assertNotIn("Newsletter premium tier", result.split("—")[0].strip(),
            "Should expand to specific action, not just repeat the title")

    def test_specific_recommended_action_used_when_present(self):
        op = {"title": "Monetization opportunity: Affiliate",
              "status": "affiliate_candidate", "monetization_score": 48,
              "recommended_action": "Sign up for Credit Karma affiliate program and integrate into funnel"}
        result = self._fmt(op)
        self.assertIn("Credit Karma", result,
            "Should use specific recommended_action when present")

    def test_approval_tag_present_when_required(self):
        op = {"title": "Paid SaaS product", "status": "product_candidate",
              "monetization_score": 70, "requires_ray_approval": True}
        result = self._fmt(op)
        self.assertIn("approval", result.lower(),
            "Must indicate when approval is required")

    def test_no_approval_tag_when_not_required(self):
        op = {"title": "Content draft", "status": "content_candidate",
              "monetization_score": 60, "requires_ray_approval": False}
        result = self._fmt(op)
        # For internal draft, no approval required
        self.assertNotIn("[needs approval]", result)


class TestFormatOpportunityDetail(unittest.TestCase):
    def _detail(self, op: dict, i: int = 1) -> list:
        from lib.hermes_internal_first import _format_opportunity_detail
        return _format_opportunity_detail(op, i)

    def test_detail_has_specific_action_on_first_line(self):
        op = {"title": "Monetization opportunity: Paid template/tool product",
              "status": "product_candidate", "monetization_score": 56,
              "why_selected": "Fits credit audience", "recommended_action": "Build checklist"}
        lines = self._detail(op)
        self.assertGreater(len(lines), 1)
        # First line should be the specific action
        self.assertFalse(
            lines[0].lower().startswith("1. monetization opportunity:"),
            f"First line too generic: {lines[0]}"
        )

    def test_detail_has_next_step(self):
        op = {"title": "Credit repair content", "status": "content_candidate",
              "monetization_score": 60}
        lines = self._detail(op)
        all_text = " ".join(lines).lower()
        self.assertIn("next:", all_text, "Must have 'Next:' step")

    def test_detail_has_approval_boundary(self):
        op = {"title": "Publish affiliate links", "status": "affiliate_candidate",
              "monetization_score": 55, "requires_ray_approval": True}
        lines = self._detail(op)
        all_text = " ".join(lines).lower()
        self.assertIn("approval", all_text, "Must mention approval boundary")

    def test_detail_has_approval_for_autonomous_too(self):
        op = {"title": "Internal draft", "status": "content_candidate",
              "monetization_score": 60, "requires_ray_approval": False}
        lines = self._detail(op)
        all_text = " ".join(lines).lower()
        self.assertIn("approval", all_text, "Must always include approval boundary note")


class TestMonetizationActionsResponse(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.review_dir = self.tmpdir / "docs" / "reports" / "review"
        self.decision_dir = self.tmpdir / "docs" / "reports" / "monetization"
        self.intake_dir = self.tmpdir / "docs" / "reports" / "intake"
        for d in [self.review_dir, self.decision_dir, self.intake_dir]:
            d.mkdir(parents=True)
        ts = "20260529_120000"
        (self.review_dir / f"daily_research_review_{ts}.json").write_text(json.dumps({
            "total_sources": 18,
            "actionable_count": 10,
            "rejected_count": 8,
            "top_opportunities": [
                {"title": "Monetization opportunity: Paid template/tool product",
                 "status": "product_candidate", "monetization_score": 56,
                 "why_selected": "Fits credit audience"},
                {"title": "Newsletter premium tier",
                 "status": "content_candidate", "monetization_score": 52},
                {"title": "Affiliate program research",
                 "status": "affiliate_candidate", "monetization_score": 46},
            ],
        }))

    def _patch_and_call(self, text: str):
        import lib.hermes_daily_cycle_state as m
        from lib.hermes_internal_first import try_internal_first
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            return try_internal_first(text)

    def test_top_opportunities_no_only_generic_labels(self):
        result = self._patch_and_call("what can make money this week")
        self.assertIsNotNone(result)
        text = result.text
        # Count how many lines are ONLY generic labels
        generic_only_count = sum(
            1 for line in text.splitlines()
            if any(line.strip().startswith(f"{i}. " + label.title()) for i in range(1, 6)
                   for label in ["Monetization opportunity", "Content opportunity", "Product opportunity"])
        )
        self.assertEqual(generic_only_count, 0,
            f"Response has generic-label-only items: {text[:400]}")

    def test_each_opportunity_has_next_action(self):
        result = self._patch_and_call("show top monetization actions")
        self.assertIsNotNone(result)
        text = result.text
        self.assertIn("Next:", text, "Each opportunity must include 'Next:' action")

    def test_each_opportunity_has_approval_boundary(self):
        result = self._patch_and_call("what can make money this week")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertIn("approval", text, "Must include approval boundary for each opportunity")

    def test_response_not_just_category_list(self):
        result = self._patch_and_call("what can make money this week")
        self.assertIsNotNone(result)
        text = result.text
        # Should have multiple lines per opportunity (not just one-liner labels)
        lines = [l for l in text.splitlines() if l.strip()]
        self.assertGreater(len(lines), 4, "Response should have detail lines, not just labels")


if __name__ == "__main__":
    unittest.main()
