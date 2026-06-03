"""
test_phase7a_cfo_intercepts_before_evidence.py
Phase 7A: CFO layer intercepts natural messages before LLM evidence dump path.
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


print("=== test_phase7a_cfo_intercepts_before_evidence ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import detect_cfo_conversation_need, is_high_priority_cfo_phrase

# ── CFO detection works for natural messages ──────────────────────────────────
print("-- detect_cfo_conversation_need identifies natural messages --")

NATURAL_MESSAGES = [
    "I am worried Hermes is becoming a command bot and not a CFO.",
    "I don't know what ChatGPT has that Hermes doesn't, but I need that logic.",
    "Right now it feels more like a master/dog relationship than a CEO/CFO relationship.",
    "What should we do to make Hermes better?",
    "I'm not sure if we should launch this week.",
]
for msg in NATURAL_MESSAGES:
    check(f"detect_cfo: {msg[:50]!r}",
          detect_cfo_conversation_need(msg.lower()) is True)

# ── High-priority phrase detection ───────────────────────────────────────────
print("\n-- is_high_priority_cfo_phrase catches command-verb messages --")

HIGH_PRIORITY_MESSAGES = [
    "create a prompt for Claude to fix this",
    "create a super prompt for fixing the routing",
    "what should we do about that",
    "can your scouts figure it out",
    "can Hermes find the best affiliate offer",
]
for msg in HIGH_PRIORITY_MESSAGES:
    check(f"high_priority: {msg[:50]!r}",
          is_high_priority_cfo_phrase(msg.lower()) is True)

# ── Command phrases are NOT intercepted by CFO ────────────────────────────────
print("\n-- exact command phrases not intercepted by CFO --")

COMMAND_PHRASES = [
    "show revenue asset packet",
    "run daily operating cycle",
    "show approval queue",
    "rescore after fixes",
    "show research queue",
    "show scout assignments",
]
for cmd in COMMAND_PHRASES:
    check(f"NOT detect_cfo: {cmd[:45]!r}",
          detect_cfo_conversation_need(cmd) is False)
    check(f"NOT high_priority: {cmd[:45]!r}",
          is_high_priority_cfo_phrase(cmd) is False)

# ── CFO responses do not contain evidence dump markers ────────────────────────
print("\n-- CFO responses do not produce evidence dumps --")

EVIDENCE_DUMP_MARKERS = ["Live answer sources:", "Confidence: ", "Source 1:", "Source 2:", "Source: http"]

CFO_TEST_MESSAGES = [
    "I am worried Hermes is becoming a command bot and not a CFO.",
    "can your scouts figure it out?",
]
for msg in CFO_TEST_MESSAGES:
    r = run_command(msg) or ""
    has_dump = any(marker.lower() in r.lower() for marker in EVIDENCE_DUMP_MARKERS)
    check(f"no evidence dump: {msg[:50]!r}", not has_dump)

# ── CFO response headers are clean ───────────────────────────────────────────
print("\n-- CFO responses start with correct headers --")

cfo_strategic = run_command("I am worried Hermes is becoming a command bot.") or ""
check("strategic concern starts with RAY, I UNDERSTAND", cfo_strategic.startswith("RAY, I UNDERSTAND"))

cfo_scout = run_command("I don't know, can your scouts figure it out?") or ""
check("scout dispatch starts with I DON'T HAVE VERIFIED", cfo_scout.startswith("I DON'T HAVE VERIFIED"))

cfo_prompt = run_command("create a prompt for Claude to fix this") or ""
check("impl prompt starts with IMPLEMENTATION PROMPT", cfo_prompt.startswith("IMPLEMENTATION PROMPT"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
