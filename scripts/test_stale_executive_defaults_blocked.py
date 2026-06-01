"""
test_stale_executive_defaults_blocked.py
Verifies Rules 1 and 2 of the Memory Safety Contract:
  - load_memory() returns empty/neutral, not stale defaults
  - Archived defaults are only accessible via explicit function
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

print("=== test_stale_executive_defaults_blocked ===\n")

from lib.hermes_executive_memory import load_memory, load_archived_executive_memory_defaults

STALE_MARKERS = ["Ollama", "Beehiiv", "OpenRouter", "YouTube Studio"]

mem = load_memory(force_refresh=True)

# Rule 1: load_memory() must not contain stale defaults
for cat in ["infrastructure_problems", "unfinished_systems", "monetization_priorities"]:
    items = mem.get(cat, [])
    for item in items:
        for marker in STALE_MARKERS:
            check(f"No stale '{marker}' in load_memory().{cat}",
                  marker not in str(item))

# Rule 1: categories should be empty lists (no Supabase in test env)
check("infrastructure_problems is empty by default",
      mem.get("infrastructure_problems", []) == [])
check("unfinished_systems is empty by default",
      mem.get("unfinished_systems", []) == [])

# Rule 1: operational_philosophy still present (standing rules, not stale)
check("operational_philosophy has DRY_RUN rule",
      any("DRY_RUN" in str(p) for p in mem.get("operational_philosophy", [])))

# Rule 2: archived defaults exist and are separate
archived = load_archived_executive_memory_defaults()
check("load_archived_executive_memory_defaults exists",
      callable(load_archived_executive_memory_defaults))
check("Archived defaults contain Ollama OFFLINE",
      any("Ollama" in str(i) for i in archived.get("infrastructure_problems", [])))
check("Archived defaults contain Beehiiv pending",
      any("Beehiiv" in str(i) for i in archived.get("unfinished_systems", [])))

# Rule 2: archived defaults must NOT match live
for cat in ["infrastructure_problems", "unfinished_systems"]:
    arch_items = archived.get(cat, [])
    live_items = mem.get(cat, [])
    if arch_items:
        check(f"Archived {cat} differs from live {cat}",
              arch_items != live_items)

# Rule 1: memory source tag
source = mem.get("source", "")
check("Memory source is not archived_defaults",
      source != "archived_defaults")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
