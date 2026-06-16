"""Tests for wiring the delegation router into TheChoseone's live command handler.
Run: python3 tests/test_thechosenone_live_delegation_wiring.py

Exercises the gate `thechosenone_command_delegation.maybe_handle()` (the exact
function the live handler calls) WITHOUT instantiating the live Telegram bot, so
the running TheChoseone single-instance lock is never touched.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import thechosenone_command_delegation as D   # noqa: E402

LATEST = ROOT / "logs" / "thechosenone" / "latest_command_receipt.json"


def _receipt() -> dict:
    return json.loads(LATEST.read_text())


class TestLiveDelegationWiring(unittest.TestCase):
    # 1) run web research -> research, dry_run_only, receipt, provider note,
    #    and NOT the old "I do not have verified state" message.
    def test_run_web_research(self):
        out = D.maybe_handle("run web research: Nav business credit affiliate requirements")
        self.assertIsNotNone(out)
        self.assertIn("Route: research", out)
        self.assertIn("dry_run_only", out)
        self.assertIn("Web research provider is not verified yet", out)
        self.assertNotIn("I do not have verified state", out)
        rec = _receipt()
        self.assertEqual(rec["route"], "research")
        self.assertEqual(rec["final_status"], "dry_run_only")

    # 2) research <topic> -> research
    def test_research_topic(self):
        out = D.maybe_handle("research best affiliate offers for funding checklist")
        self.assertIn("Route: research", out)

    # 3) create monetization task from package -> showroom
    def test_monetization_task(self):
        out = D.maybe_handle(
            "create monetization task from package proof_credit: Turn this into a $97-$297 offer")
        self.assertIn("Route: showroom", out)
        self.assertEqual(_receipt()["route"], "showroom")

    # 4) turn package <id> into offer -> showroom
    def test_turn_package_into_offer(self):
        out = D.maybe_handle("turn package proof_credit into offer")
        self.assertIn("Route: showroom", out)

    # 5) send this to codex -> dry_run_only + bridge-not-verified
    def test_codex_dry_run_only(self):
        out = D.maybe_handle("send this to codex: improve Hermes Advisor")
        self.assertIn("Route: codex", out)
        self.assertIn("dry_run_only", out)
        self.assertIn("Worker bridge not verified", out)

    # 6) unsafe -> blocked
    def test_blocked_unsafe(self):
        out = D.maybe_handle("send emails to leads")
        self.assertTrue(out.startswith("Blocked."))
        self.assertIn("Reason:", out)
        self.assertIn("Safe alternative:", out)
        self.assertEqual(_receipt()["route"], "blocked")

    # 7-9) read-only commands must FALL THROUGH (gate returns None) so the
    #      existing TheChoseone handlers run unchanged.
    def test_readonly_commands_fall_through(self):
        for cmd in ("what needs approval", "show package proof_credit", "scout status",
                    "status", "war room version", "details package proof_credit"):
            self.assertIsNone(D.maybe_handle(cmd), f"{cmd!r} must fall through, not be delegated")

    # also: ordinary questions are not hijacked / not blocked
    def test_questions_not_hijacked(self):
        for q in ("how do we publish content?", "what should we deploy next quarter?",
                  "what do you think about Nexus?"):
            self.assertIsNone(D.maybe_handle(q))

    # 10) no secrets in receipts
    def test_no_secrets_in_receipt(self):
        D.maybe_handle("run web research: token=SECRETXYZ123 affiliate offers chat_id 99887766")
        blob = LATEST.read_text()
        self.assertNotIn("SECRETXYZ123", blob)
        self.assertNotIn("99887766", blob)

    def test_proof_automation_dry_run(self):
        out = D.maybe_handle("run proof automation dry run")
        self.assertIn("Route: proof_automation", out)
        self.assertIn("dry_run_only", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
