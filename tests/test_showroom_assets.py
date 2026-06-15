"""Tests for the Showroom asset/package registry + manual-use review semantics.
Run: python3 tests/test_showroom_assets.py

Isolated: REGISTRY is redirected to a temp file so the real runtime registry is
never touched and nothing committable is written.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import showroom_assets as SA  # noqa: E402


class TestShowroomAssets(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = SA.REGISTRY
        SA.REGISTRY = Path(self._tmp.name) / "showroom_assets.json"

    def tearDown(self):
        SA.REGISTRY = self._orig
        self._tmp.cleanup()

    def test_register_and_lookup(self):
        a = SA.register("proof_credit", "Credit Readiness Review", "docs/x.md", status="needs_review")
        self.assertIn("asset_id", a)
        self.assertEqual(a["asset_type"], "proof_credit")
        self.assertTrue(any(x["asset_id"] == a["asset_id"] for x in SA.by_status("needs_review")))
        self.assertTrue(any(x["asset_id"] == a["asset_id"] for x in SA.recent()))

    def test_review_batch_requires_package_id_no_blanket_approval(self):
        # Empty package id must be refused — no blanket approval.
        res = SA.review_batch("", "approved")
        self.assertFalse(res["ok"])
        self.assertIn("package_id required", res["error"])

    def test_review_batch_on_package(self):
        SA.register("proof_credit", "A", "a.md", status="needs_review")
        SA.register("proof_credit", "B", "b.md", status="needs_review")
        res = SA.review_batch("proof_credit", "approved_for_manual_use_only", notes="ok")
        self.assertTrue(res["ok"])
        self.assertEqual(res["count"], 2)
        self.assertEqual(res["package_id"], "proof_credit")

    def test_review_batch_unknown_package_is_safe(self):
        res = SA.review_batch("does_not_exist", "approved")
        self.assertFalse(res["ok"])
        self.assertIn("no assets found", res["error"])

    def test_manual_use_status_available(self):
        # The manual-use-only status must exist as an allowed batch status.
        self.assertIn("approved_for_manual_use_only", SA.BATCH_STATUSES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
