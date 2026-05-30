"""
test_content_draft_no_old_template_leak.py
===========================================
Verify that 'create first draft' commands do NOT produce output from the
old social-script template (Hook / Script: / Your Business Structure...).

The old template is allowed to exist for social script generation but must
not answer: create first draft, build checklist draft, draft lead magnet.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_OLD_TEMPLATE_PHRASES = [
    "current funding blockers",
    "your business structure could be holding you back",
    "hook\n",
    "**hook**",
    "script:\n",
    "clear the top blocker, then rerun readiness check",
]

_DRAFT_TRIGGERS = [
    "create the first draft for the Credit/Funding Readiness Checklist",
    "create first draft",
    "build checklist draft",
    "draft lead magnet",
    "create the checklist draft",
]


class TestContentDraftNoOldTemplateLeak(unittest.TestCase):
    def _call(self, text: str):
        from lib.hermes_internal_first import try_internal_first
        return try_internal_first(text)

    def test_no_old_template_in_draft_commands(self):
        for trigger in _DRAFT_TRIGGERS:
            result = self._call(trigger)
            self.assertIsNotNone(result, f"'{trigger}' returned None")
            if result:
                text = result.text.lower()
                for phrase in _OLD_TEMPLATE_PHRASES:
                    self.assertNotIn(phrase.lower(), text,
                        f"Old template phrase '{phrase}' appeared in response to '{trigger}'")

    def test_no_hook_script_leak(self):
        result = self._call("create first draft")
        self.assertIsNotNone(result)
        text = result.text
        self.assertNotIn("Hook\n", text)
        self.assertNotIn("Script:\n", text)
        self.assertNotIn("Your Business Structure Could Be Holding", text)

    def test_funding_topic_still_works_for_blockers(self):
        """The 'funding' topic should still work for explicit funding blocker queries."""
        result = self._call("show funding")
        # This may or may not return None — just ensure it doesn't crash
        # and if it does respond, it shouldn't be a draft creation message
        if result:
            text = result.text.lower()
            self.assertNotIn("content draft created", text,
                "'show funding' must not return draft-creation response")


if __name__ == "__main__":
    unittest.main()
