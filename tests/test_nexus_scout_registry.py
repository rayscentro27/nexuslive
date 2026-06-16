"""Tests for nexus_scout_registry — scout definitions, lookups, and summaries."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import nexus_scout_registry as NSR


class TestNexusScoutRegistry(unittest.TestCase):

    def test_divisions_defined(self):
        self.assertEqual(NSR.DIVISION_MARKET_INTELLIGENCE, "market_intelligence")
        self.assertEqual(NSR.DIVISION_MONETIZATION_INTELLIGENCE, "monetization_intelligence")

    def test_get_scout_returns_dict_for_valid_id(self):
        scouts = list(NSR.SCOUTS_BY_ID.keys())
        if scouts:
            scout = NSR.get_scout(scouts[0])
            self.assertIsNotNone(scout)
            self.assertIn("scout_id", scout)
            self.assertIn("name", scout)

    def test_get_scout_returns_none_for_invalid_id(self):
        self.assertIsNone(NSR.get_scout("nonexistent_scout"))

    def test_get_division_scouts_returns_list(self):
        monetization_scouts = NSR.get_division_scouts("monetization_intelligence")
        self.assertIsInstance(monetization_scouts, list)

    def test_get_division_scouts_empty_for_bad_division(self):
        result = NSR.get_division_scouts("unknown_division")
        self.assertEqual(result, [])

    def test_get_due_scouts_returns_list(self):
        due = NSR.get_due_scouts(since_hours=9999)
        self.assertIsInstance(due, list)

    def test_get_due_scouts_with_no_time(self):
        due = NSR.get_due_scouts(since_hours=0)
        self.assertIsInstance(due, list)

    def test_scout_registry_summary_returns_string(self):
        summary = NSR.scout_registry_summary()
        self.assertIsInstance(summary, str)
        self.assertIn("Monetization Intelligence", summary)

    def test_mark_scout_run_creates_flag_file(self):
        scouts = list(NSR.SCOUTS_BY_ID.keys())
        if scouts:
            sid = scouts[0]
            from pathlib import Path
            ROOT = Path(__file__).resolve().parent.parent
            flag = ROOT / "artifacts" / "scout_flags" / f"{sid}_last_run.json"
            flag.unlink(missing_ok=True)
            try:
                NSR.mark_scout_run(sid)
                self.assertTrue(flag.exists())
            finally:
                flag.unlink(missing_ok=True)

    def test_scouts_have_required_fields(self):
        for sid, scout in NSR.SCOUTS_BY_ID.items():
            with self.subTest(scout_id=sid):
                self.assertIn("name", scout)
                self.assertIn("schedule_hours", scout)
                self.assertIn("division", scout)

    def test_division_scouts_mapped(self):
        total = len(NSR.SCOUTS)
        mapped = sum(len(v) for v in NSR.DIVISION_SCOUTS.values())
        self.assertEqual(total, mapped)

    def test_no_secrets_in_registry(self):
        import json
        dump = json.dumps(NSR.SCOUTS_BY_ID)
        self.assertNotIn("token=", dump)
        self.assertNotIn("api_key", dump)

    def test_no_paid_apis(self):
        """No paid API modules imported at module level."""
        import inspect
        source = inspect.getsource(NSR)
        module_lines = [l for l in source.split("\n")
                        if l.strip().startswith(("import ", "from "))
                        and not l.strip().startswith(("#", '"', "'"))]
        module_lines = [l for l in module_lines if not l[0].isspace()]
        for line in module_lines:
            if "urllib" in line or "requests" in line or "openai" in line:
                self.fail(f"Module-level network import: {line}")


if __name__ == "__main__":
    unittest.main()
