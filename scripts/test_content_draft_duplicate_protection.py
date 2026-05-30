"""
test_content_draft_duplicate_protection.py
===========================================
Verify that calling 'create first draft' twice does NOT create a duplicate.
Second call must return the existing artifact path.
Calling 'create a new version' MUST create a new file.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent


class TestContentDraftDuplicateProtection(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def _count_drafts(self) -> int:
        from lib.hermes_content_artifact_builder import _CONTENT_DIR, _CHECKLIST_SLUG
        if not _CONTENT_DIR.exists():
            return 0
        return len(list(_CONTENT_DIR.glob(f"{_CHECKLIST_SLUG}_draft_*.md")))

    def test_first_call_creates_draft(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=False)
        self.assertIsNotNone(result)
        # Either created a new one or found an existing one — both are valid
        self.assertIn("path", result)
        path = _ROOT / result["path"]
        self.assertTrue(path.exists(), "Draft file must exist after first call")

    def test_second_call_does_not_duplicate(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        # Ensure at least one draft exists
        create_credit_funding_readiness_checklist_draft(new_version=False)
        count_before = self._count_drafts()

        # Second call — must not create another file
        result = create_credit_funding_readiness_checklist_draft(new_version=False)
        self.assertTrue(result.get("is_duplicate") or not result.get("created"),
            "Second call must detect existing draft and not create duplicate")
        count_after = self._count_drafts()
        self.assertEqual(count_before, count_after,
            f"Second call must not add a new draft file. Before: {count_before}, after: {count_after}")

    def test_duplicate_response_includes_path(self):
        from lib.hermes_content_artifact_builder import (
            create_credit_funding_readiness_checklist_draft,
            format_content_created_response,
        )
        create_credit_funding_readiness_checklist_draft(new_version=False)
        result = create_credit_funding_readiness_checklist_draft(new_version=False)
        text = format_content_created_response(result)
        self.assertIn("docs/reports/content/", text,
            "Duplicate response must include the artifact path")

    def test_new_version_creates_new_file(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        import time
        # Ensure a draft exists first
        create_credit_funding_readiness_checklist_draft(new_version=False)
        count_before = self._count_drafts()

        # Small sleep to ensure different timestamp
        time.sleep(1)
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        self.assertTrue(result.get("created"),
            "new_version=True must create a new file")
        count_after = self._count_drafts()
        self.assertGreater(count_after, count_before,
            "new_version=True must increase the number of draft files")

    def test_via_route_duplicate_detection(self):
        """Test dedup via the full routing path."""
        r1 = self._call("create first draft")
        self.assertIsNotNone(r1)
        r2 = self._call("create first draft")
        self.assertIsNotNone(r2)
        text2 = r2.text.lower()
        # Second call must say "already created" OR path without "content draft created" header
        if "content draft created" in r1.text.lower():
            self.assertFalse(
                "content draft created" in text2 and "already" not in text2,
                "Second call must detect duplicate, not re-create"
            )

    def test_revise_it_creates_new_version(self):
        r = self._call("revise it")
        self.assertIsNotNone(r)
        text = r.text.lower()
        self.assertNotIn("current funding blockers", text,
            "'revise it' must not route to old template")
        # Must have artifact builder response
        has_artifact = any(kw in text for kw in [
            "content draft created", "docs/reports/content/", "i already created",
        ])
        self.assertTrue(has_artifact,
            f"'revise it' must route to artifact builder. Got:\n{r.text[:300]}")


if __name__ == "__main__":
    unittest.main()
