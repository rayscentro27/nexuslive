"""
test_cfo_routing_priority.py
Tests: CFO layer runs after exact command handlers, not before.
       Existing commands still work.
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


print("=== test_cfo_routing_priority ===\n")

from hermes_command_router.router import run_command

# ── Exact commands produce their own headers (not CFO) ────────────────────────
print("-- exact commands still work --")

EXACT_CMD_MAP = {
    "show revenue asset packet":        "REVENUE ASSET PACKET",
    "run daily operating cycle":        "NEXUS PLAN",
    "show approval queue":              "APPROVAL QUEUE",
    "rescore after fixes":              "REVENUE PACKET RESCORED",
    "show research queue":              "RESEARCH QUEUE",
    "show scout assignments":           "SCOUT ASSIGNMENTS",
}

for cmd, expected_header in EXACT_CMD_MAP.items():
    try:
        response = run_command(cmd) or ""
        check(f"'{cmd[:45]}' has '{expected_header}' header",
              expected_header.upper() in response.upper())
    except Exception as exc:
        check(f"'{cmd[:45]}' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── Exact commands do NOT produce CFO "RAY, I UNDERSTAND" header ─────────────
print("\n-- exact commands not intercepted by CFO layer --")

EXACT_CMDS = [
    "show revenue asset packet",
    "run daily operating cycle",
    "show approval queue",
]

for cmd in EXACT_CMDS:
    try:
        response = run_command(cmd) or ""
        check(f"'{cmd[:45]}' not intercepted by CFO",
              not response.startswith("RAY, I UNDERSTAND"))
    except Exception as exc:
        check(f"'{cmd[:45]}' did not raise", False)

# ── CFO layer activates for natural/strategic messages ───────────────────────
print("\n-- CFO layer activates for natural messages --")

NATURAL_MESSAGES = [
    "I am worried Hermes is becoming a command bot",
    "I don't know what ChatGPT has that Hermes doesn't but I need that logic",
]

for msg in NATURAL_MESSAGES:
    try:
        response = run_command(msg) or ""
        is_cfo = (
            response.startswith("RAY, I UNDERSTAND")
            or response.startswith("I DON'T HAVE VERIFIED")
            or response.startswith("IMPLEMENTATION PROMPT")
        )
        check(f"'{msg[:45]}...' → CFO response", is_cfo)
    except Exception as exc:
        check(f"'{msg[:45]}...' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── CFO does not intercept small exact commands ───────────────────────────────
print("\n-- CFO does not intercept small commands --")
from lib.hermes_cfo_conversation_layer import detect_cfo_conversation_need

short_commands = [
    "show revenue asset packet",
    "run daily operating cycle",
    "rescore after fixes",
    "show approval queue",
    "build revenue asset packet",
]
for cmd in short_commands:
    check(f"detect_cfo_need('{cmd[:40]}') == False",
          detect_cfo_conversation_need(cmd) is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
