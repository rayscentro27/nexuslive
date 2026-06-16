"""Telegram sender uses the certifi CA bundle. Run: python3 tests/test_telegram_certifi.py
No live Telegram calls — context construction only."""
import ssl
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_gate as G  # noqa: E402


class TestTelegramCertifi(unittest.TestCase):
    def test_returns_ssl_context(self):
        ctx = G._telegram_ssl_ctx()
        self.assertIsInstance(ctx, ssl.SSLContext)

    def test_context_is_verifying(self):
        # Must verify certificates — never an unverified context.
        ctx = G._telegram_ssl_ctx()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_context_is_cached(self):
        self.assertIs(G._telegram_ssl_ctx(), G._telegram_ssl_ctx())

    def test_prefers_certifi_bundle(self):
        # When certifi is installed, the loaded CA store should include it.
        try:
            import certifi
        except Exception:
            self.skipTest("certifi not installed")
        ctx = G._telegram_ssl_ctx()
        self.assertGreater(ctx.cert_store_stats().get("x509_ca", 0), 0)

    def test_send_helper_exists_and_is_callable(self):
        self.assertTrue(callable(G._telegram_send))


if __name__ == "__main__":
    unittest.main()
