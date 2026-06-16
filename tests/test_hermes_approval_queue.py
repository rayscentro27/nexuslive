"""Tests for the manual-review approval queue (build/format + manual-use safety).
Run: python3 tests/test_hermes_approval_queue.py

Isolated: state/history files are redirected to a temp dir. The queue aggregates
from optional sources via try/except (it "never crashes"), so it works even when
those source modules are absent on this branch.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_approval_queue as AQ  # noqa: E402


class TestApprovalQueue(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._s, self._h = AQ._STATE_FILE, AQ._HISTORY_FILE
        AQ._STATE_FILE = Path(self._tmp.name) / "state.json"
        AQ._HISTORY_FILE = Path(self._tmp.name) / "history.jsonl"

    def tearDown(self):
        AQ._STATE_FILE, AQ._HISTORY_FILE = self._s, self._h
        self._tmp.cleanup()

    def test_manual_use_boundary_wording(self):
        # Approving only authorizes the next step — never a live action.
        b = AQ.APPROVAL_BOUNDARY.lower()
        self.assertIn("will not publish", b)
        self.assertIn("send emails", b)
        self.assertIn("without a separate explicit ray command", b)

    def test_build_queue_never_crashes(self):
        # Fault-tolerant aggregation: returns a list even with sources absent.
        q = AQ.build_approval_queue()
        self.assertIsInstance(q, list)

    def test_format_queue_is_safe_text(self):
        out = AQ.format_approval_queue()
        self.assertIsInstance(out, str)
        self.assertIn("APPROVAL QUEUE", out.upper())

    def test_normalize_item_has_required_fields(self):
        raw = {"_source_type": "test", "_raw": {}, "title": "Approve lead magnet",
               "if_rejected": "stays blocked"}
        item = AQ.normalize_approval_item(raw, 0)
        for k in ("approval_id", "title", "category", "risk_level"):
            self.assertIn(k, item)

    def test_risk_and_category_inference_are_pure(self):
        self.assertTrue(isinstance(AQ._infer_category("publish newsletter"), str))
        self.assertTrue(isinstance(AQ._infer_risk("send emails to leads"), str))

    def test_no_blanket_auto_actions_in_formatters(self):
        # A formatted detail/result must state what Hermes will NOT do automatically.
        raw = {"_source_type": "test", "_raw": {}, "title": "Approve something"}
        AQ._save_state({"items": [AQ.normalize_approval_item(raw, 0)]})
        text = AQ.format_approval_queue()
        self.assertNotIn("automatically approved", text.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
