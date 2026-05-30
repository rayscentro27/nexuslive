"""
test_content_draft_routes_to_artifact_builder.py
==================================================
Verify that 'create the first draft for the Credit/Funding Readiness Checklist'
routes to the artifact builder, not the LLM or old funding handler.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ARTIFACT_INDICATORS = [
    "content draft created",
    "internal draft",
    "docs/reports/content/",
    "i already created",
]

_BAD_ROUTING_INDICATORS = [
    "current funding blockers",
    "hook",
    "script:",
    "route to content_intelligence_scout",
]


class TestContentDraftRoutesToArtifactBuilder(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_create_first_draft_routes_to_artifact_builder(self):
        result = self._call("create the first draft for the Credit/Funding Readiness Checklist")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_artifact = any(kw in text for kw in _ARTIFACT_INDICATORS)
        self.assertTrue(has_artifact,
            f"Must route to artifact builder. Got:\n{result.text[:400]}")

    def test_create_first_draft_not_old_template(self):
        result = self._call("create the first draft for the Credit/Funding Readiness Checklist")
        self.assertIsNotNone(result)
        text = result.text.lower()
        for bad in _BAD_ROUTING_INDICATORS:
            self.assertNotIn(bad.lower(), text,
                f"Must not route to old template. Found '{bad}' in:\n{result.text[:300]}")

    def test_alternate_phrases_route_to_artifact_builder(self):
        phrases = [
            "create first draft",
            "build checklist draft",
            "draft lead magnet",
        ]
        for phrase in phrases:
            result = self._call(phrase)
            self.assertIsNotNone(result, f"'{phrase}' returned None")
            if result:
                text = result.text.lower()
                has_artifact = any(kw in text for kw in _ARTIFACT_INDICATORS)
                self.assertTrue(has_artifact,
                    f"'{phrase}' must route to artifact builder. Got:\n{result.text[:300]}")

    def test_matched_topic_is_create_content_draft(self):
        result = self._call("create the first draft for the Credit/Funding Readiness Checklist")
        self.assertIsNotNone(result)
        self.assertEqual(result.matched_topic, "create_content_draft",
            f"matched_topic must be 'create_content_draft', got '{result.matched_topic}'")

    def test_response_includes_evidence_path(self):
        result = self._call("create first draft")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_path = "docs/reports" in text or "act_" in text
        self.assertTrue(has_path, "Response must include evidence path or action ID")

    def test_response_mentions_approval_boundary(self):
        result = self._call("create first draft")
        self.assertIsNotNone(result)
        text = result.text.lower()
        has_boundary = any(kw in text for kw in ["approval", "internal", "publishing"])
        self.assertTrue(has_boundary,
            "Response must include approval boundary or internal-only notice")


if __name__ == "__main__":
    unittest.main()
