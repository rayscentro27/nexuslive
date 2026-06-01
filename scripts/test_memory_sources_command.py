"""
test_memory_sources_command.py
Verifies the 'show memory sources' command returns plain-language source list.
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

print("=== test_memory_sources_command ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import _run_memory_sources

# ── Intent classification ──────────────────────────────────────────────────
source_phrases = [
    "show memory sources",
    "memory sources",
    "what memory sources",
    "what are your memory sources",
    "where does your memory come from",
]
for phrase in source_phrases:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' classified as memory_sources",
          intent == "memory_sources")

# "where did that answer come from" is now answer_source, not memory_sources
answer_intent, _, _ = classify_intent("where did that answer come from")
check("'where did that answer come from' is answer_source",
      answer_intent == "answer_source")

# Non-matching phrases
non_matches = [
    "system health",
    "show archived memory",
    "show debug memory",
    "cite source",
    "answer source",
]
for phrase in non_matches:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' NOT classified as memory_sources",
          intent != "memory_sources")

# ── Router handler ─────────────────────────────────────────────────────────
status, evidence, rec = _run_memory_sources()
check("Memory sources handler returns healthy", status == "healthy")
check("Memory sources evidence is a list", isinstance(evidence, list))
check("Memory sources evidence has content", len(evidence) > 0)

combined = "\n".join(evidence)
check("Contains HERMES MEMORY SOURCES header", "HERMES MEMORY SOURCES" in combined)
check("Lists active live-answer sources", "Current conversation context" in combined or "Latest content artifact" in combined)
check("Lists NOT used sources", "archived executive memory" in combined)
check("Does not dump stale data", "Ollama" not in combined)
check("Does not dump raw config", "SUPABASE_URL" not in combined)
check("References contract doc", "MEMORY_SAFETY_CONTRACT" in combined)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
