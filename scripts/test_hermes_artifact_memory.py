"""Test HermesArtifactMemory — register, retrieve, and summary table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))

from lib.hermes_artifact_memory import HermesArtifactMemory, ARTIFACT_MEMORY_FILE

def main():
    memory = HermesArtifactMemory()

    # Register test artifacts
    test_path = Path("docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_TEST.md")
    r1 = memory.register("ceo_packet", str(test_path), run_id="test_001", summary="test CEO packet")
    r2 = memory.register("compliance_review", "docs/reports/learn_by_doing/credit_repair/compliance_review_test.md", run_id="test_001")
    r3 = memory.register("ceo_packet", "docs/reports/ceo_review/NEXUS_MONETIZATION_CEO_PACKET_TEST2.md", run_id="test_002", summary="second test packet")

    assert ARTIFACT_MEMORY_FILE.exists(), "Artifact memory file not created"

    # Latest should be TEST2
    latest = memory.latest("ceo_packet")
    assert latest is not None, "No latest ceo_packet found"
    assert "TEST2" in latest["path"], f"Expected TEST2, got {latest['path']}"
    print(f"✅ latest(ceo_packet) → {Path(latest['path']).name}")

    # History
    history = memory.history("ceo_packet", n=5)
    assert len(history) >= 2, f"Expected >= 2 history items, got {len(history)}"
    print(f"✅ history(ceo_packet) → {len(history)} items")

    # All types
    types = memory.all_types()
    assert "ceo_packet" in types
    assert "compliance_review" in types
    print(f"✅ all_types() → {types}")

    # Summary table
    table = memory.summary_table()
    assert "ceo_packet" in table
    print(f"✅ summary_table():\n{table}")

    print("\n✅ Artifact memory tests passed.")

if __name__ == "__main__":
    main()
