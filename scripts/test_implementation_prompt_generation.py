"""
test_implementation_prompt_generation.py
Tests: implementation prompt generation returns structured prompt with required sections.
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


print("=== test_implementation_prompt_generation ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import (
    create_implementation_prompt_if_needed,
    _build_implementation_prompt_text,
    build_cfo_context, build_cfo_response, format_cfo_response,
)

# ── Intent classification ─────────────────────────────────────────────────────
print("-- intent classification --")

PROMPT_PHRASES = [
    ("create prompt from this",              "create_implementation_prompt"),
    ("turn this into a claude prompt",       "create_implementation_prompt"),
    ("create implementation prompt",         "create_implementation_prompt"),
    ("give me a prompt for claude",          "create_implementation_prompt"),
    ("what should i send claude",            "create_implementation_prompt"),
    ("create a super prompt",               "create_implementation_prompt"),
]

for phrase, expected in PROMPT_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → {expected}", intent == expected)

# ── _build_implementation_prompt_text structure ───────────────────────────────
print("\n-- _build_implementation_prompt_text structure --")
prompt = _build_implementation_prompt_text("Add CFO conversation layer to Hermes")
check("starts with IMPLEMENTATION PROMPT", prompt.startswith("IMPLEMENTATION PROMPT"))
check("has Goal:", "Goal:" in prompt)
check("has Context:", "Context:" in prompt)
check("has Requirements:", "Requirements:" in prompt)
check("has Safety:", "Safety:" in prompt)
check("has Tests:", "Tests:" in prompt)
check("has Final report:", "Final report:" in prompt)
check("has approval boundary in safety", "approval" in prompt.lower())

# ── create_implementation_prompt_if_needed ────────────────────────────────────
print("\n-- create_implementation_prompt_if_needed --")
PROMPT_MESSAGES = [
    "give me a prompt for claude to fix this",
    "create a super prompt for implementing this",
    "what should I send claude?",
    "turn this into a claude prompt",
    "have opencode fix this",
]
for msg in PROMPT_MESSAGES:
    result = create_implementation_prompt_if_needed(msg, "test recommendation")
    check(f"'{msg[:45]}' → prompt generated",
          result is not None and "IMPLEMENTATION PROMPT" in result)

NON_PROMPT_MESSAGES = [
    "what should we do about revenue?",
    "I am worried about Hermes",
    "show revenue packet",
]
for msg in NON_PROMPT_MESSAGES:
    result = create_implementation_prompt_if_needed(msg, "rec")
    check(f"'{msg[:40]}' → returns None (not a prompt request)", result is None)

# ── CFO response for implementation request ───────────────────────────────────
print("\n-- CFO response for implementation request --")
msg = "give me a prompt for Claude to fix this"
ctx = build_cfo_context(msg)
resp = build_cfo_response(msg, ctx)
fmt = format_cfo_response(resp)
check("implementation response starts with IMPLEMENTATION PROMPT",
      fmt.startswith("IMPLEMENTATION PROMPT"))
check("implementation response has Goal", "Goal:" in fmt)
check("implementation response has Safety", "Safety:" in fmt)

# ── Handler via run_command ───────────────────────────────────────────────────
print("\n-- run_command: create implementation prompt --")
response = run_command("create prompt from this: add cfo layer") or ""
check("handler returns IMPLEMENTATION PROMPT",
      "IMPLEMENTATION PROMPT" in response.upper())
check("prompt has safety section",
      "safety" in response.lower() or "approval" in response.lower())
check("prompt does not assume implementation happened",
      "has been implemented" not in response.lower()
      and "was implemented" not in response.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
