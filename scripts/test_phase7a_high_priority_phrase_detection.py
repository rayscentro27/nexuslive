"""
test_phase7a_high_priority_phrase_detection.py
Phase 7A: is_high_priority_cfo_phrase correctly identifies high-priority CFO messages
          and does not intercept unrelated commands.
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


print("=== test_phase7a_high_priority_phrase_detection ===\n")

from lib.hermes_cfo_conversation_layer import is_high_priority_cfo_phrase, _HIGH_PRIORITY_CFO_PHRASES

# ── _HIGH_PRIORITY_CFO_PHRASES list is populated ─────────────────────────────
print("-- _HIGH_PRIORITY_CFO_PHRASES list --")
check("list is non-empty", len(_HIGH_PRIORITY_CFO_PHRASES) > 0)
check("contains 'create a prompt for claude'", "create a prompt for claude" in _HIGH_PRIORITY_CFO_PHRASES)
check("contains 'can your scouts'", "can your scouts" in _HIGH_PRIORITY_CFO_PHRASES)
check("contains 'command bot'", "command bot" in _HIGH_PRIORITY_CFO_PHRASES)
check("contains 'what should we do about that'", "what should we do about that" in _HIGH_PRIORITY_CFO_PHRASES)

# ── High-priority phrases correctly detected ──────────────────────────────────
print("\n-- is_high_priority_cfo_phrase detects high-priority messages --")
HIGH = [
    "I am worried Hermes is becoming a command bot and not a CFO.",
    "Right now it feels more like a master/dog relationship.",
    "What should we do about that?",
    "I don't know, can your scouts figure it out?",
    "Can Hermes find the best affiliate offer?",
    "create a prompt for Claude to fix this",
    "create a super prompt for the routing fix",
    "give me a prompt for Claude to build this",
    "What should I send Claude about this?",
]
for msg in HIGH:
    check(f"is_high_priority: {msg[:55]!r}",
          is_high_priority_cfo_phrase(msg.lower()) is True)

# ── Non-CFO commands NOT detected as high priority ────────────────────────────
print("\n-- is_high_priority_cfo_phrase does NOT intercept unrelated commands --")
NOT_HIGH = [
    "show revenue asset packet",
    "run daily operating cycle",
    "show approval queue",
    "rescore after fixes",
    "show research queue",
    "show scout assignments",
    "what are you still trying to figure out",
    "show memory v2 primary status",
    "record this lesson: be more concise",
    "approve all pending lessons",
    "show pending approvals",
]
for msg in NOT_HIGH:
    check(f"NOT is_high_priority: {msg[:55]!r}",
          is_high_priority_cfo_phrase(msg.lower()) is False)

# ── Empty and short messages ──────────────────────────────────────────────────
print("\n-- edge cases --")
check("empty string not high priority", is_high_priority_cfo_phrase("") is False)
check("single word not high priority", is_high_priority_cfo_phrase("help") is False)
check("unrelated long message not high priority",
      is_high_priority_cfo_phrase("what is today's date and time?") is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
