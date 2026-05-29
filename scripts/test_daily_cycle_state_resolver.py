"""
test_daily_cycle_state_resolver.py
====================================
Tests for hermes_daily_cycle_state unified state resolver.
All daily Telegram commands must read from the same latest cycle.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import unittest


class TestFindLatestDailyCycle(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.intake_dir = Path(self.tmpdir) / "docs" / "reports" / "intake"
        self.decision_dir = Path(self.tmpdir) / "docs" / "reports" / "monetization"
        self.review_dir = Path(self.tmpdir) / "docs" / "reports" / "review"
        for d in [self.intake_dir, self.decision_dir, self.review_dir]:
            d.mkdir(parents=True)

    def _write(self, path: Path, data):
        path.write_text(json.dumps(data))

    def test_returns_none_paths_when_no_data(self):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
        self.assertIsNone(cycle["review"])
        self.assertIsNone(cycle["decision"])
        self.assertIsNone(cycle["rejected"])
        self.assertIsNone(cycle["intake"])

    def test_finds_latest_review(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.review_dir / "daily_research_review_20260529_100000.json", {"ts": "old"})
        self._write(self.review_dir / "daily_research_review_20260529_200000.json", {"ts": "new"})
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
        self.assertIsNotNone(cycle["review"])
        self.assertIn("200000", str(cycle["review"]))

    def test_matches_decision_to_review_timestamp(self):
        import lib.hermes_daily_cycle_state as m
        ts = "20260529_222011"
        self._write(self.review_dir / f"daily_research_review_{ts}.json", {})
        self._write(self.decision_dir / f"monetization_decision_cycle_{ts}.json", [])
        self._write(self.decision_dir / "monetization_decision_cycle_20260528_100000.json", [])
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
        self.assertIsNotNone(cycle["decision"])
        self.assertIn(ts, str(cycle["decision"]))

    def test_matches_rejected_to_review_timestamp(self):
        import lib.hermes_daily_cycle_state as m
        ts = "20260529_222011"
        self._write(self.review_dir / f"daily_research_review_{ts}.json", {})
        self._write(self.decision_dir / f"rejected_opportunities_{ts}.json", [])
        self._write(self.decision_dir / "rejected_opportunities_20260528_100000.json", [])
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
        self.assertIsNotNone(cycle["rejected"])
        self.assertIn(ts, str(cycle["rejected"]))

    def test_falls_back_to_latest_decision_when_no_review(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.decision_dir / "monetization_decision_cycle_20260529_200000.json", [])
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            cycle = m.find_latest_daily_cycle()
        self.assertIsNone(cycle["review"])
        self.assertIsNotNone(cycle["decision"])


class TestLoadDailyCycleSummary(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.intake_dir = Path(self.tmpdir) / "docs" / "reports" / "intake"
        self.decision_dir = Path(self.tmpdir) / "docs" / "reports" / "monetization"
        self.review_dir = Path(self.tmpdir) / "docs" / "reports" / "review"
        for d in [self.intake_dir, self.decision_dir, self.review_dir]:
            d.mkdir(parents=True)

    def _write(self, path: Path, data):
        path.write_text(json.dumps(data))

    def test_has_data_false_when_empty(self):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            summary = m.load_daily_cycle_summary()
        self.assertFalse(summary["has_data"])

    def test_reads_counts_from_review_artifact(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "total_sources": 18,
            "actionable_count": 10,
            "rejected_count": 8,
            "high_value_count": 3,
            "approval_required_count": 1,
            "top_opportunities": [{"title": "Top opp", "monetization_score": 82}],
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            summary = m.load_daily_cycle_summary()
        self.assertTrue(summary["has_data"])
        self.assertEqual(summary["total_sources"], 18)
        self.assertEqual(summary["actionable"], 10)
        self.assertEqual(summary["rejected"], 8)
        self.assertEqual(summary["high_value"], 3)
        self.assertEqual(summary["pending_approval"], 1)
        self.assertIsNotNone(summary["top_opportunity"])

    def test_falls_back_to_decision_cycle_when_no_review(self):
        import lib.hermes_daily_cycle_state as m
        decisions = [
            {"title": "A", "status": "content_candidate", "monetization_score": 80},
            {"title": "B", "status": "reject", "monetization_score": 20},
        ]
        self._write(self.decision_dir / "monetization_decision_cycle_20260529_120000.json", decisions)
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            summary = m.load_daily_cycle_summary()
        self.assertTrue(summary["has_data"])
        self.assertEqual(summary["actionable"], 1)
        self.assertEqual(summary["rejected"], 1)


class TestLoadRejectedSources(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.intake_dir = Path(self.tmpdir) / "docs" / "reports" / "intake"
        self.decision_dir = Path(self.tmpdir) / "docs" / "reports" / "monetization"
        self.review_dir = Path(self.tmpdir) / "docs" / "reports" / "review"
        for d in [self.intake_dir, self.decision_dir, self.review_dir]:
            d.mkdir(parents=True)

    def _write(self, path, data):
        path.write_text(json.dumps(data))

    def test_returns_empty_list_when_no_data(self):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            rejected = m.load_rejected_sources()
        self.assertEqual(rejected, [])

    def test_reads_rejected_from_review_artifact(self):
        import lib.hermes_daily_cycle_state as m
        rejected_data = [
            {"title": "Bad source", "monetization_score": 15, "why_rejected": "Low score"},
        ]
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "rejected": rejected_data,
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            result = m.load_rejected_sources()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Bad source")

    def test_reads_rejected_from_rejected_file_when_no_review_rejected_field(self):
        import lib.hermes_daily_cycle_state as m
        ts = "20260529_120000"
        self._write(self.review_dir / f"daily_research_review_{ts}.json", {})
        self._write(self.decision_dir / f"rejected_opportunities_{ts}.json", [
            {"title": "Rej", "monetization_score": 10},
        ])
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            result = m.load_rejected_sources()
        self.assertEqual(len(result), 1)

    def test_rejected_count_matches_review_count(self):
        """show rejected and show daily review must report same count."""
        import lib.hermes_daily_cycle_state as m
        rejected_data = [
            {"title": "A", "monetization_score": 10},
            {"title": "B", "monetization_score": 12},
            {"title": "C", "monetization_score": 8},
        ]
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "rejected": rejected_data,
            "rejected_count": 3,
            "total_sources": 10,
            "actionable_count": 7,
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            rejected = m.load_rejected_sources()
            summary = m.load_daily_cycle_summary()
        self.assertEqual(len(rejected), summary["rejected"])

    def test_respects_limit(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "rejected": [{"title": f"R{i}", "monetization_score": 5} for i in range(20)],
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            result = m.load_rejected_sources(limit=3)
        self.assertEqual(len(result), 3)


class TestFormatCommonLanguage(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.intake_dir = Path(self.tmpdir) / "docs" / "reports" / "intake"
        self.decision_dir = Path(self.tmpdir) / "docs" / "reports" / "monetization"
        self.review_dir = Path(self.tmpdir) / "docs" / "reports" / "review"
        for d in [self.intake_dir, self.decision_dir, self.review_dir]:
            d.mkdir(parents=True)

    def _write(self, path, data):
        path.write_text(json.dumps(data))

    def test_no_data_prompt(self):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            text = m.format_daily_cycle_status_common_language()
        self.assertIn("No daily intake", text)

    def test_shows_counts_in_plain_language(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "total_sources": 18, "actionable_count": 10, "rejected_count": 8,
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            text = m.format_daily_cycle_status_common_language()
        self.assertIn("18", text)
        self.assertIn("10", text)
        self.assertIn("8", text)

    def test_no_raw_paths_in_common_language(self):
        import lib.hermes_daily_cycle_state as m
        self._write(self.review_dir / "daily_research_review_20260529_120000.json", {
            "total_sources": 5, "actionable_count": 3, "rejected_count": 2,
        })
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            text = m.format_daily_cycle_status_common_language()
        self.assertNotIn("docs/reports", text)

    def test_information_sources_no_directory_dump(self):
        import lib.hermes_daily_cycle_state as m
        with patch.object(m, "REVIEW_DIR", self.review_dir), \
             patch.object(m, "DECISION_DIR", self.decision_dir), \
             patch.object(m, "INTAKE_DIR", self.intake_dir):
            text = m.format_information_sources_common_language()
        # Should NOT dump raw directory listing
        self.assertNotIn("items)", text)
        self.assertNotIn("not yet created", text)
        # Should explain sources in plain language
        self.assertIn("YouTube", text)
        self.assertIn("GitHub", text)


if __name__ == "__main__":
    unittest.main()
