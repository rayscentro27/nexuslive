"""War Room safety + delegation routing fix tests.
Run: python3 tests/test_war_room_safety_delegation_fix.py

Covers: Hermes never initiates live actions (flag-independent guard), worker &
unsafe commands route to TheChoseone, delegation outranks package summaries.
"""
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_live_action_guard as GUARD          # noqa: E402
from lib import hermes_mobile_telegram as T                # noqa: E402
from lib import nexus_war_room_router as R                 # noqa: E402
from lib import thechosenone_command_delegation as D       # noqa: E402

LATEST = ROOT / "logs" / "thechosenone" / "latest_command_receipt.json"
BANNED = ("initiate", "get those emails out", "send draft", "let's get those emails")


def _no_banned(text: str) -> bool:
    low = (text or "").lower()
    return not any(b in low for b in BANNED)


class TestWarRoomSafetyFix(unittest.TestCase):
    # 1) Hermes direct message "send emails to leads": no initiate, safe handoff
    def test_hermes_direct_send_emails_refuses(self):
        # guard is flag-independent — verify with the flag OFF too
        os.environ["HERMES_INTELLIGENT_LAYER_ENABLED"] = "false"
        out = T._reply_for("send emails to leads")
        self.assertIn("will not start or send it", out)
        self.assertIn("create outreach review task", out)
        self.assertTrue(_no_banned(out), f"banned phrase in: {out!r}")

    # 2) @mention "send emails to leads": refuse live action, draft safe review task
    def test_hermes_mention_send_emails(self):
        out = T._reply_for("@NexusHermesMobileBot send emails to leads")
        self.assertIn("Safe alternative", out)
        self.assertIn("Do not send emails", out)
        self.assertTrue(_no_banned(out))

    # 2b) flag ON must not change the guard outcome (guard runs first)
    def test_guard_independent_of_flag(self):
        os.environ["HERMES_INTELLIGENT_LAYER_ENABLED"] = "true"
        try:
            out = T._reply_for("send emails to leads")
            self.assertIn("will not start or send it", out)
            self.assertTrue(_no_banned(out))
        finally:
            os.environ["HERMES_INTELLIGENT_LAYER_ENABLED"] = "false"

    # 3) worker command -> TheChoseone, dry_run_only, bridge not verified
    def test_codex_dry_run_only(self):
        out = D.maybe_handle("send this to codex: improve Hermes Advisor")
        self.assertIn("Route: codex", out)
        self.assertIn("dry_run_only", out)
        self.assertIn("Worker bridge not verified", out)
        self.assertEqual(R.route("send this to codex: improve Hermes Advisor")["target"], "thechoseone")

    def test_worker_variants_route_to_thechoseone(self):
        for cmd in ("route to claude: refactor", "ask opencode to fix tests",
                    "send this to opencode: build x"):
            self.assertEqual(R.route(cmd)["target"], "thechoseone")
            self.assertIn("dry_run_only", D.maybe_handle(cmd))

    # 4) monetization delegation outranks package summary
    def test_monetization_outranks_package_summary(self):
        for cmd in ("create monetization task from package proof_credit: Turn this into a $97-$297 offer",
                    "turn package proof_credit into offer",
                    "turn proof_credit into a paid offer",
                    "create offer from package proof_credit",
                    "review package proof_credit for monetization"):
            out = D.maybe_handle(cmd)
            self.assertIsNotNone(out, f"delegation gate missed: {cmd!r}")
            self.assertIn("Route: showroom", out)

    # 5) show package proof_credit still falls through to package summary
    def test_show_package_still_summary(self):
        self.assertIsNone(D.maybe_handle("show package proof_credit"))

    # 6) what needs approval still falls through to approval queue
    def test_what_needs_approval_falls_through(self):
        self.assertIsNone(D.maybe_handle("what needs approval"))

    # 7) send emails to leads -> visible Blocked from TheChoseone
    def test_send_emails_blocked(self):
        out = D.maybe_handle("send emails to leads")
        self.assertTrue(out.startswith("Blocked."))
        self.assertIn("Reason:", out)
        self.assertIn("Safe alternative:", out)
        self.assertEqual(_receipt()["route"], "blocked")

    # 8) no Hermes response contains banned phrases (sweep several live-actions)
    def test_no_banned_phrases_anywhere(self):
        for cmd in ("send emails to leads", "email leads", "publish this post",
                    "charge customers", "deploy to production", "place a live trade",
                    "send this to codex: do x", "approve all packages automatically"):
            out = T._reply_for(cmd)
            self.assertTrue(_no_banned(out), f"banned phrase for {cmd!r}: {out!r}")

    # 9) no secrets in receipts
    def test_no_secrets_in_receipt(self):
        D.maybe_handle("send this to codex: use token=SUPERSECRET9 and chat_id 99887766")
        blob = LATEST.read_text()
        self.assertNotIn("SUPERSECRET9", blob)
        self.assertNotIn("99887766", blob)

    # ordinary questions must NOT be hijacked or refused
    def test_questions_not_hijacked(self):
        for q in ("how do we publish content?", "what should we deploy next quarter?",
                  "how do we make money in 30 days?"):
            self.assertIsNone(GUARD.refusal_if_live_action(q))
            self.assertIsNone(D.maybe_handle(q))


def _receipt() -> dict:
    return json.loads(LATEST.read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
