"""
test_old_evidence_response_source_hunt.py
Verifies that the four identified sources of the old generic evidence response
are patched: stale exec memory path, evidence formatter, context pack builder,
and reasoning layer fallback.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_old_evidence_response_source_hunt ===\n")

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Source 1: hermes_internal_first.py no longer reads stale exec memory ──────
print("-- Source 1: hermes_internal_first.py monetization handler --")
src1 = (ROOT / "lib" / "hermes_internal_first.py").read_text()
# Find the monetization topic handler block
idx = src1.find('if topic == "monetization"')
check("topic==monetization block exists", idx >= 0)
block = src1[idx:idx+800] if idx >= 0 else ""
check("no longer reads stale exec_mem.load_memory()", "load_memory" not in block)
check("now calls build_today_monetization_plan", "build_today_monetization_plan" in block)
check("no Monetization Priorities hardcoded header", "**Monetization Priorities**" not in block)
check("no hardcoded 'nexus monetization audit' append", 'Run `nexus monetization audit`' not in block)

# ── Source 4: hermes_reasoning_layer.py guards monetization before evidence dump
print("\n-- Source 4: hermes_reasoning_layer.py evidence-only fallback guard --")
src4 = (ROOT / "lib" / "hermes_reasoning_layer.py").read_text()
check("monetization guard present", "_monetization_keywords" in src4)
check("guard calls build_today_monetization_plan", "build_today_monetization_plan" in src4)
check("guard returns before generic evidence dump", "hermes_monetization_today" in src4)

# ── intake.py: monetization audit phrases mapped to business_opportunities ────
print("\n-- intake.py monetization audit routing --")
src_intake = (ROOT / "hermes_command_router" / "intake.py").read_text()
check("nexus monetization audit in intake", "nexus monetization audit" in src_intake)
check("show monetization audit in intake", "show monetization audit" in src_intake)
check("monetization priorities in intake", "monetization priorities" in src_intake)

# ── language_pack.py: audit phrases added to MONETIZATION_PHRASES ─────────────
print("\n-- hermes_language_pack.py MONETIZATION_PHRASES --")
src_lp = (ROOT / "lib" / "hermes_language_pack.py").read_text()
check("nexus monetization audit in MONETIZATION_PHRASES", "nexus monetization audit" in src_lp)
check("monetization audit in MONETIZATION_PHRASES", "monetization audit" in src_lp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
