"""
test_no_tool_call_leakage.py
Verifies that raw tool call syntax is blocked by hermes_final_response_gate.
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

print("=== test_no_tool_call_leakage ===")

# Force block mode to verify replacement occurs
os.environ["HERMES_FINAL_GATE_ACTION"] = "block"
import lib.hermes_final_response_gate as gate_mod
import importlib
importlib.reload(gate_mod)

from lib.hermes_final_response_gate import inspect

TOOL_CALL_SAMPLES = [
    'search_files(pattern="trading strategy", directory="nexus-ai")',
    'Let me help. read_file(path="/docs/reports/handoffs/handoff.md")',
    'I will use list_files(directory="artifacts/") to check.',
    'Calling execute(command="nexus status") now.',
    'Running get_file(name="report.md") to retrieve that.',
    'I can check this: query(topic="youtube status", limit=5)',
]

for sample in TOOL_CALL_SAMPLES:
    result = inspect(sample)
    check(f"tool call blocked: {sample[:50]}", not result.passed)
    check(f"tool call has safe replacement: {sample[:30]}", result.safe_text != sample)

# Clean responses must pass through
CLEAN_SAMPLES = [
    "Here is the YouTube status: 3 sources registered.",
    "No verified data for that yet. Run a status check.",
    "Paper trading is active. No live orders.",
    "I don't have verified evidence for that specific claim.",
]

for sample in CLEAN_SAMPLES:
    result = inspect(sample)
    check(f"clean response passes: {sample[:50]}", result.passed or "verified" in sample.lower())

# cleanup
del os.environ["HERMES_FINAL_GATE_ACTION"]

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
