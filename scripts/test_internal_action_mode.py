"""
test_internal_action_mode.py
=============================
Verify HERMES_INTERNAL_ACTION_MODE config flags are readable
and have the correct safe defaults.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import unittest


class TestInternalActionModeDefaults(unittest.TestCase):
    def _cfg(self) -> dict:
        # Reload without any env overrides
        from lib.hermes_runtime_config import get_internal_action_config
        return get_internal_action_config()

    def test_function_exists(self):
        from lib.hermes_runtime_config import get_internal_action_config
        self.assertTrue(callable(get_internal_action_config))

    def test_returns_dict_with_all_keys(self):
        cfg = self._cfg()
        expected_keys = {
            "internal_action_mode",
            "daily_intake_allow_telegram_run",
            "autonomous_internal_actions",
            "public_actions_require_approval",
            "paid_actions_require_approval",
            "live_trading_require_approval",
        }
        self.assertEqual(set(cfg.keys()), expected_keys)

    def test_all_values_are_bool(self):
        cfg = self._cfg()
        for k, v in cfg.items():
            self.assertIsInstance(v, bool, f"{k} should be bool, got {type(v)}")

    def test_internal_action_mode_default_true(self):
        env_backup = os.environ.pop("HERMES_INTERNAL_ACTION_MODE", None)
        try:
            from lib.hermes_runtime_config import get_internal_action_config
            self.assertTrue(get_internal_action_config()["internal_action_mode"])
        finally:
            if env_backup is not None:
                os.environ["HERMES_INTERNAL_ACTION_MODE"] = env_backup

    def test_daily_intake_allow_default_true(self):
        env_backup = os.environ.pop("HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN", None)
        try:
            from lib.hermes_runtime_config import get_internal_action_config
            self.assertTrue(get_internal_action_config()["daily_intake_allow_telegram_run"])
        finally:
            if env_backup is not None:
                os.environ["HERMES_DAILY_INTAKE_ALLOW_TELEGRAM_RUN"] = env_backup

    def test_autonomous_internal_actions_default_true(self):
        env_backup = os.environ.pop("HERMES_AUTONOMOUS_INTERNAL_ACTIONS", None)
        try:
            from lib.hermes_runtime_config import get_internal_action_config
            self.assertTrue(get_internal_action_config()["autonomous_internal_actions"])
        finally:
            if env_backup is not None:
                os.environ["HERMES_AUTONOMOUS_INTERNAL_ACTIONS"] = env_backup

    def test_public_actions_require_approval_default_true(self):
        cfg = self._cfg()
        self.assertTrue(cfg["public_actions_require_approval"],
            "Publishing must always require approval")

    def test_paid_actions_require_approval_default_true(self):
        cfg = self._cfg()
        self.assertTrue(cfg["paid_actions_require_approval"],
            "Paid actions must always require approval")

    def test_live_trading_require_approval_default_true(self):
        cfg = self._cfg()
        self.assertTrue(cfg["live_trading_require_approval"],
            "Live trading must always require approval")

    def test_env_override_false(self):
        os.environ["HERMES_INTERNAL_ACTION_MODE"] = "false"
        try:
            from lib.hermes_runtime_config import get_internal_action_config
            self.assertFalse(get_internal_action_config()["internal_action_mode"])
        finally:
            del os.environ["HERMES_INTERNAL_ACTION_MODE"]

    def test_env_override_true(self):
        os.environ["HERMES_AUTONOMOUS_INTERNAL_ACTIONS"] = "true"
        try:
            from lib.hermes_runtime_config import get_internal_action_config
            self.assertTrue(get_internal_action_config()["autonomous_internal_actions"])
        finally:
            del os.environ["HERMES_AUTONOMOUS_INTERNAL_ACTIONS"]


if __name__ == "__main__":
    unittest.main()
