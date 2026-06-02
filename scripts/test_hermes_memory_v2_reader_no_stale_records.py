"""
test_hermes_memory_v2_reader_no_stale_records.py
Verifies that the v2 reader and preview commands never surface stale markers,
raw payloads, provider snapshots, or executive_briefings as current truth.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0

STALE_MARKERS = [
    "Ollama OFFLINE", "Beehiiv pending", "YouTube Studio pending",
    "OpenRouter not configured", "Executive Memory — as of",
    "Quality escalation fallback", "NitroTrades fabricated status",
    "fake pending approvals",
]

FORBIDDEN_RESPONSE_PATTERNS = [
    "[artifact_inventory]",
    "[handoff]",
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "═══",
    "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_reader_no_stale_records ===\n")

from hermes_command_router.router import run_command, _PLAIN_INTENTS
import lib.hermes_memory_v2_reader as v2

print("-- _STALE_MARKERS defined in v2 reader --")
for m in STALE_MARKERS[:4]:
    check(f"v2 reader knows stale marker '{m[:30]}'",
          any(m.lower() in s.lower() for s in v2._STALE_MARKERS))

print("\n-- v2 preview command responses contain no stale markers --")
preview_commands = [
    "show memory v2 preview",
    "show memory v2 status",
    "show memory v2 rules",
    "compare memory v2",
]
for cmd in preview_commands:
    result = run_command(cmd, source="telegram") or ""
    for marker in STALE_MARKERS:
        check(f"'{cmd[:35]}' — no '{marker[:30]}'", marker not in result)
    for pattern in FORBIDDEN_RESPONSE_PATTERNS:
        check(f"'{cmd[:35]}' — no forbidden '{pattern[:25]}'", pattern not in result)
    print()

print("-- v2 preview commands say preview only / not primary --")
for cmd in ["show memory v2 preview", "show memory v2 status"]:
    result = run_command(cmd, source="telegram") or ""
    check(f"'{cmd[:35]}' contains 'preview'", "preview" in result.lower() or "Preview" in result)
    check(f"'{cmd[:35]}' does not say 'live primary reader'",
          "live primary" not in result.lower() or
          ("not" in result.lower() and "primary" in result.lower()))

print("\n-- explain_v2_reader_status contains no stale markers --")
status = v2.explain_v2_reader_status()
for m in STALE_MARKERS:
    check(f"status text — no '{m[:30]}'", m not in status)

print("\n-- build_v2_memory_context_pack returns no raw payload --")
pack = v2.build_v2_memory_context_pack()
pack_str = str(pack)
check("no 'secret_key' in pack", "secret_key" not in pack_str.lower())
check("no 'api_token' in pack", "api_token" not in pack_str.lower())
check("no 'eyJ' (JWT) in pack", "eyJ" not in pack_str)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
