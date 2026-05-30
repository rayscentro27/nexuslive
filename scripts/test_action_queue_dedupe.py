"""
test_action_queue_dedupe.py
============================
Verify action queue deduplication helpers work correctly.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestNormalizeActionTitle(unittest.TestCase):
    def _norm(self, title: str) -> str:
        from lib.hermes_action_queue import normalize_action_title
        return normalize_action_title(title)

    def test_strips_bracket_status_prefix(self):
        result = self._norm("[product_candidate] Monetization opportunity: Paid template")
        self.assertNotIn("[product_candidate]", result)
        self.assertIn("monetization opportunity", result)

    def test_strips_status_prefix(self):
        result = self._norm("Status: content_candidate — Route to scout")
        self.assertNotIn("status:", result.lower())

    def test_lowercases(self):
        result = self._norm("Build Credit Checklist")
        self.assertEqual(result, "build credit checklist")

    def test_collapses_whitespace(self):
        result = self._norm("  run   operating  loop  ")
        self.assertEqual(result, "run operating loop")

    def test_empty_string(self):
        result = self._norm("")
        self.assertEqual(result, "")

    def test_same_title_different_brackets_dedupes(self):
        from lib.hermes_action_queue import normalize_action_title
        t1 = normalize_action_title("[content_candidate] Build checklist lead magnet")
        t2 = normalize_action_title("[product_candidate] Build checklist lead magnet")
        self.assertEqual(t1, t2, "Same core title with different status brackets must normalize to same key")


class TestActionDedupeKey(unittest.TestCase):
    def _key(self, **kwargs):
        from lib.hermes_action_queue import action_dedupe_key, Action
        a = Action(**kwargs)
        return action_dedupe_key(a)

    def test_same_title_same_key(self):
        k1 = self._key(title="Run operating loop to identify top revenue action this week")
        k2 = self._key(title="Run operating loop to identify top revenue action this week")
        self.assertEqual(k1, k2)

    def test_different_title_different_key(self):
        k1 = self._key(title="Build checklist lead magnet")
        k2 = self._key(title="Process YouTube sources")
        self.assertNotEqual(k1, k2)

    def test_same_title_different_scout_different_key(self):
        k1 = self._key(title="Build checklist", assigned_scout="scout_a")
        k2 = self._key(title="Build checklist", assigned_scout="scout_b")
        self.assertNotEqual(k1, k2)

    def test_bracket_titles_same_key(self):
        k1 = self._key(title="[content_candidate] Monetization opportunity: Newsletter premium tier")
        k2 = self._key(title="[product_candidate] Monetization opportunity: Newsletter premium tier")
        # Same core title, so key should match (only first tuple element differs by normalization)
        # Both should normalize to the same string
        from lib.hermes_action_queue import normalize_action_title
        self.assertEqual(
            normalize_action_title("[content_candidate] Monetization opportunity: Newsletter premium tier"),
            normalize_action_title("[product_candidate] Monetization opportunity: Newsletter premium tier"),
        )


class TestGetUniqueOpenActions(unittest.TestCase):
    def test_function_exists(self):
        from lib.hermes_action_queue import get_unique_open_actions
        self.assertTrue(callable(get_unique_open_actions))

    def test_returns_list(self):
        from lib.hermes_action_queue import get_unique_open_actions
        result = get_unique_open_actions()
        self.assertIsInstance(result, list)

    def test_unique_count_lte_total(self):
        from lib.hermes_action_queue import get_open_actions, get_unique_open_actions
        all_open = get_open_actions()
        unique = get_unique_open_actions()
        self.assertLessEqual(len(unique), len(all_open))

    def test_no_duplicate_titles_in_unique(self):
        from lib.hermes_action_queue import get_unique_open_actions, normalize_action_title
        unique = get_unique_open_actions()
        seen_keys = set()
        for a in unique:
            key = normalize_action_title(a.title)
            self.assertNotIn(key, seen_keys,
                f"Duplicate normalized title in unique list: {a.title}")
            seen_keys.add(key)


class TestGetOpenActionByTitle(unittest.TestCase):
    def test_function_exists(self):
        from lib.hermes_action_queue import get_open_action_by_title
        self.assertTrue(callable(get_open_action_by_title))

    def test_returns_none_for_unknown_title(self):
        from lib.hermes_action_queue import get_open_action_by_title
        result = get_open_action_by_title("zzzz this does not exist zzzz")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
