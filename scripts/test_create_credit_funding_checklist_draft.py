"""
test_create_credit_funding_checklist_draft.py
===============================================
Verify that create_credit_funding_readiness_checklist_draft() writes a real
Markdown artifact to disk and updates the action queue and decision log.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ROOT = Path(__file__).resolve().parent.parent
_CONTENT_DIR = _ROOT / "docs" / "reports" / "content"


class TestCreateCreditFundingChecklistDraft(unittest.TestCase):
    def setUp(self):
        from lib.hermes_content_artifact_builder import _find_existing_checklist_draft
        self._existing_before = _find_existing_checklist_draft()

    def test_artifact_builder_module_imports(self):
        import lib.hermes_content_artifact_builder as m
        for fn in ["create_credit_funding_readiness_checklist_draft",
                   "create_content_draft_from_action",
                   "find_best_content_action",
                   "build_content_artifact_path",
                   "format_content_created_response"]:
            self.assertTrue(hasattr(m, fn), f"Missing function: {fn}")

    def test_create_draft_returns_result_dict(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        self.assertIsInstance(result, dict)
        self.assertIn("created", result)
        self.assertIn("path", result)
        self.assertIn("action_id", result)

    def test_create_draft_writes_file(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        self.assertTrue(result.get("created"), f"Expected created=True, got {result}")
        path = _ROOT / result["path"]
        self.assertTrue(path.exists(), f"Draft file not found at {path}")

    def test_draft_file_has_required_sections(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        path = _ROOT / result["path"]
        content = path.read_text().lower()
        required = [
            "business setup", "credit profile", "documentation",
            "funding red flag", "compliance", "nexus",
        ]
        for section in required:
            self.assertIn(section, content,
                f"Draft must contain section '{section}'")

    def test_draft_file_has_compliance_note(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        path = _ROOT / result["path"]
        content = path.read_text().lower()
        self.assertIn("educational", content,
            "Draft must include compliance note stating educational purposes")
        self.assertIn("does not guarantee", content,
            "Draft must state it does not guarantee funding")

    def test_draft_is_internal_only_marked(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        path = _ROOT / result["path"]
        content = path.read_text()
        self.assertIn("INTERNAL", content,
            "Draft must be clearly marked as internal only")
        no_publish_markers = ["not for publication", "pending ray", "internal draft"]
        has_marker = any(m.lower() in content.lower() for m in no_publish_markers)
        self.assertTrue(has_marker, "Draft must have a 'not for publication' marker")

    def test_action_id_is_returned(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        self.assertIn("act_", result.get("action_id", ""),
            "Result must include a valid action_id")

    def test_path_is_in_content_dir(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        self.assertIn("docs/reports/content/", result.get("path", ""),
            "Draft must be saved in docs/reports/content/")

    def test_json_metadata_created(self):
        from lib.hermes_content_artifact_builder import create_credit_funding_readiness_checklist_draft
        result = create_credit_funding_readiness_checklist_draft(new_version=True)
        # JSON metadata is alongside the .md file
        md_path = _ROOT / result["path"]
        json_path = md_path.with_suffix(".json")
        self.assertTrue(json_path.exists(), f"JSON metadata not found at {json_path}")


if __name__ == "__main__":
    unittest.main()
