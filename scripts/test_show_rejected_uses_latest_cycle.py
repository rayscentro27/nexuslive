"""
test_show_rejected_uses_latest_cycle.py
=========================================
Verify 'show rejected' handler reads from the same source as 'show daily review'.
The rejected count shown by both commands must be identical.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestShowRejectedUsesLatestCycle(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.intake_dir = self.tmpdir / "docs" / "reports" / "intake"
        self.decision_dir = self.tmpdir / "docs" / "reports" / "monetization"
        self.review_dir = self.tmpdir / "docs" / "reports" / "review"
        for d in [self.intake_dir, self.decision_dir, self.review_dir]:
            d.mkdir(parents=True)

        # Latest cycle: 8 rejected in review, 6 in rejected_opportunities (different older file)
        ts = "20260529_222011"
        self._ts = ts
        (self.review_dir / f"daily_research_review_{ts}.json").write_text(json.dumps({
            "total_sources": 18,
            "actionable_count": 10,
            "rejected_count": 8,
            "rejected": [{"title": f"R{i}", "monetization_score": 10} for i in range(8)],
        }))
        # Older rejected file with DIFFERENT count — should NOT be used
        (self.decision_dir / f"rejected_opportunities_20260528_100000.json").write_text(json.dumps(
            [{"title": f"OLD{i}", "monetization_score": 5} for i in range(6)]
        ))
        # Matching rejected file
        (self.decision_dir / f"rejected_opportunities_{ts}.json").write_text(json.dumps(
            [{"title": f"R{i}", "monetization_score": 10} for i in range(8)]
        ))

    def _patch(self, func):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            return func(m)

    def test_show_rejected_uses_review_data_not_older_rejected_file(self):
        def check(m):
            return m.load_rejected_sources()
        result = self._patch(check)
        # Should return 8 (from review artifact), not 6 (from old rejected file)
        self.assertEqual(len(result), 8,
            f"Expected 8 from review artifact, got {len(result)}")

    def test_rejected_count_matches_summary(self):
        def check(m):
            return m.load_rejected_sources(), m.load_daily_cycle_summary()
        rejected, summary = self._patch(check)
        self.assertEqual(len(rejected), summary["rejected"],
            f"Rejected list={len(rejected)} but summary says {summary['rejected']}")

    def test_rejected_sources_from_correct_cycle(self):
        def check(m):
            cycle = m.find_latest_daily_cycle()
            return cycle, m.load_rejected_sources()
        cycle, rejected = self._patch(check)
        self.assertIn(self._ts, str(cycle["review"]))
        # Titles should be R0..R7, not OLD0..OLD5
        titles = [r.get("title", "") for r in rejected]
        self.assertTrue(all(t.startswith("R") for t in titles),
            f"Got unexpected titles: {titles}")

    def test_no_stale_data_when_newer_cycle_exists(self):
        """Adding a newer cycle must cause both commands to switch to it."""
        import lib.hermes_daily_cycle_state as m
        new_ts = "20260529_230000"
        (self.review_dir / f"daily_research_review_{new_ts}.json").write_text(json.dumps({
            "total_sources": 5,
            "actionable_count": 4,
            "rejected_count": 1,
            "rejected": [{"title": "NewR", "monetization_score": 8}],
        }))
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            rejected = m.load_rejected_sources()
            summary = m.load_daily_cycle_summary()
        self.assertEqual(len(rejected), 1)
        self.assertEqual(summary["rejected"], 1)


if __name__ == "__main__":
    unittest.main()
