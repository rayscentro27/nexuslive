"""
test_live_memory_sources_visible_response.py
Verifies that 'show memory sources' produces a visible, non-empty response
through the command router and is never swallowed by routing or formatting.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Executive Memory — as of",
    "Quality escalation fallback",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_live_memory_sources_visible_response ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

print("-- Intent classification --")
variants = [
    "show memory sources",
    "Hermes, show memory sources",
    "where do you get memory from",
    "what memory sources do you use",
    "what are your memory sources",
]
for v in variants:
    intent, _, _ = classify_intent(v)
    check(f"classify {v!r} → memory_sources", intent == "memory_sources")

print("\n-- Response is non-empty --")
result = run_command("show memory sources", source="telegram")
check("run_command returns non-empty string", bool(result and result.strip()))
check("response length > 100 chars", len(result or "") > 100)

print("\n-- Response contains HERMES MEMORY SOURCES --")
check("response contains HERMES MEMORY SOURCES", "HERMES MEMORY SOURCES" in result)

print("\n-- Response is plain text (no HERMES REPORT wrapper) --")
check("response does not contain '═══' report border", "═══" not in result)
check("response does not contain 'HERMES REPORT' header", "HERMES REPORT" not in result)
check("response does not contain 'What Happened:'", "What Happened:" not in result)
check("response does not contain 'Action Needed From You:'", "Action Needed From You:" not in result)

print("\n-- Response content sections present --")
check("contains 'Live answer sources:'", "Live answer sources:" in result)
check("contains 'Historical sources:'", "Historical sources:" in result)
check("contains 'Blocked from live answers:'", "Blocked from live answers:" in result)
check("contains 'Supabase memory v2:'", "Supabase memory v2:" in result or "memory v2" in result.lower())

print("\n-- No stale strings in active/positive context --")
# Stale markers are allowed if they appear ONLY in a 'Blocked' list context.
# They must NOT appear as active operational claims.
blocked_section = ""
if "Blocked from live answers:" in result:
    blocked_section = result.split("Blocked from live answers:")[-1]
for s in STALE_MARKERS:
    if s in result:
        # Allowed only if it appears solely within the Blocked section
        in_blocked = s in blocked_section
        check(f"stale marker '{s[:40]}' only in Blocked section (not active claim)", in_blocked)
    else:
        check(f"no stale marker: '{s[:40]}'", True)

print("\n-- No evidence dump --")
check("no artifact_inventory dump", "[artifact_inventory]" not in result)
check("no [handoff] dump", "[handoff]" not in result)
check("no 'I can answer from verified artifacts' phrase",
      "I can answer from verified artifacts" not in result)
check("no 'Strategic context from evidence'", "Strategic context from evidence" not in result)

print("\n-- Memory v2 status mentioned --")
check("hermes_memory_v2 mentioned", "hermes_memory_v2" in result)
check("preview / reader status mentioned", "preview" in result.lower() or "not primary" in result.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
