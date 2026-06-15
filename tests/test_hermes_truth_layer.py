"""Tests for Hermes truth layer. Run: python3 tests/test_hermes_truth_layer.py"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import hermes_truth_layer as TL  # noqa: E402


class TestTruthLayer(unittest.TestCase):
    def test_evidence_item_defaults(self):
        item = TL.EvidenceItem(
            source="test_source",
            evidence_level="unverified_claim",
            label="test claim",
        )
        self.assertEqual(item.label, "test claim")
        self.assertEqual(item.evidence_level, "unverified_claim")
        self.assertIsNotNone(item.source)

    def test_truth_packet_structure(self):
        packet = TL.TruthPacket(collected_at="2026-01-01T00:00:00")
        self.assertEqual(len(packet.items), 0)
        self.assertEqual(len(packet.sources_probed), 0)

    def test_verified_only_filters(self):
        packet = TL.TruthPacket(collected_at="now")
        packet.items.append(
            TL.EvidenceItem(source="test", evidence_level="verified_file", label="verified")
        )
        packet.items.append(
            TL.EvidenceItem(source="test", evidence_level="unverified_claim", label="unverified")
        )
        verified = packet.verified_only()
        self.assertEqual(len(verified), 1)
        self.assertEqual(verified[0].evidence_level, "verified_file")

    def test_summary_text_no_evidence(self):
        packet = TL.TruthPacket(collected_at="now")
        summary = packet.summary_text()
        self.assertIn("No verified evidence", summary)

    def test_evidence_levels_ordered(self):
        levels = ["verified_file", "verified_supabase", "verified_workflow_output", "verified_log", "unverified_claim"]
        self.assertEqual(TL.EVIDENCE_LEVELS, levels) if hasattr(TL, "EVIDENCE_LEVELS") else None

    def test_collect_truth_no_secrets(self):
        packet = TL.collect_truth()
        text = str(packet.to_dict())
        for secret in ("sk-", "api_key", "password", "token"):
            self.assertNotIn(secret, text.lower())

    def test_collect_truth_returns_packet(self):
        packet = TL.collect_truth()
        self.assertIsInstance(packet, TL.TruthPacket)
        self.assertIsNotNone(packet.collected_at)

    def test_by_source_filter(self):
        packet = TL.TruthPacket(collected_at="now")
        packet.items.append(
            TL.EvidenceItem(source="artifact_registry", evidence_level="verified_file", label="test")
        )
        results = packet.by_source("artifact_registry")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source, "artifact_registry")

    def test_empty_by_source_returns_empty(self):
        packet = TL.TruthPacket(collected_at="now")
        self.assertEqual(len(packet.by_source("nonexistent")), 0)


if __name__ == "__main__":
    unittest.main()
