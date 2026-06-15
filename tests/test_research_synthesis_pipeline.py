"""Tests for research_synthesis_pipeline — topic classification and opportunity extraction."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import research_synthesis_pipeline as RSP


class TestResearchSynthesisPipeline(unittest.TestCase):

    def test_topic_classifiers_defined(self):
        self.assertIsInstance(RSP.TOPIC_CLASSIFIERS, dict)
        self.assertGreater(len(RSP.TOPIC_CLASSIFIERS), 0)

    def test_classify_topic_returns_known_topic(self):
        topic = RSP.classify_topic("funding readiness and business credit")
        self.assertIsInstance(topic, str)
        self.assertIn(topic, RSP.TOPIC_CLASSIFIERS or {"funding"})

    def test_classify_topic_returns_default_for_empty(self):
        topic = RSP.classify_topic("")
        self.assertIsInstance(topic, str)

    def test_classify_topic_detects_content(self):
        topic = RSP.classify_topic("YouTube video about affiliate marketing automation")
        self.assertIsInstance(topic, str)

    def test_extract_opportunities_returns_list(self):
        opps = RSP.extract_opportunities("A coaching program for credit repair professionals.", "funding")
        self.assertIsInstance(opps, list)

    def test_extract_opportunities_default_for_empty(self):
        opps = RSP.extract_opportunities("", "")
        self.assertIsInstance(opps, list)

    def test_timestamp_format(self):
        now = RSP._now()
        self.assertIsInstance(now, str)

    def test_no_secrets_in_module(self):
        import inspect
        source = inspect.getsource(RSP)
        self.assertNotIn("token=", source)
        self.assertNotIn("api_key", source)

    def test_no_paid_apis_at_module_level(self):
        import inspect
        source = inspect.getsource(RSP)
        module_lines = [l for l in source.split("\n")
                        if l.strip().startswith(("import ", "from "))
                        and not l.strip().startswith(("#", '"', "'"))]
        module_lines = [l for l in module_lines if not l[0].isspace()]
        for line in module_lines:
            if "urllib" in line or "requests" in line or "openai" in line:
                self.fail(f"Module-level network import: {line}")


if __name__ == "__main__":
    unittest.main()
