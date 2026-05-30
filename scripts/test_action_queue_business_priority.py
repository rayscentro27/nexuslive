"""
test_action_queue_business_priority.py
========================================
Verify that the action queue puts specific business work (content, products,
credit, newsletters) before generic operating-loop actions.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestActionQueueBusinessPriority(unittest.TestCase):
    def _make_action(self, title: str, priority: int = 50, status="queued"):
        from lib.hermes_action_queue import Action
        return Action(title=title, priority=priority, status=status)

    def test_meta_action_scores_zero(self):
        from lib.hermes_action_queue import _action_business_score, _is_meta_action
        meta = self._make_action("run operating loop to identify top revenue action this week", priority=95)
        self.assertTrue(_is_meta_action(meta), "Operating loop action should be meta")
        self.assertEqual(_action_business_score(meta), 0,
            "Meta action must score 0 regardless of priority")

    def test_business_action_beats_meta_action(self):
        from lib.hermes_action_queue import _action_business_score
        meta = self._make_action("run operating loop to identify top revenue action this week", priority=95)
        biz = self._make_action("credit repair checklist draft", priority=70)
        self.assertGreater(_action_business_score(biz), _action_business_score(meta),
            "Business action must score higher than meta action even with lower priority")

    def test_newsletter_action_beats_operating_loop(self):
        from lib.hermes_action_queue import _action_business_score
        meta = self._make_action("operating loop intake pipeline", priority=95)
        newsletter = self._make_action("newsletter premium tier launch", priority=60)
        self.assertGreater(_action_business_score(newsletter), _action_business_score(meta))

    def test_assigned_action_gets_bonus(self):
        from lib.hermes_action_queue import _action_business_score, Action
        unassigned = Action(title="credit score guide", priority=50, status="queued")
        assigned = Action(title="credit score guide", priority=50, status="assigned",
                          assigned_scout="content_scout")
        self.assertGreater(_action_business_score(assigned), _action_business_score(unassigned))

    def test_unique_open_actions_business_first(self):
        from lib.hermes_action_queue import get_unique_open_actions, _is_meta_action
        actions = get_unique_open_actions()
        if len(actions) < 2:
            self.skipTest("Not enough actions in queue to test ordering")
        # Find first non-meta action
        first_biz = next((a for a in actions if not _is_meta_action(a)), None)
        first_meta = next((a for a in actions if _is_meta_action(a)), None)
        if first_biz and first_meta:
            biz_idx = actions.index(first_biz)
            meta_idx = actions.index(first_meta)
            self.assertLess(biz_idx, meta_idx,
                f"Business action '{first_biz.title}' should appear before "
                f"meta action '{first_meta.title}' in sorted queue")

    def test_format_summary_has_why_it_matters(self):
        from lib.hermes_action_queue import (
            format_action_queue_summary_common_language, get_unique_open_actions, _is_meta_action
        )
        business_actions = [a for a in get_unique_open_actions() if not _is_meta_action(a)]
        if not business_actions:
            self.skipTest("No business actions in queue")
        summary = format_action_queue_summary_common_language()
        self.assertIn("Why it matters", summary,
            "Action queue summary must include 'Why it matters' for business actions")

    def test_format_summary_separates_system_actions(self):
        from lib.hermes_action_queue import (
            format_action_queue_summary_common_language, get_unique_open_actions, _is_meta_action
        )
        meta_actions = [a for a in get_unique_open_actions() if _is_meta_action(a)]
        business_actions = [a for a in get_unique_open_actions() if not _is_meta_action(a)]
        if not meta_actions or not business_actions:
            self.skipTest("Need both meta and business actions to test separation")
        summary = format_action_queue_summary_common_language()
        self.assertIn("System / background", summary,
            "Action queue must label generic system actions separately")


if __name__ == "__main__":
    unittest.main()
