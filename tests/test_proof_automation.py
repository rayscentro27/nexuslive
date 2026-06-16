"""Tests for the proof-automation package engine (draft-only, compliance-safe).
Run: python3 tests/test_proof_automation.py

Isolated: STORE and ASSET_DIR are redirected to a temp dir so no real runtime
store/assets are written.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import proof_automation as PA  # noqa: E402


class TestProofAutomation(unittest.TestCase):
    def setUp(self):
        # generate_assets() computes paths relative_to(ROOT), so the test dirs must
        # live INSIDE the repo. Use a gitignored logs/ tmp dir (nothing committable).
        self._tmp = tempfile.TemporaryDirectory(dir=str(ROOT / "logs"))
        self._store, self._adir = PA.STORE, PA.ASSET_DIR
        PA.STORE = Path(self._tmp.name) / "store.json"
        PA.ASSET_DIR = Path(self._tmp.name) / "assets"

    def tearDown(self):
        PA.STORE, PA.ASSET_DIR = self._store, self._adir
        self._tmp.cleanup()

    def test_compliance_scrub_removes_guarantees(self):
        scrubbed = PA.compliance_scrub("We offer guaranteed funding and guaranteed profit.")
        self.assertNotIn("guaranteed funding", scrubbed.lower())
        self.assertNotIn("guaranteed profit", scrubbed.lower())
        self.assertIn("education only", scrubbed.lower())

    def test_disclaimers_present_for_core_tracks(self):
        for track in ("credit", "funding", "opportunity", "trading"):
            d = PA._disclaimer(track)
            self.assertIn("Educational content only", d)
            self.assertIn("nothing published without approval", d.lower())

    def test_create_project_defaults_draft_only(self):
        proj = PA.create_project("credit", "build credit readiness pack")
        self.assertEqual(proj["track"], "credit")
        self.assertEqual(proj["automation_mode"], "draft_only")
        self.assertEqual(proj["status"], "new")

    def test_invalid_mode_falls_back_to_draft_only(self):
        proj = PA.create_project("funding", "x", mode="approved_live_BOGUS")
        self.assertEqual(proj["automation_mode"], "draft_only")

    def test_generate_assets_are_drafts(self):
        proj = PA.create_project("credit", "credit readiness")
        PA.run_scouts(proj["id"])
        assets = PA.generate_assets(proj["id"])
        self.assertTrue(len(assets) >= 1)
        # generated asset bodies carry the educational disclaimer (no guarantees)
        joined = " ".join(a.get("body", "") + a.get("title", "") for a in assets).lower()
        self.assertNotIn("guaranteed funding", joined)

    def test_automation_modes_never_default_live(self):
        self.assertIn("draft_only", PA.AUTOMATION_MODES)
        self.assertNotEqual(PA.AUTOMATION_MODES[0], "approved_live")


if __name__ == "__main__":
    unittest.main(verbosity=2)
