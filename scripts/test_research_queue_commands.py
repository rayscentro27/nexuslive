"""
test_research_queue_commands.py
Tests: 'show research queue' and related commands route and respond correctly.
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


print("=== test_research_queue_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── Intent classification ─────────────────────────────────────────────────────
print("-- intent classification --")

INTENT_MAP = {
    "show research queue":                "show_research_queue",
    "research queue":                     "show_research_queue",
    "show open research questions":       "show_research_queue",
    "what is in the research queue":      "show_research_queue",
    "add this to the research queue":     "show_research_queue",
    "show unresolved questions":          "show_unresolved_questions",
    "what are you still trying to figure out": "show_unresolved_questions",
    "what don't you know":                "show_unresolved_questions",
}

for phrase, expected in INTENT_MAP.items():
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → {expected}", intent == expected)

# ── Handler responses ────────────────────────────────────────────────────────
print("\n-- handler responses --")

for phrase, expected_header in [
    ("show research queue",         "RESEARCH QUEUE"),
    ("show unresolved questions",   "UNRESOLVED QUESTIONS"),
]:
    try:
        response = run_command(phrase) or ""
        check(f"'{phrase}' has correct header",
              expected_header.upper() in response.upper())
        check(f"'{phrase}' is non-empty", len(response.strip()) > 20)
    except Exception as exc:
        check(f"'{phrase}' did not raise", False)
        print(f"  Error: {exc!s:.100}")

# ── Research queue format_research_queue ─────────────────────────────────────
print("\n-- format_research_queue --")
from lib.hermes_cfo_conversation_layer import format_research_queue
rq = format_research_queue()
check("format_research_queue returns str", isinstance(rq, str))
check("format_research_queue starts with RESEARCH QUEUE",
      rq.startswith("RESEARCH QUEUE"))
check("format_research_queue has approval boundary",
      "Approval boundary" in rq or "approval" in rq.lower())

# ── format_unresolved_questions ───────────────────────────────────────────────
print("\n-- format_unresolved_questions --")
from lib.hermes_cfo_conversation_layer import format_unresolved_questions
uq = format_unresolved_questions()
check("format_unresolved_questions returns str", isinstance(uq, str))
check("format_unresolved_questions starts with UNRESOLVED",
      uq.startswith("UNRESOLVED"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
