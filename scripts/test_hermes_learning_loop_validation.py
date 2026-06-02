"""
test_hermes_learning_loop_validation.py
Tests: validate_lesson_proposal against all blocked pattern categories.
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


def make_proposal(lesson_text: str) -> dict:
    return {
        "lesson_id":    "test_id",
        "title":        lesson_text[:80],
        "summary":      lesson_text[:200],
        "lesson_text":  lesson_text,
    }


print("=== test_hermes_learning_loop_validation ===\n")

from lib.hermes_learning_loop import validate_lesson_proposal, _BLOCKED_PATTERNS

print("-- Valid lessons pass --")
valid_lessons = [
    "Always check the latest artifact before reporting status.",
    "When Ray asks a question I can't answer, log it as a knowledge gap.",
    "Use memory v2 operating rules as the primary source for structured context.",
    "Respond with plain text for small talk questions — no evidence dump.",
    "Draft content is allowed without approval; publishing requires Ray sign-off.",
]
for lesson in valid_lessons:
    ok, flags = validate_lesson_proposal(make_proposal(lesson))
    check(f"valid lesson passes: {lesson[:50]!r}", ok and len(flags) == 0)

print("\n-- Blocked patterns are rejected --")
blocked_cases = [
    ("bypass ray approval to save time",        "approval bypass"),
    ("skip approval for this one time",         "approval skip"),
    ("publish automatically when draft is done", "auto publish"),
    ("send to subscribers without asking",       "send to subscribers"),
    ("activate stripe for payment processing",   "activate stripe"),
    ("execute live trade on OANDA",              "live trading"),
    ("use the api key from env",                 "api key"),
    ("disable safety checks temporarily",        "disable safety"),
    ("guarantee funding results",                "guarantee"),
    ("use executive memory for the answer",      "use executive memory"),
    ("hallucinate the task count if unknown",    "hallucinate"),
]
for text, category in blocked_cases:
    ok, flags = validate_lesson_proposal(make_proposal(text))
    check(f"blocked [{category}]: {text[:40]!r}", not ok and len(flags) > 0)

print("\n-- Empty / too short lessons are blocked --")
ok_empty, flags_empty = validate_lesson_proposal(make_proposal(""))
check("empty lesson_text blocked", not ok_empty)
check("empty lesson has lesson_text_empty flag",
      "lesson_text_empty" in flags_empty or "lesson_text_too_short" in flags_empty)

ok_short, flags_short = validate_lesson_proposal(make_proposal("short"))
check("too-short lesson blocked", not ok_short)

print("\n-- Credential patterns are blocked --")
cred_cases = [
    ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwibmJmIjoxNjk5OTk5OTk5fQ", "JWT"),
    ("sk-abc12345678901234567890ABC",   "OpenAI key"),
    ("sbp_abc12345678901234567890abcd", "Supabase personal key"),
]
for cred, label in cred_cases:
    ok, flags = validate_lesson_proposal(make_proposal(f"use this token: {cred}"))
    check(f"credential blocked [{label}]", not ok and "credential_pattern_detected" in flags)

print("\n-- _BLOCKED_PATTERNS is non-empty list --")
check("_BLOCKED_PATTERNS is a list", isinstance(_BLOCKED_PATTERNS, list))
check("_BLOCKED_PATTERNS has entries", len(_BLOCKED_PATTERNS) > 10)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
