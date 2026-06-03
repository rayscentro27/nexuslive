"""
test_cfo_conversation_no_evidence_dump.py
Tests: strategic/business messages do not produce evidence dumps.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def is_evidence_dump(text: str) -> bool:
    # Only flag generic fallback dumps (not proper handler responses)
    DUMP_MARKERS = [
        "evidence inventory", "artifact dump", "handoff dump",
        "stale executive memory", "full artifact list",
        "--- evidence ---",
        "Status: unknown",
        "What would you like me to check? Options:",
    ]
    text_str = (text or "")
    return any(m in text_str for m in DUMP_MARKERS)


print("=== test_cfo_conversation_no_evidence_dump ===\n")

from hermes_command_router.router import run_command

# ── Strategic messages should not produce evidence dumps ──────────────────────
print("-- strategic messages avoid evidence dumps --")

STRATEGIC_MESSAGES = [
    "I am worried Hermes is becoming a command bot and not a CFO",
    "What should we do about making more money this month?",
    "I don't know what ChatGPT has that Hermes doesn't but I need that logic",
    "Right now it feels like a master/dog relationship instead of CEO/CFO",
    "How do we get to $1000 a week?",
    "Can you find the best affiliate offer for the funding checklist?",
]

for msg in STRATEGIC_MESSAGES:
    try:
        response = run_command(msg)
        check(f"'{msg[:50]}...' not evidence dump", not is_evidence_dump(response))
        check(f"'{msg[:50]}...' non-empty response", len((response or "").strip()) > 20)
    except Exception as exc:
        check(f"'{msg[:50]}...' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── Phase 7 commands don't produce evidence dumps ────────────────────────────
print("\n-- Phase 7 commands avoid evidence dumps --")

PHASE7_COMMANDS = [
    "show research queue",
    "show scout assignments",
    "what are you still trying to figure out",
    "show unresolved questions",
]

for cmd in PHASE7_COMMANDS:
    try:
        response = run_command(cmd)
        check(f"'{cmd}' not evidence dump", not is_evidence_dump(response))
    except Exception as exc:
        check(f"'{cmd}' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── CFO response doesn't have evidence dump markers ──────────────────────────
print("\n-- CFO response format check --")

from lib.hermes_cfo_conversation_layer import build_cfo_context, build_cfo_response, format_cfo_response

msg = "I am worried Hermes is becoming a command bot"
ctx = build_cfo_context(msg)
resp = build_cfo_response(msg, ctx)
fmt = format_cfo_response(resp)

check("CFO response not evidence dump", not is_evidence_dump(fmt))
check("CFO response starts with RAY or I DON'T",
      fmt.startswith("RAY") or fmt.startswith("I DON'T"))
check("CFO response does not start with 'HERMES REPORT'",
      not fmt.startswith("HERMES REPORT"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
