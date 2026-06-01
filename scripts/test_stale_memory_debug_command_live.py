"""
test_stale_memory_debug_command_live.py
Verifies that "show stale memory debug" response begins with
"STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED FROM LIVE ANSWERS"
and does NOT fall into quality fallback.
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

print("=== test_stale_memory_debug_command_live ===\n")

from hermes_command_router.router import _run_stale_memory_debug, run_command
from hermes_command_router.intake import classify_intent

# ── 1. Handler output must start with warning ─────────────────────────────
status, evidence, rec = _run_stale_memory_debug()
full = "\n".join(evidence)
first_line = evidence[0] if evidence else ""
check("stale debug handler returns healthy", status == "healthy")
check("first line is STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED",
      first_line == "STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED FROM LIVE ANSWERS")
check("mentions explicit request", "explicitly requested debug memory" in full)
check("mentions NEVER injected", "NEVER injected into normal Telegram replies" in full)

# ── 2. Does not fall into quality fallback ────────────────────────────────
check("does not contain 'unable to generate'", "unable to generate" not in full.lower())
check("does not contain 'wasn't able'", "wasn't able" not in full.lower())

# ── 3. Shows blocked stale defaults ───────────────────────────────────────
check("shows Ollama (blocked)", "Ollama" in full or "(BLOCKED)" in full)
check("shows BLOCKED marker", "BLOCKED" in full)

# ── 4. run_command output ─────────────────────────────────────────────────
resp = run_command("show stale memory debug", source="telegram")
check("run_command stale debug contains warning",
      "STALE MEMORY DEBUG" in resp)
check("run_command stale debug no quality fallback",
      "wasn't able to generate" not in resp)

# ── 5. Intent classification ─────────────────────────────────────────────
for phrase in [
    "show stale memory debug",
    "stale memory debug",
    "show blocked memory debug",
    "show deprecated memory debug",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → stale_memory_debug", intent == "stale_memory_debug")

# Non-matching
for phrase in [
    "show memory sources",
    "show archived memory",
    "system health",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' NOT stale_memory_debug", intent != "stale_memory_debug")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
