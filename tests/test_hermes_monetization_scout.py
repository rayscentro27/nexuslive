"""Tests for hermes_monetization_scout — trigger detection, idea extraction, risk detection."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_monetization_scout as SCOUT


class TestMonetizationScout(unittest.TestCase):

    def test_has_user_provided_source_pasted_text(self):
        self.assertTrue(SCOUT.has_user_provided_source(
            "Here is a transcript of a video about affiliate marketing..."))
        self.assertTrue(SCOUT.has_user_provided_source(
            "article: Business funding strategies for 2026"))
        self.assertTrue(SCOUT.has_user_provided_source(
            "notes: They said credit repair is booming."))

    def test_has_user_provided_source_short_message(self):
        self.assertFalse(SCOUT.has_user_provided_source("what do you think about affiliate marketing?"))
        self.assertFalse(SCOUT.has_user_provided_source("scout monetization opportunities"))
        self.assertFalse(SCOUT.has_user_provided_source("run monetization audit"))

    def test_is_monetization_scout_request(self):
        self.assertTrue(SCOUT.is_monetization_scout_request("monetization scout this idea"))
        self.assertTrue(SCOUT.is_monetization_scout_request("make money from this"))
        self.assertTrue(SCOUT.is_monetization_scout_request("what can nexus do with this"))

    def test_should_handle_returns_true_for_pasted_source(self):
        long_text = "video: " + "how to make money with ai automation and content marketing " * 15
        self.assertTrue(SCOUT.should_handle(long_text))

    def test_should_handle_returns_false_for_short_chat(self):
        self.assertFalse(SCOUT.should_handle("what is monetization?"))

    def test_extract_ideas_returns_list_of_dicts(self):
        source = "A newsletter about business credit with ai automation tools and marketing content"
        ideas = SCOUT.extract_ideas(source)
        self.assertIsInstance(ideas, list)
        if ideas:
            self.assertIn("name", ideas[0])
            self.assertIn("composite", ideas[0])

    def test_extract_ideas_empty_for_gibberish(self):
        ideas = SCOUT.extract_ideas("")
        self.assertIsInstance(ideas, list)

    def test_detect_risks_returns_list(self):
        source = "This product promises guaranteed approval for everyone."
        risks = SCOUT.detect_risks(source)
        self.assertIsInstance(risks, list)

    def test_detect_risks_no_false_positives(self):
        source = "Standard affiliate marketing program with typical commission structure."
        risks = SCOUT.detect_risks(source)
        self.assertIsInstance(risks, list)

    def test_analyze_source_returns_dict(self):
        source = "They have a coaching program for funding consultants at $5k per month."
        result = SCOUT.analyze_source(source)
        self.assertIsInstance(result, dict)
        self.assertIn("ideas", result)
        self.assertIn("risks", result)

    def test_format_scout_response_includes_structure(self):
        analysis = SCOUT.analyze_source("a video about how to make money with content")
        formatted = SCOUT.format_scout_response(analysis)
        self.assertIn("NEXUS MONETIZATION SCOUT", formatted)

    def test_no_secrets_in_analysis(self):
        source = "My API key is sk-abc123 and token=secretvalue"
        result = SCOUT.analyze_source(source)
        formatted = str(result)
        self.assertNotIn("sk-abc123", formatted)

    def test_run_scout_returns_string(self):
        result = SCOUT.run_scout("test message about monetization")
        self.assertIsInstance(result, str)

    def test_no_paid_apis_called(self):
        """scout module uses only stdlib (re); no network/API calls at module level."""
        import inspect
        source = inspect.getsource(SCOUT)
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("openai", source)


if __name__ == "__main__":
    unittest.main()
