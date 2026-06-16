"""Tests for Hermes provider policy. Run: python3 tests/test_hermes_provider_policy.py"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_provider_policy as PP  # noqa: E402


class TestProviderPolicy(unittest.TestCase):
    def tearDown(self):
        for k in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "HERMES_ALLOW_OPENROUTER_FALLBACK"):
            os.environ.pop(k, None)

    def test_default_priority(self):
        policy = PP.load_provider_policy()
        self.assertGreater(len(policy.priority), 0)
        self.assertNotIn("openrouter", policy.priority)

    def test_openrouter_blocked_by_default(self):
        policy = PP.load_provider_policy()
        self.assertFalse(policy.openrouter_allowed)

    def test_policy_no_secrets_in_summary(self):
        policy = PP.load_provider_policy()
        summary = str(policy.summary_dict())
        for secret in ("sk-", "api_key_"):
            lower = secret.lower()
            if lower in summary:
                self.fail(f"Secret value pattern '{secret}' found in policy summary")

    def test_provider_status_no_secrets(self):
        status = PP.get_provider_status(redact=True)
        for secret in ("sk-", "api_key_"):
            lower = secret.lower()
            if lower in status.lower():
                self.fail(f"Secret value pattern '{secret}' found in provider status")

    def test_evidence_only_when_no_llm(self):
        best = PP.load_provider_policy().best_available()
        self.assertIn(best, ("evidence_only",) + PP.STRATEGIC_PROVIDERS)

    def test_openrouter_allowed_when_enabled(self):
        os.environ["HERMES_ALLOW_OPENROUTER_FALLBACK"] = "true"
        os.environ["OPENROUTER_API_KEY"] = "sk-test-key-12345"
        policy = PP.load_provider_policy()
        self.assertTrue(policy.openrouter_allowed)


if __name__ == "__main__":
    unittest.main()
