"""Tests for the TheChoseone delegation router.
Run: python3 tests/test_thechosenone_delegation_router.py"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import thechosenone_delegation_router as DR  # noqa: E402

LATEST = ROOT / "logs" / "thechosenone" / "latest_command_receipt.json"


class TestDelegationRouter(unittest.TestCase):
    def test_research_classification(self):
        # (6.6) "run web research: Nav affiliate requirements" -> research
        cls = DR.classify_prompt("run web research: Nav affiliate requirements")
        self.assertEqual(cls["route"], "research")
        self.assertEqual(cls["safety"], "safe")

    def test_showroom_monetization_classification(self):
        # (6.7) "turn package proof_credit into offer" -> showroom + monetization
        cls = DR.classify_prompt("turn package proof_credit into offer")
        self.assertEqual(cls["route"], "showroom")
        self.assertEqual(cls["intent"], "monetization")
        self.assertEqual(cls.get("package"), "proof_credit")

    def test_blocks_unsafe_actions(self):
        # (6.8) unsafe send/email/publish/payment -> blocked
        for bad in ("send email to all leads", "publish the post now",
                    "charge the customer $97", "place a live trade",
                    "deploy to production"):
            cls = DR.classify_prompt(bad)
            self.assertEqual(cls["route"], "blocked", f"should block: {bad}")
            self.assertEqual(cls["execution_mode"], "blocked")

    def test_safety_disclaimer_not_falsely_blocked(self):
        # A monetization task whose text includes the user's OWN "Do not publish,
        # charge, email..." disclaimer must route to showroom, NOT blocked.
        cls = DR.classify_prompt(
            "create monetization task from package proof_credit: Turn this into a "
            "$97-$297 manual readiness review offer. Do not publish, send, charge, "
            "email, DM, deploy, or approve.")
        self.assertEqual(cls["route"], "showroom")
        self.assertEqual(cls["intent"], "monetization")
        self.assertEqual(cls.get("package"), "proof_credit")
        # but an affirmative unsafe action is still blocked
        self.assertEqual(DR.classify_prompt("publish it and charge them")["route"], "blocked")

    def test_workers_dry_run_only_without_bridge(self):
        # (6.9) codex/claude/opencode -> dry_run_only if no verified bridge
        self.assertFalse(DR.bridge_verified("codex"))
        for w in ("codex", "claude", "opencode"):
            cls = DR.classify_prompt(f"send this to {w}: build a thing")
            self.assertEqual(cls["route"], w)
            self.assertEqual(cls["execution_mode"], "dry_run_only")

    def test_delegate_creates_receipt(self):
        # (6.10) delegated tasks create receipts
        res = DR.delegate("run web research: best funding affiliate offers")
        self.assertIn("command_id", res["receipt"])
        self.assertTrue(LATEST.exists())
        rec = json.loads(LATEST.read_text())
        self.assertEqual(rec["route"], "research")
        self.assertIn(rec["final_status"], ("report_ready", "queued", "dry_run_only", "blocked"))
        for field in ("original_prompt", "sanitized_prompt", "execution_mode",
                      "output_artifact_path", "errors"):
            self.assertIn(field, rec)

    def test_no_secrets_in_receipt(self):
        # (6.11) no secrets appear in receipts
        DR.delegate("research token=TOPSECRETVAL chat_id 1234567890 affiliate offers")
        blob = LATEST.read_text()
        self.assertNotIn("TOPSECRETVAL", blob)
        self.assertNotIn("1234567890", blob)
        self.assertIn("[redacted]", blob)

    def test_single_response_no_double_reply(self):
        # (6.12) routing yields exactly one response (proxy for no double-reply)
        res = DR.delegate("research affiliate offers")
        self.assertIsInstance(res["response"], str)
        self.assertEqual(res["response"].count("Task received."), 1)
        # classification is deterministic -> one route, one reply
        c1 = DR.classify_prompt("research affiliate offers")
        c2 = DR.classify_prompt("research affiliate offers")
        self.assertEqual(c1, c2)

    def test_response_format(self):
        res = DR.delegate("run web research: Nav affiliate requirements")
        for section in ("Task received.", "Route:", "Status:", "What I will return:",
                        "Safety:", "Receipt:"):
            self.assertIn(section, res["response"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
