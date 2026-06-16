"""Tests for wiring the Hermes intelligent layer into the live Telegram bot.
Run: python3 tests/test_hermes_intelligent_layer_wiring.py

Hermetic: exercises the flag gate and the IL routing helper WITHOUT calling the
local LLM (respond_llm) or any network. Operational commands are checked via the
router-gated path so the bot's existing behavior is preserved.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_intelligent_layer as IL          # noqa: E402
from lib import hermes_mobile_telegram as T              # noqa: E402

ON = "HERMES_INTELLIGENT_LAYER_ENABLED"
LATEST = ROOT / "logs" / "thechosenone" / "latest_command_receipt.json"


def _set_flag(val: bool):
    os.environ[ON] = "true" if val else "false"


class TestIntelligentLayerWiring(unittest.TestCase):
    def tearDown(self):
        os.environ.pop(ON, None)

    # 1) Flag OFF -> intelligent layer is never consulted (existing behavior).
    def test_flag_off_bypasses_layer(self):
        _set_flag(False)
        self.assertFalse(IL.enabled())
        self.assertIsNone(T._intelligent_reply("what do you think about Nexus?"))

    # 2) Flag ON -> opinion engine handles "what do you think about Nexus?"
    def test_flag_on_opinion_used(self):
        _set_flag(True)
        out = T._intelligent_reply("what do you think about Nexus?")
        self.assertIsNotNone(out)
        self.assertEqual(out["intent"], "opinion")
        for s in ("My take:", "Why:", "Risk:", "Best next move:"):
            self.assertIn(s, out["reply_text"])

    # 3) Flag ON -> "how do we make money in 30 days?" => Credit/Funding first
    def test_flag_on_monetization_credit_first(self):
        _set_flag(True)
        out = T._intelligent_reply("how do we make money in 30 days?")
        self.assertIsNotNone(out)
        self.assertIn("Credit/Funding", out["reply_text"])

    # 4) Flag ON -> research drafts a handoff with the full safety footer
    def test_flag_on_research_handoff(self):
        _set_flag(True)
        out = T._intelligent_reply("research the best affiliate offers for the funding checklist")
        self.assertIsNotNone(out)
        self.assertEqual(out["intent"], "research")
        self.assertIn("handoff-only", out["reply_text"])
        self.assertIn("run web research:", out["reply_text"])
        low = out["reply_text"].lower()
        for boundary in ("do not apply", "publish", "paid apis", "expose secrets"):
            self.assertIn(boundary, low)

    # 5) Flag ON -> "turn the credit pack into an offer" drafts the exact command
    def test_flag_on_prompt_monetization_command(self):
        _set_flag(True)
        out = T._intelligent_reply("turn the credit pack into an offer")
        self.assertIsNotNone(out)
        self.assertEqual(out["intent"], "prompt")
        self.assertIn("create monetization task from package proof_credit:", out["reply_text"])
        self.assertIn("Suggested route:\nshowroom", out["reply_text"])

    def test_flag_on_explicit_prompt_request(self):
        _set_flag(True)
        out = T._intelligent_reply(
            "create a prompt for TheChoseone to turn proof_credit into a paid offer")
        self.assertEqual(out["intent"], "prompt")
        self.assertIn("proof_credit", out["reply_text"])
        self.assertIn("Command for TheChoseone:", out["reply_text"])

    # 6) Operational "show package proof_credit" -> NOT handled by IL, no intro, no exec
    def test_operational_show_package_not_hijacked(self):
        _set_flag(True)
        self.assertIsNone(T._intelligent_reply("show package proof_credit"))
        res = T.handle_message("show package proof_credit")
        self.assertFalse(res["will_reply"])           # Hermes stays silent
        self.assertEqual(res["routed_to"], "thechoseone")
        self.assertFalse(res["executed"])

    # 7) "what needs approval" remains TheChoseone-owned
    def test_what_needs_approval_thechoseone_owned(self):
        _set_flag(True)
        self.assertIsNone(T._intelligent_reply("what needs approval"))
        res = T.handle_message("what needs approval")
        self.assertFalse(res["will_reply"])
        self.assertEqual(res["routed_to"], "thechoseone")

    # 8) Hermes execution stays disabled (no execute/delegate/send api; no receipt write)
    def test_hermes_execution_disabled(self):
        _set_flag(True)
        for forbidden in ("delegate", "execute", "send", "approve", "trade"):
            self.assertFalse(hasattr(IL, forbidden), f"IL must not expose {forbidden}()")
        before = LATEST.stat().st_mtime if LATEST.exists() else 0
        out = T.handle_message("turn the credit pack into an offer")
        self.assertTrue(out.get("intelligent_layer"))
        self.assertFalse(out["executed"])
        after = LATEST.stat().st_mtime if LATEST.exists() else 0
        self.assertEqual(before, after, "Hermes must NOT write a TheChoseone receipt")

    # 9) No secrets in IL reply (token planted in a research topic)
    def test_no_secrets_in_reply(self):
        _set_flag(True)
        out = T._intelligent_reply("research token=TOPSECRET123 affiliate offers chat_id 99887766")
        self.assertNotIn("TOPSECRET123", out["reply_text"])
        self.assertNotIn("99887766", out["reply_text"])

    # 10) No double reply: one deterministic reply per message
    def test_single_reply_no_double(self):
        _set_flag(True)
        a = T._intelligent_reply("what do you think about Nexus?")
        b = T._intelligent_reply("what do you think about Nexus?")
        self.assertEqual(a["reply_text"], b["reply_text"])
        # handle_message yields exactly one reply_text field
        res = T.handle_message("what do you think about Nexus?")
        self.assertTrue(res["will_reply"])
        self.assertIsInstance(res["reply_text"], str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
