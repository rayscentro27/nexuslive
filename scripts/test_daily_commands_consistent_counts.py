"""
test_daily_commands_consistent_counts.py
==========================================
Verify that all daily Telegram commands return consistent counts from the same cycle.
'show rejected', 'show daily review', 'what did you find today' must all agree.
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


def _make_cycle_data(tmpdir: Path, ts: str, total: int, actionable: int, rejected_count: int):
    intake_dir = tmpdir / "docs" / "reports" / "intake"
    decision_dir = tmpdir / "docs" / "reports" / "monetization"
    review_dir = tmpdir / "docs" / "reports" / "review"
    for d in [intake_dir, decision_dir, review_dir]:
        d.mkdir(parents=True, exist_ok=True)

    rejected_list = [{"title": f"R{i}", "monetization_score": 10} for i in range(rejected_count)]
    actionable_list = [
        {"title": f"A{i}", "status": "content_candidate", "monetization_score": 70}
        for i in range(actionable)
    ]

    review_data = {
        "generated_at": ts,
        "total_sources": total,
        "actionable_count": actionable,
        "rejected_count": rejected_count,
        "high_value_count": 2,
        "approval_required_count": 0,
        "rejected": rejected_list,
        "top_opportunities": actionable_list[:3],
    }
    (review_dir / f"daily_research_review_{ts}.json").write_text(json.dumps(review_data))

    decision_data = actionable_list + [
        {"title": f"R{i}", "status": "reject", "monetization_score": 10} for i in range(rejected_count)
    ]
    (decision_dir / f"monetization_decision_cycle_{ts}.json").write_text(json.dumps(decision_data))
    (decision_dir / f"rejected_opportunities_{ts}.json").write_text(json.dumps(rejected_list))

    return intake_dir, decision_dir, review_dir


class TestConsistentCounts(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.intake_dir, self.decision_dir, self.review_dir = _make_cycle_data(
            self.tmpdir, "20260529_120000", total=18, actionable=10, rejected_count=8
        )

    def _patch(self, func):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            return func(m)

    def test_rejected_count_same_as_review_rejected_count(self):
        def check(m):
            rejected = m.load_rejected_sources()
            summary = m.load_daily_cycle_summary()
            return len(rejected), summary["rejected"]
        r_list_len, r_summary = self._patch(check)
        self.assertEqual(r_list_len, r_summary,
            f"load_rejected_sources returned {r_list_len} but summary shows {r_summary}")

    def test_total_sources_consistent(self):
        def check(m):
            summary = m.load_daily_cycle_summary()
            return summary["total_sources"]
        total = self._patch(check)
        self.assertEqual(total, 18)

    def test_actionable_consistent(self):
        def check(m):
            summary = m.load_daily_cycle_summary()
            top = m.load_top_opportunities()
            return summary["actionable"], len(top)
        actionable, top_count = self._patch(check)
        self.assertEqual(actionable, 10)
        self.assertGreater(top_count, 0)

    def test_all_counts_from_same_cycle(self):
        def check(m):
            cycle = m.find_latest_daily_cycle()
            rejected = m.load_rejected_sources()
            top = m.load_top_opportunities()
            summary = m.load_daily_cycle_summary()
            return cycle, len(rejected), len(top), summary
        cycle, r_len, t_len, summary = self._patch(check)
        # All paths should point to same timestamp
        self.assertIsNotNone(cycle["review"])
        ts = "20260529_120000"
        self.assertIn(ts, str(cycle["review"]))
        # Counts should match
        self.assertEqual(r_len, summary["rejected"])

    def test_two_cycles_always_uses_latest(self):
        """When two cycles exist, all commands use the newer one."""
        import lib.hermes_daily_cycle_state as m
        _make_cycle_data(self.tmpdir, "20260529_060000", total=10, actionable=5, rejected_count=5)

        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
            summary = m.load_daily_cycle_summary()
        # Should use 120000 (newer)
        self.assertIn("120000", str(cycle["review"]))
        self.assertEqual(summary["total_sources"], 18)


if __name__ == "__main__":
    unittest.main()
