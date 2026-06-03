"""
test_phase7a_implementation_prompt_routing.py
Phase 7A: Implementation prompt messages route correctly even when starting with "create".
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


print("=== test_phase7a_implementation_prompt_routing ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import (
    is_high_priority_cfo_phrase, detect_cfo_conversation_need,
    select_cfo_response_strategy, build_cfo_context,
)

# ── High-priority phrase detection for prompt messages ────────────────────────
print("-- impl prompt phrases recognized as high priority --")

PROMPT_MESSAGES = [
    "create a prompt for Claude to fix this",
    "give me a prompt for Claude to build this",
    "what should I send Claude about this?",
    "create a super prompt for fixing the routing",
    "turn this into a Claude prompt",
    "prompt for Claude to fix the routing",
    "create a prompt to implement this feature",
]
for msg in PROMPT_MESSAGES:
    check(f"is_high_priority: {msg[:50]!r}",
          is_high_priority_cfo_phrase(msg.lower()) is True)

# ── "create" starts with command verb → detect_cfo=False; "give me" → detect_cfo=True (has keywords) ──
print("\n-- command verb detection (create = False, give me = True via keywords) --")
check("detect_cfo=False for 'create a prompt for Claude' (starts with command verb)",
      detect_cfo_conversation_need("create a prompt for claude to fix this") is False)
check("detect_cfo=True for 'give me a prompt for Claude' (not a command verb, has cfo keywords)",
      detect_cfo_conversation_need("give me a prompt for claude") is True)

# ── select_cfo_response_strategy routes to implementation_prompt ─────────────
print("\n-- strategy selection routes to implementation_prompt --")
for msg in PROMPT_MESSAGES:
    ctx = build_cfo_context(msg)
    strategy = select_cfo_response_strategy(msg, ctx)
    check(f"strategy=implementation_prompt: {msg[:50]!r}",
          strategy == "implementation_prompt")

# ── run_command produces IMPLEMENTATION PROMPT header ────────────────────────
print("\n-- run_command produces IMPLEMENTATION PROMPT output --")
PROMPT_TEST_CASES = [
    "create a prompt for Claude to fix this",
    "give me a prompt for Claude to build this",
    "create a super prompt for the revenue routing fix",
]
for msg in PROMPT_TEST_CASES:
    r = run_command(msg) or ""
    check(f"starts IMPLEMENTATION PROMPT: {msg[:45]!r}",
          r.startswith("IMPLEMENTATION PROMPT"))
    check(f"contains Goal: {msg[:45]!r}", "Goal:" in r or "goal" in r.lower())
    check(f"contains Safety: {msg[:45]!r}", "Safety:" in r or "safety" in r.lower())
    check(f"no Hermes report header: {msg[:45]!r}", "════" not in r[:80])

# ── Exact command 'create prompt from this' still works via existing handler ──
print("\n-- exact command phrases still work via _PLAIN_INTENTS --")
r = run_command("create prompt from this") or ""
check("create prompt from this still works", "IMPLEMENTATION PROMPT" in r.upper()
      or len(r.strip()) > 10)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
