"""
test_archived_memory_warning_live.py
Verifies that "show archived executive memory" response begins with
"ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH".
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

print("=== test_archived_memory_warning_live ===\n")

from hermes_command_router.router import _run_archived_executive_memory, run_command
from hermes_command_router.intake import classify_intent

# ── 1. Handler output must start with warning ─────────────────────────────
status, evidence, rec = _run_archived_executive_memory()
full = "\n".join(evidence)
first_line = evidence[0] if evidence else ""
check("archived handler returns healthy", status == "healthy")
check("first line is ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH",
      first_line == "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH")
check("mentions historical/debug context", "historical/debug context" in full)
check("mentions blocked from normal answers", "blocked from normal Telegram answers" in full)
check("mentions original hardcoded defaults", "ORIGINAL hardcoded defaults" in full)
check("mentions no longer injected", "NO LONGER injected" in full)

# ── 2. Run_command output ─────────────────────────────────────────────────
resp = run_command("show archived executive memory", source="telegram")
check("run_command archived contains warning",
      "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH" in resp)

# ── 3. Intent classification ─────────────────────────────────────────────
for phrase in [
    "show archived memory",
    "show archived executive memory",
    "archived executive memory",
    "show old executive memory",
    "show historical executive memory",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' → archived_executive_memory", intent == "archived_executive_memory")

# Non-matching
for phrase in [
    "show memory sources",
    "memory sources",
    "stale memory debug",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase}' NOT archived_executive_memory", intent != "archived_executive_memory")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
