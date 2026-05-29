"""
test_core_nexus_project_brief.py
Verifies "what is nexus" returns the project brief, not LLM hallucination.
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

print("=== test_core_nexus_project_brief ===")

from lib.hermes_internal_first import try_internal_first
from pathlib import Path

QUERIES = [
    "what is nexus",
    "what is the nexus project",
    "nexus overview",
    "tell me about nexus",
    "nexus mission",
]

for q in QUERIES:
    result = try_internal_first(q)
    check(f"has internal reply for: {q}", result is not None)
    if result:
        check(f"reply mentions Ray or mission: {q}", "ray" in result.text.lower() or "mission" in result.text.lower() or "revenue" in result.text.lower())
        check(f"topic is nexus_project: {q}", result.matched_topic == "nexus_project")
        check(f"not LLM-generated: {q}", "hermes_reasoning_layer" not in result.source)

# Brief file itself
brief = Path(__file__).resolve().parent.parent / "docs" / "reports" / "core" / "nexus_project_brief.md"
check("brief file exists on disk", brief.exists())
if brief.exists():
    content = brief.read_text()
    check("brief contains mission statement", "mission" in content.lower() or "$1,000" in content)
    check("brief contains safety model", "DRY_RUN" in content or "dry_run" in content.lower())
    check("brief is non-trivial", len(content) > 500)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
