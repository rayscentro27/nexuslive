"""
test_quality_fallback_no_stale_memory.py
Verifies Rule 4 of the Memory Safety Contract:
  - Quality escalation fallback returns clean clarification
  - Never dumps stale executive memory
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

print("=== test_quality_fallback_no_stale_memory ===\n")

from lib.hermes_response_quality import _fallback_data_block, quality_check, escalate

STALE_EXEC = (
    "Ollama (netcup, localhost:11555) — OFFLINE\n"
    "Beehiiv newsletter — login session pending\n"
    "YouTube Studio — 6 profile links not yet added manually\n"
    "OpenRouter as content-tier provider — not yet in model_routing_rules\n"
)

# Test 1: Non-follow-up message must not dump stale data
result = _fallback_data_block("something totally random test here", STALE_EXEC)
check("Non-follow-up fallback does not contain Ollama", "Ollama" not in result)
check("Non-follow-up fallback does not contain Beehiiv", "Beehiiv" not in result)
check("Non-follow-up fallback does not contain OpenRouter", "OpenRouter" not in result)
check("Non-follow-up fallback is actionable",
      "specific question" in result.lower() or "nexus ceo briefing" in result.lower())
check("Non-follow-up fallback does NOT contain 'Quality escalation fallback'",
      "Quality escalation fallback" not in result)
check("Non-follow-up fallback does NOT contain 'Executive Memory'",
      "Executive Memory" not in result)

# Test 2: Follow-up messages must route to context resolver
result_fu = _fallback_data_block("show it", STALE_EXEC)
check("Follow-up 'show it' does not contain Ollama", "Ollama" not in result_fu)
check("Follow-up 'show it' does not contain Beehiiv", "Beehiiv" not in result_fu)
check("Follow-up 'show it' returns clarification", len(result_fu) > 5)

result_rec = _fallback_data_block("what do you recommend", STALE_EXEC)
check("Follow-up 'what do you recommend' no stale", "Ollama" not in result_rec)

result_status = _fallback_data_block("what is its status", STALE_EXEC)
check("Follow-up 'what is its status' no stale", "Ollama" not in result_status)

# Test 3: quality_check on clean text
clean = quality_check("The system is healthy. 3 workers active, 0 failures.", chat_id="test_q")
check("Quality check passes on clean operational text", not clean.flagged or clean.score > 0.5)

# Test 4: escalate() uses active memory reader (not stale defaults)
from lib.hermes_active_memory_reader import load_active_memory
active = load_active_memory(force_refresh=True)
check("escalate() context source is not archived",
      active.get("source") != "archived_defaults")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
