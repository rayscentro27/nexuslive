"""
test_daily_research_review_command_response.py
================================================
'show daily research review' must ALWAYS return a non-empty response.
Tests cover routing, format, and no-data fallback.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest


REVIEW_TRIGGERS = [
    "show daily research review",
    "hermes, show daily research review",
    "show daily review",
    "daily research review",
    "show research review",
    "show latest review",
    "Hermes, show daily research review.",
]


class TestDailyResearchReviewRouting(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_all_trigger_phrases_return_response(self):
        for phrase in REVIEW_TRIGGERS:
            with self.subTest(phrase=phrase):
                result = self._call(phrase)
                self.assertIsNotNone(result, f"'{phrase}' returned None")
                self.assertTrue(len(result.text) > 20, f"'{phrase}' returned too short: {result.text!r}")

    def test_routes_to_daily_review_topic(self):
        result = self._call("show daily research review")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "daily_review")

    def test_hermes_prefix_routes_correctly(self):
        result = self._call("Hermes, show daily research review.")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "daily_review")

    def test_never_returns_empty_text(self):
        for phrase in REVIEW_TRIGGERS:
            with self.subTest(phrase=phrase):
                result = self._call(phrase)
                self.assertIsNotNone(result)
                self.assertGreater(len(result.text.strip()), 0, f"'{phrase}' returned empty text")

    def test_no_data_returns_helpful_fallback(self):
        """When no review files exist, must return actionable fallback not empty."""
        import lib.hermes_daily_cycle_state as m
        tmpdir = Path(tempfile.mkdtemp())
        empty_review = tmpdir / "review"
        empty_review.mkdir()
        empty_decision = tmpdir / "decision"
        empty_decision.mkdir()
        empty_intake = tmpdir / "intake"
        empty_intake.mkdir()
        with patch.object(m, "REVIEW_DIR", empty_review), \
             patch.object(m, "DECISION_DIR", empty_decision), \
             patch.object(m, "INTAKE_DIR", empty_intake):
            result = self._call("show daily research review")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "do not have" in text or "no daily" in text or "run" in text,
            f"No-data fallback not helpful: {result.text}"
        )
        self.assertGreater(len(result.text.strip()), 20)


class TestDailyResearchReviewFormat(unittest.TestCase):
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
            "high_value_count": 3,
            "approval_required_count": 0,
            "top_opportunities": [
                {"title": "Build Credit Readiness Checklist", "status": "product_candidate",
                 "monetization_score": 80, "recommended_action": "Create a paid template",
                 "why_selected": "Fits credit/funding audience"},
            ],
            "rejected": [{"title": f"R{i}", "monetization_score": 10} for i in range(8)],
        }))
        (self.decision_dir / f"monetization_decision_cycle_{ts}.json").write_text(json.dumps([
            {"title": "Build Credit Readiness Checklist", "status": "product_candidate", "monetization_score": 80},
        ]))

    def _patch_and_call(self, text: str):
        import lib.hermes_daily_cycle_state as m
        from lib.hermes_internal_first import try_internal_first
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            return try_internal_first(text)

    def test_response_contains_source_count(self):
        result = self._patch_and_call("show daily research review")
        self.assertIsNotNone(result)
        self.assertIn("18", result.text)

    def test_response_contains_actionable_count(self):
        result = self._patch_and_call("show daily research review")
        self.assertIn("10", result.text)

    def test_response_contains_rejected_count(self):
        result = self._patch_and_call("show daily research review")
        self.assertIn("8", result.text)

    def test_response_contains_top_opportunities(self):
        result = self._patch_and_call("show daily research review")
        self.assertIsNotNone(result)
        text = result.text.lower()
        self.assertTrue(
            "top" in text or "opportunity" in text or "checklist" in text,
            f"No top opportunities section: {result.text[:300]}"
        )

    def test_response_contains_rejected_section(self):
        result = self._patch_and_call("show daily research review")
        text = result.text.lower()
        self.assertIn("rejected", text)

    def test_response_contains_evidence_paths(self):
        result = self._patch_and_call("show daily research review")
        text = result.text
        self.assertTrue(
            "review:" in text.lower() or "evidence" in text.lower() or "docs/reports" in text,
            f"No evidence paths in response: {text[:300]}"
        )

    def test_first_line_is_human_readable(self):
        result = self._patch_and_call("show daily research review")
        first_line = result.text.splitlines()[0]
        self.assertFalse(
            first_line.startswith("/") or first_line.startswith("docs/"),
            f"First line must be readable, not a path: {first_line}"
        )


if __name__ == "__main__":
    unittest.main()
