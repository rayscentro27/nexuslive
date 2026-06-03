"""
test_scout_assignment_commands.py
Tests: 'show scout assignments', 'what did the scouts find?' route correctly.
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


print("=== test_scout_assignment_commands ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── Intent classification ─────────────────────────────────────────────────────
print("-- intent classification --")

INTENT_MAP = {
    "show scout assignments":           "show_scout_assignments",
    "scout assignments":                "show_scout_assignments",
    "what are scouts working on":       "show_scout_assignments",
    "what did the scouts find":         "show_scout_assignments",
    "what did scouts find":             "show_scout_assignments",
    "active scout assignments":         "show_scout_assignments",
}

for phrase, expected in INTENT_MAP.items():
    intent, _, _ = classify_intent(phrase)
    check(f"'{phrase[:45]}' → {expected}", intent == expected)

# ── Handler responses ────────────────────────────────────────────────────────
print("\n-- handler responses --")

response = run_command("show scout assignments") or ""
check("'show scout assignments' returns SCOUT ASSIGNMENTS header",
      "SCOUT ASSIGNMENTS" in response.upper())
check("'show scout assignments' has approval boundary",
      "approval" in response.lower())

# ── format_scout_assignments ─────────────────────────────────────────────────
print("\n-- format_scout_assignments --")
from lib.hermes_cfo_conversation_layer import format_scout_assignments
sa = format_scout_assignments()
check("returns str", isinstance(sa, str))
check("starts with SCOUT ASSIGNMENTS", sa.startswith("SCOUT ASSIGNMENTS"))

# ── Scout map completeness ────────────────────────────────────────────────────
print("\n-- scout map completeness --")
from lib.hermes_cfo_conversation_layer import _SCOUT_MAP
REQUIRED_CATEGORIES = [
    "monetization_strategy", "content_strategy", "funding_credit",
    "technical_system", "product_direction", "hermes_behavior_feedback",
    "unknown_general",
]
for cat in REQUIRED_CATEGORIES:
    check(f"[{cat}] has scout mapping", cat in _SCOUT_MAP)
    if cat in _SCOUT_MAP:
        check(f"[{cat}] scout list non-empty", len(_SCOUT_MAP[cat]) >= 1)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
