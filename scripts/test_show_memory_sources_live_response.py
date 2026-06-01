"""
test_show_memory_sources_live_response.py
Verifies the exact content of the show memory sources response.
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

print("=== test_show_memory_sources_live_response ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command, _run_memory_sources

# ── 1. Classify intent ─────────────────────────────────────────────────────
for phrase in [
    "show memory sources", "memory sources", "what memory sources",
    "what are your memory sources", "where does your memory come from",
    "where do you get memory from", "what memory do you use",
    "what sources do you use", "show your memory sources",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → memory_sources", intent == "memory_sources")

# ── 2. Handler content ─────────────────────────────────────────────────────
status, evidence, rec = _run_memory_sources()
full = "\n".join(evidence)
check("status is healthy", status == "healthy")
check("header: HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in full)
check("live: Current conversation context", "Current conversation context" in full)
check("live: Latest content artifact", "Latest content artifact" in full)
check("live: Action queue", "Action queue" in full)
check("live: Decision log", "Decision log" in full)
check("live: Source intake registry", "Source intake registry" in full)
check("live: Daily research review", "Daily research review" in full)
check("live: Active operating rules", "Active operating rules" in full)
check("live: Live provider policy", "Live provider policy" in full)
check("section: Historical/debug sources", "Historical/debug sources" in full)
check("historical: archived executive memory listed", "archived executive memory" in full)
check("historical: stale memory debug listed", "stale memory debug" in full)
check("section: Blocked from live answers", "Blocked from live answers" in full)
check("blocked: old Executive Memory defaults", "old Executive Memory defaults" in full)
check("blocked: stale provider status", "stale provider status" in full)
check("blocked: old Beehiiv/YouTube/OpenRouter defaults", "old Beehiiv" in full)
check("blocked: quality escalation fallback dumps", "quality escalation fallback" in full)
check("evidence: MEMORY_SAFETY_CONTRACT", "MEMORY_SAFETY_CONTRACT" in full)

# ── 3. No stale data in response ───────────────────────────────────────────
bad = [
    "Hermes Executive Memory (v1", "Monetization Priorities",
    "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "OFFLINE",
]
for marker in bad:
    check(f"no stale marker: {marker!r}", marker not in full)

# ── 4. full run_command roundtrip ─────────────────────────────────────────
resp = run_command("show memory sources", source="telegram")
check("run_command has HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in resp)
check("run_command no Hermes Executive Memory v1", "Hermes Executive Memory (v1" not in resp)
check("run_command no ARCHIVED EXECUTIVE MEMORY header", "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH" not in resp)
check("run_command has Blocked from live answers", "Blocked from live answers" in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
