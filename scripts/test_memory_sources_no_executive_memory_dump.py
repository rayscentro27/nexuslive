"""
test_memory_sources_no_executive_memory_dump.py
Ensures show memory sources never returns executive memory dump or stale defaults.
All four memory commands remain independently correct.
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

print("=== test_memory_sources_no_executive_memory_dump ===\n")

from hermes_command_router.router import run_command

STALE_MARKERS = [
    "Hermes Executive Memory (v1",
    "Monetization Priorities",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "Launch Nexus AI affiliate",
    "strategic context from evidence",
    "i can answer from verified artifacts",
    "artifact_inventory",
]

# ── show memory sources must never contain stale data ────────────────────
resp_ms = run_command("show memory sources", source="telegram")
for marker in STALE_MARKERS:
    check(f"memory sources: no stale marker {marker!r}", marker not in resp_ms)
check("memory sources: has HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in resp_ms)
check("memory sources: has Blocked from live answers", "Blocked from live answers" in resp_ms)
check("memory sources: no ARCHIVED header", "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH" not in resp_ms)

# ── archived executive memory still works and has its own content ─────────
resp_arch = run_command("show archived executive memory", source="telegram")
check("archived: has ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH", "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH" in resp_arch)
check("archived: different response from memory sources", resp_arch != resp_ms)

# ── stale memory debug still works ────────────────────────────────────────
resp_dbg = run_command("show stale memory debug", source="telegram")
check("stale debug: has STALE MEMORY DEBUG", "STALE MEMORY DEBUG" in resp_dbg)
check("stale debug: different response from memory sources", resp_dbg != resp_ms)

# ── answer source still works ─────────────────────────────────────────────
resp_ans = run_command("where did that answer come from", source="telegram")
check("answer source: has ANSWER SOURCE", "ANSWER SOURCE" in resp_ans)
check("answer source: different response from memory sources", resp_ans != resp_ms)

# ── memory sources phrasing variants all return same handler ─────────────
from hermes_command_router.intake import classify_intent
variants = [
    "show memory sources", "memory sources", "what memory sources",
    "what are your memory sources", "where do you get memory from",
]
for phrase in variants:
    intent, _, _ = classify_intent(phrase)
    check(f"variant '{phrase}' → memory_sources", intent == "memory_sources")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
