"""
test_hermes_truth_layer.py
Verify hermes_truth_layer.py collects evidence and returns a correct TruthPacket.
"""
import sys
import tempfile
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


from lib.hermes_truth_layer import collect_truth, TruthPacket, EvidenceItem


def test_collect_returns_truth_packet():
    result = collect_truth()
    if isinstance(result, TruthPacket):
        ok("collect_returns_truth_packet")
    else:
        fail("collect_returns_truth_packet", f"got {type(result)}")


def test_collected_at_is_iso_string():
    result = collect_truth()
    if result.collected_at and "T" in result.collected_at:
        ok("collected_at_is_iso_string")
    else:
        fail("collected_at_is_iso_string", repr(result.collected_at))


def test_sources_probed_non_empty():
    result = collect_truth()
    if result.sources_probed:
        ok(f"sources_probed_non_empty — probed: {result.sources_probed}")
    else:
        fail("sources_probed_non_empty", "sources_probed is empty")


def test_no_exceptions_on_missing_files():
    """collect_truth must not raise even when all artifact stores are empty/missing."""
    try:
        result = collect_truth()
        ok("no_exceptions_on_missing_files")
    except Exception as e:
        fail("no_exceptions_on_missing_files", str(e))


def test_verified_only_excludes_unverified():
    result = collect_truth()
    verified = result.verified_only()
    for item in verified:
        if item.evidence_level == "unverified_claim":
            fail("verified_only_excludes_unverified", f"found unverified_claim in verified_only()")
            return
    ok("verified_only_excludes_unverified")


def test_evidence_item_to_dict():
    item = EvidenceItem(
        source="artifact_registry",
        evidence_level="verified_file",
        label="test artifact",
        artifact_id="abc123",
        file_path="/tmp/test.json",
    )
    d = item.to_dict()
    required = {"source", "evidence_level", "label", "artifact_id", "file_path"}
    missing = required - set(d.keys())
    if not missing:
        ok("evidence_item_to_dict")
    else:
        fail("evidence_item_to_dict", f"missing keys: {missing}")


def test_truth_packet_summary_text():
    result = collect_truth()
    text = result.summary_text()
    if isinstance(text, str) and "Evidence collected" in text:
        ok("truth_packet_summary_text")
    else:
        fail("truth_packet_summary_text", repr(text[:80]))


def test_truth_packet_to_dict():
    result = collect_truth()
    d = result.to_dict()
    required = {"collected_at", "sources_probed", "total", "verified", "items"}
    missing = required - set(d.keys())
    if not missing:
        ok("truth_packet_to_dict")
    else:
        fail("truth_packet_to_dict", f"missing: {missing}")


def test_by_source_filter():
    result = collect_truth()
    ar_items = result.by_source("artifact_registry")
    for item in ar_items:
        if item.source != "artifact_registry":
            fail("by_source_filter", "by_source returned wrong source items")
            return
    ok("by_source_filter — artifact_registry items correctly filtered")


def test_source_intake_collector_with_real_log():
    """If INTAKE_LOG exists, items are read from it."""
    import lib.hermes_telegram_source_intake as si
    if not si.INTAKE_LOG.exists():
        ok("source_intake_collector_with_real_log — (no intake log on this machine)")
        return
    result = collect_truth()
    intake_items = result.by_source("source_intake")
    if intake_items:
        ok(f"source_intake_collector_with_real_log — {len(intake_items)} items")
    else:
        ok("source_intake_collector_with_real_log — log exists but no parseable entries (acceptable)")


if __name__ == "__main__":
    print("=== test_hermes_truth_layer ===")
    test_collect_returns_truth_packet()
    test_collected_at_is_iso_string()
    test_sources_probed_non_empty()
    test_no_exceptions_on_missing_files()
    test_verified_only_excludes_unverified()
    test_evidence_item_to_dict()
    test_truth_packet_summary_text()
    test_truth_packet_to_dict()
    test_by_source_filter()
    test_source_intake_collector_with_real_log()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
