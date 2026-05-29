"""
test_claude_code_work_lookup.py
Verifies "what did claude code work on" reads handoff files, not LLM memory.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_claude_code_work_lookup ===")

from lib.hermes_internal_first import try_internal_first
from pathlib import Path

QUERIES = [
    "what did claude code work on",
    "what did claude work on",
    "what did claude code do",
    "claude code work",
    "show handoffs",
    "recent handoffs",
    "latest handoff",
]

for q in QUERIES:
    result = try_internal_first(q)
    check(f"has internal reply for: {q}", result is not None)
    if result:
        check(f"topic is claude_code_work: {q}", result.matched_topic == "claude_code_work")
        check(f"not LLM source: {q}", "hermes_reasoning_layer" not in result.source)

# If handoff files exist, verify content is from files
handoff_dir = Path(__file__).resolve().parent.parent / "docs" / "reports" / "handoffs"
files = sorted(handoff_dir.glob("claude_code_handoff_*.md"), reverse=True) if handoff_dir.exists() else []
check("handoff directory exists", handoff_dir.exists())
check("has handoff files", len(files) > 0)
if files:
    result = try_internal_first("what did claude code work on")
    check("reply mentions handoffs", result is not None and "handoff" in result.text.lower())
    check("source points to handoff dir", result is not None and "handoff" in result.source.lower())
    check("reply is CONFIRMED confidence", result is not None and result.confidence in {"INTERNAL_CONFIRMED", "INTERNAL_PARTIAL"})

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
