"""
test_memory_classification_rules.py
Verifies that HERMES_MEMORY_CLASSIFICATION_RULES.md exists and contains
all required classification sections.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = ROOT / "docs" / "HERMES_MEMORY_CLASSIFICATION_RULES.md"

PASS = 0; FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")

print("=== test_memory_classification_rules ===\n")

check("HERMES_MEMORY_CLASSIFICATION_RULES.md exists", RULES_FILE.exists())

if RULES_FILE.exists():
    text = RULES_FILE.read_text(encoding="utf-8")

    # ── Required sections ─────────────────────────────────────────────────────
    print("-- Classification sections present --")
    check("has active_live_answer section", "active_live_answer" in text)
    check("has historical_only section", "historical_only" in text)
    check("has deprecated section", "### 3. deprecated" in text or "deprecated" in text)
    check("has blocked_from_live section", "blocked_from_live" in text)
    check("has debug_only section", "debug_only" in text)
    check("has needs_review section", "needs_review" in text)

    # ── Blocked markers enumerated ────────────────────────────────────────────
    print("\n-- Stale defaults listed as blocked --")
    check("Ollama OFFLINE listed as blocked", "Ollama OFFLINE" in text)
    check("Beehiiv pending listed as blocked", "Beehiiv pending" in text)
    check("YouTube Studio pending listed as blocked", "YouTube Studio pending" in text)
    check("OpenRouter listed as blocked", "OpenRouter" in text)
    check("NitroTrades listed as blocked", "NitroTrades" in text)
    check("fake pending counts listed as blocked", "fake" in text.lower() and "pending" in text.lower())
    check("artifact_inventory listed as blocked", "[artifact_inventory]" in text)
    check("revenue_plan listed as blocked", "[revenue_plan]" in text)

    # ── Active sources listed ─────────────────────────────────────────────────
    print("\n-- Active live sources listed --")
    check("current artifact registry listed", "artifact registry" in text.lower())
    check("current action queue listed", "action queue" in text.lower())
    check("current decision log listed", "decision log" in text.lower())
    check("live provider policy listed", "provider policy" in text.lower())

    # ── Enforcement section ───────────────────────────────────────────────────
    print("\n-- Enforcement section --")
    check("enforcement section exists", "Enforcement" in text)
    check("test_memory_classification_blocks_stale referenced", "test_memory_classification_blocks_stale" in text)

    # ── Migration rules ────────────────────────────────────────────────────────
    print("\n-- Migration rules --")
    check("migration rule section exists", "Migration Rule" in text or "hermes_memory_v2" in text)
    check("blocked_from_telegram scope defined", "blocked_from_telegram" in text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
