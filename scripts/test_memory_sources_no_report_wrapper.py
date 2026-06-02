"""
test_memory_sources_no_report_wrapper.py
Verifies that all memory command responses are plain text — no HERMES REPORT wrapper,
no box-drawing characters, no Markdown tables, correct section headers present.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

WRAPPER_PATTERNS = [
    "═══",
    "HERMES REPORT",
    "What Happened:",
    "Action Needed From You:",
    "| --- |",
    "```",
]

MEMORY_COMMANDS = {
    "show memory sources":           ("HERMES MEMORY SOURCES", ["Live answer sources:", "Blocked from live answers:"]),
    "show memory sources again":     ("HERMES MEMORY SOURCES", ["Live answer sources:", "Blocked from live answers:"]),
    "show active operating rules":   ("ACTIVE OPERATING RULES", ["live-answer rules", "Rule"]),
    "where did that answer come from": ("ANSWER SOURCE", ["context"]),
}


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_sources_no_report_wrapper ===\n")

from hermes_command_router.router import run_command

for cmd, (expected_header, expected_sections) in MEMORY_COMMANDS.items():
    print(f"-- '{cmd[:50]}' --")
    result = run_command(cmd, source="telegram")
    check(f"non-empty response", bool(result and result.strip()))

    for pattern in WRAPPER_PATTERNS:
        check(f"no '{pattern[:30]}' wrapper", pattern not in (result or ""))

    check(f"contains '{expected_header}'", expected_header in (result or ""))

    for section in expected_sections:
        check(f"contains section '{section[:40]}'",
              section.lower() in (result or "").lower())

    check(f"response > 80 chars", len(result or "") > 80)
    print()

print("\n-- 'show memory sources again' content matches 'show memory sources' --")
r1 = run_command("show memory sources", source="telegram")
r2 = run_command("show memory sources again", source="telegram")
check("content identical", r1 == r2)
check("no wrapper in 'again' response", "═══" not in (r2 or ""))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
