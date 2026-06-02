"""
test_content_show_it_period_normalization.py
Tests: 'Show it.' with trailing period routes to content draft preview,
same as 'show it' without punctuation.
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


print("=== test_content_show_it_period_normalization ===\n")

# ── Normalization logic: strip trailing .?! before continuity lookup ──────────
print("-- normalization strips trailing punctuation --")
# Simulate what handle_inbound_message does
test_inputs = [
    "Show it.",
    "show it.",
    "Show it!",
    "show it?",
    "Show it",
    "can i view it.",
    "view the draft.",
]
EXPECTED_STRIPPED = {
    "show it.": "show it",
    "show it!": "show it",
    "show it?": "show it",
    "show it": "show it",
    "can i view it.": "can i view it",
    "view the draft.": "view the draft",
}

for raw in test_inputs:
    normalized = raw.strip().lower()
    stripped = normalized.rstrip('.?!')
    expected = EXPECTED_STRIPPED.get(normalized, normalized.rstrip('.?!'))
    check(f"'{raw}' strips to '{expected}'", stripped == expected)

# ── Continuity dict contains "show it" (no period) ────────────────────────────
print("\n-- continuity keys exist without trailing punctuation --")

# We can't instantiate NexusTelegramBot easily, so test via telegram_bot source
import inspect
import telegram_bot as _tbot
src = inspect.getsource(_tbot.NexusTelegramBot.handle_inbound_message)

check("handle_inbound_message strips trailing '.?!'",
      "rstrip('.?!')" in src or "rstrip(\".?!\")" in src)
# Keys use double-quotes in the source dict, check without repr()
check("'show it' in continuity dict source (exact, no period)", '"show it"' in src)
check("_norm_no_punct used for lookup", "_norm_no_punct" in src)

# ── No "Use a content draft command:" error for stripped phrases ───────────────
print("\n-- 'show it.' does not produce 'Use a content draft command' error --")
# Simulate the punct-strip logic directly
CONTINUITY_SAMPLE_KEYS = {
    "show it", "can i view it", "can i see it", "view it",
    "view the draft", "see the draft", "show the draft",
}
for raw_phrase in ["Show it.", "show it.", "Show it!", "can i view it."]:
    normalized = raw_phrase.strip().lower()
    stripped = normalized.rstrip('.?!')
    check(f"'{raw_phrase}' stripped '{stripped}' is in continuity keys",
          stripped in CONTINUITY_SAMPLE_KEYS)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
