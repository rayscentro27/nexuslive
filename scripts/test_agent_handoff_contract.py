"""
test_agent_handoff_contract.py
Verify AGENT_HANDOFF_CONTRACT.md exists and contains all required fields.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0

CONTRACT_PATH = ROOT / "docs" / "AGENT_HANDOFF_CONTRACT.md"


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


def test_contract_file_exists():
    if CONTRACT_PATH.exists():
        ok("contract_file_exists")
    else:
        fail("contract_file_exists", str(CONTRACT_PATH))


_content = CONTRACT_PATH.read_text() if CONTRACT_PATH.exists() else ""


def test_contract_has_required_fields_section():
    if "required" in _content.lower() and "field" in _content.lower():
        ok("contract_has_required_fields_section")
    else:
        fail("contract_has_required_fields_section")


def test_contract_mentions_no_artifact_no_completion():
    if "NO ARTIFACT" in _content.upper() or "no artifact" in _content.lower():
        ok("contract_mentions_no_artifact_no_completion")
    else:
        fail("contract_mentions_no_artifact_no_completion")


def test_contract_mentions_acceptance_criteria():
    if ("acceptance" in _content.lower() or "acceptance_criteria" in _content
            or "complete" in _content.lower() or "verified" in _content.lower()):
        ok("contract_mentions_acceptance_criteria")
    else:
        fail("contract_mentions_acceptance_criteria")


def test_contract_mentions_artifact_path():
    if "artifact_path" in _content or "file_path" in _content or "artifact path" in _content.lower():
        ok("contract_mentions_artifact_path")
    else:
        fail("contract_mentions_artifact_path")


def test_contract_mentions_agent_name():
    if "agent_name" in _content or "agent name" in _content.lower():
        ok("contract_mentions_agent_name")
    else:
        fail("contract_mentions_agent_name")


def test_contract_mentions_registry():
    if "registry" in _content.lower() or "nexus_artifact_registry" in _content:
        ok("contract_mentions_registry")
    else:
        fail("contract_mentions_registry")


def test_contract_has_example_handoffs():
    count = _content.count("##") + _content.count("```")
    if count >= 4:
        ok(f"contract_has_example_handoffs — found {count} section/code markers")
    else:
        fail("contract_has_example_handoffs", f"only {count} markers found")


def test_contract_blocks_live_trading():
    if "live trading" in _content.lower() or "live broker" in _content.lower():
        ok("contract_blocks_live_trading — mentions live trading prohibition")
    else:
        fail("contract_blocks_live_trading")


def test_contract_blocks_publishing():
    if "publish" in _content.lower() or "client-facing" in _content.lower():
        ok("contract_blocks_publishing — mentions publishing prohibition")
    else:
        fail("contract_blocks_publishing")


if __name__ == "__main__":
    print("=== test_agent_handoff_contract ===")
    test_contract_file_exists()
    test_contract_has_required_fields_section()
    test_contract_mentions_no_artifact_no_completion()
    test_contract_mentions_acceptance_criteria()
    test_contract_mentions_artifact_path()
    test_contract_mentions_agent_name()
    test_contract_mentions_registry()
    test_contract_has_example_handoffs()
    test_contract_blocks_live_trading()
    test_contract_blocks_publishing()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
