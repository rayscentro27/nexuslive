"""
test_archived_memory_explicit_only.py
Verifies Rule 5 of the Memory Safety Contract:
  - Archived/debug memory only shown when explicitly requested
  - Every archived/debug response includes a warning label
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

print("=== test_archived_memory_explicit_only ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import _run_archived_executive_memory, _run_stale_memory_debug

# ── Archived memory intents ─────────────────────────────────────────────────
archived_phrases = [
    "show archived memory",
    "show archived defaults",
    "load archived defaults",
    "archived executive memory",
    "what were the old defaults",
    "original defaults",
]
for phrase in archived_phrases:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' classified as archived_executive_memory",
          intent == "archived_executive_memory")

# Non-archived phrases should NOT match
non_archived = [
    "system health",
    "show memory sources",
    "stale memory debug",
]
for phrase in non_archived:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' NOT classified as archived_executive_memory",
          intent != "archived_executive_memory")

# ── Archived memory handler ─────────────────────────────────────────────────
status, evidence, rec = _run_archived_executive_memory()
check("Archived handler returns healthy status", status == "healthy")
check("Archived evidence is a list", isinstance(evidence, list))
check("Archived evidence has content", len(evidence) > 0)
first = evidence[0] if evidence else ""
check("Archived response begins with ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH",
      first == "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH")
check("Archived response mentions ORIGINAL or ARCHIVED",
      any("ORIGINAL" in e or "ARCHIVED" in e for e in evidence))

# ── Stale memory debug handler ─────────────────────────────────────────────
status2, evidence2, rec2 = _run_stale_memory_debug()
check("Stale debug handler returns healthy", status2 == "healthy")
check("Stale debug evidence has content", len(evidence2) > 0)

# Must include warning label
first2 = evidence2[0] if evidence2 else ""
check("Stale debug begins with STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED",
      "STALE MEMORY DEBUG" in first2 and "BLOCKED" in first2)
check("Stale debug mentions explicit request", "explicitly requested debug memory" in " ".join(evidence2))

# Must actually show stale defaults (it's debug mode)
check("Stale debug shows Ollama (archived)",
      "Ollama" in " ".join(evidence2) or "(BLOCKED)" in " ".join(evidence2))

# ── Normal commands must NOT trigger archive ────────────────────────────────
check("Normal query does not trigger archive",
      classify_intent("what is the status")[0] != "archived_executive_memory")
check("Follow-up does not trigger archive",
      classify_intent("show it")[0] != "archived_executive_memory")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
