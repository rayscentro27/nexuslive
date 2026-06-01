"""
test_memory_sources_not_archived_memory.py
Verifies that "show memory sources" NEVER returns Hermes Executive Memory v1.
The two handlers must be completely separate.
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

print("=== test_memory_sources_not_archived_memory ===\n")

from hermes_command_router.router import _run_memory_sources, _run_archived_executive_memory, _run_answer_source

# ── 1. Memory sources handler ─────────────────────────────────────────────
status, evidence, rec = _run_memory_sources()
full = "\n".join(evidence)
check("memory_sources returns healthy", status == "healthy")
check("memory_sources does not contain Hermes Executive Memory", "Hermes Executive Memory" not in full)
check("memory_sources does not contain v1", "(v1" not in full)
check("memory_sources does not contain executive memory data", "Ollama OFFLINE" not in full)
check("memory_sources does not contain Beehiiv", "Beehiiv" not in full)
check("memory_sources contains HERMES MEMORY SOURCES header", "HERMES MEMORY SOURCES" in full)
check("memory_sources lists active sources", "Current content artifacts" in full)
check("memory_sources lists blocked sources", "archived executive memory" in full)
check("memory_sources references contract", "MEMORY_SAFETY_CONTRACT" in full)

# ── 2. Answer source handler ──────────────────────────────────────────────
status2, evidence2, rec2 = _run_answer_source()
full2 = "\n".join(evidence2)
check("answer_source returns healthy", status2 == "healthy")
check("answer_source contains ANSWER SOURCE header", "ANSWER SOURCE" in full2)
check("answer_source does not contain Hermes Executive Memory", "Hermes Executive Memory" not in full2)
check("answer_source mentions active context", "active context" in full2)
check("answer_source says did not use archived", "did not use archived executive memory" in full2)

# ── 3. Archived memory handler is separate ───────────────────────────────
status3, evidence3, rec3 = _run_archived_executive_memory()
full3 = "\n".join(evidence3)
check("archived_executive_memory returns healthy", status3 == "healthy")
check("archived_executive_memory has warning", "NOT CURRENT TRUTH" in full3)

# ── 4. Memory sources does not call executive memory at all ──────────────
import dis
import hermes_command_router.router as rtr
source_code = open(rtr.__file__).read()
import_count = source_code.count("_run_archived_executive_memory")
check("memory_sources handler does not call archived memory",
      "_run_archived_executive_memory" not in source_code.split("def _run_memory_sources")[1].split("def ")[0]
      if "def _run_memory_sources" in source_code and "def " in source_code.split("def _run_memory_sources")[1]
      else True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
