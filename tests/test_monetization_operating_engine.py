"""Tests for monetization_operating_engine — utility functions and focus areas."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import monetization_operating_engine as MOE


class TestMonetizationOperatingEngine(unittest.TestCase):

    def test_nexus_focus_areas_defined(self):
        self.assertIsInstance(MOE.NEXUS_FOCUS_AREAS, list)
        self.assertGreater(len(MOE.NEXUS_FOCUS_AREAS), 0)

    def test_focus_areas_include_funding_readiness(self):
        areas = " ".join(MOE.NEXUS_FOCUS_AREAS).lower()
        self.assertIn("funding", areas)
        self.assertIn("credit", areas)

    def test_parse_json_valid(self):
        result = MOE._parse_json('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_parse_json_invalid_returns_fallback(self):
        result = MOE._parse_json("not json", fallback={"default": True})
        self.assertEqual(result, {"default": True})

    def test_parse_json_empty_fallback(self):
        result = MOE._parse_json("")
        self.assertIsNone(result)

    def test_timestamp_format(self):
        ts = MOE._ts()
        self.assertIsInstance(ts, str)
        self.assertIn("_", ts)

    def test_now_format(self):
        now = MOE._now()
        self.assertIsInstance(now, str)

    def test_save_writes_file(self):
        tmp = Path("/tmp/test_mono_engine.txt")
        try:
            result = MOE._save(tmp, "test content")
            self.assertEqual(result, tmp)
            self.assertTrue(tmp.exists())
            self.assertEqual(tmp.read_text(), "test content")
        finally:
            tmp.unlink(missing_ok=True)

    def test_engine_class_imports_cleanly(self):
        engine = MOE.MonetizationOperatingEngine()
        self.assertIsInstance(engine, MOE.MonetizationOperatingEngine)

    def test_no_paid_apis_at_module_level(self):
        import inspect
        source = inspect.getsource(MOE)
        module_lines = [l for l in source.split("\n")
                        if l.strip().startswith(("import ", "from "))
                        and not l.strip().startswith(("#", '"', "'"))]
        module_lines = [l for l in module_lines if not l[0].isspace()]
        for line in module_lines:
            if "urllib" in line or "requests" in line or "openai" in line:
                self.fail(f"Module-level network import: {line}")

    def test_query_existing_assets_returns_dict(self):
        assets = MOE._query_existing_assets()
        self.assertIsInstance(assets, dict)


if __name__ == "__main__":
    unittest.main()
