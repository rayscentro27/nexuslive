"""Tests for the Hermes -> TheChoseone prompt builder.
Run: python3 tests/test_hermes_to_thechosenone_prompt_builder.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_to_thechosenone_prompt_builder as PB  # noqa: E402


class TestPromptBuilder(unittest.TestCase):
    def test_format_has_all_sections(self):
        out = PB.build_task_prompt(
            task="Turn the credit pack into an offer.",
            goal="A reviewable paid offer.",
            inputs=["Package: proof_credit"],
            required_output=["Offer name", "Price options"],
            success_criteria="Ray can approve a concrete offer.",
            route="showroom")
        for section in ("Task:", "Goal:", "Context:", "Inputs:", "Required output:",
                        "Safety:", "Success criteria:", "Suggested route:"):
            self.assertIn(section, out)

    def test_safety_block_always_present(self):
        out = PB.build_task_prompt(task="x", goal="y")
        for s in PB.SAFETY_BLOCK:
            self.assertIn(s, out)

    def test_proof_credit_offer_task(self):
        # (6.4) draft a TheChoseone task to turn proof_credit into an offer
        out = PB.build_task_prompt(
            task="Turn the proof_credit package into a paid offer.",
            goal="A $97-$297 manual readiness review offer.",
            inputs=["Package: proof_credit"],
            route="showroom")
        self.assertIn("proof_credit", out)
        self.assertIn("Suggested route:\nshowroom", out)
        self.assertIn("Do not publish.", out)

    def test_route_validation_falls_back(self):
        out = PB.build_task_prompt(task="research affiliate offers", goal="g",
                                   route="not_a_real_route")
        # invalid route -> suggested, still inside allowed ROUTES
        last = out.strip().splitlines()[-1]
        self.assertIn(last, PB.ROUTES)

    def test_secrets_scrubbed_from_prompt(self):
        out = PB.build_task_prompt(task="use token=SUPERSECRET123", goal="g")
        self.assertNotIn("SUPERSECRET123", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
