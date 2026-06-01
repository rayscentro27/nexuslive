"""
test_memory_safety_contract_exists.py
Verifies the Memory Safety Contract document exists with all 4 required categories.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_memory_safety_contract_exists ===\n")

contract_path = ROOT / "docs" / "HERMES_MEMORY_SAFETY_CONTRACT.md"
check("Contract file exists", contract_path.exists())

if contract_path.exists():
    text = contract_path.read_text()
    check("Contains Live Answer Memory section", "### 1. Live Answer Memory" in text)
    check("Contains Historical Memory section", "### 2. Historical Memory" in text)
    check("Contains Deprecated Memory section", "### 3. Deprecated Memory" in text)
    check("Contains Debug Memory section", "### 4. Debug Memory" in text)
    check("Contains Core Rule", "Normal Telegram answers must not use hardcoded stale" in text)
    check("Contains Rule 1", "### Rule 1" in text and "No stale defaults in live paths" in text)
    check("Contains Rule 2", "### Rule 2" in text and "Archived defaults exist for reference" in text)
    check("Contains Rule 3", "### Rule 3" in text and "Active Memory Reader is the single entry point" in text)
    check("Contains Rule 4", "### Rule 4" in text and "Quality escalation never dumps stale" in text)
    check("Contains Rule 5", "### Rule 5" in text and "Historical and debug memory require explicit opt-in" in text)
    check("Contains Rule 6", "### Rule 6" in text and "Every memory write logs source" in text)
    check("Contains Ollama OFFLINE in deprecated list", "Ollama OFFLINE" in text)
    check("Contains Beehiiv pending in deprecated list", "Beehiiv pending" in text)
    check("Contains OpenRouter not configured in deprecated list", "OpenRouter not configured" in text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
