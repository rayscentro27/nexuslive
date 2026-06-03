"""
test_phase7a_unknown_scout_dispatch_priority.py
Phase 7A: Unknown-answer messages produce scout dispatch, not old scout status.
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


print("=== test_phase7a_unknown_scout_dispatch_priority ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import select_cfo_response_strategy, build_cfo_context

# ── Explicit scout delegation phrases → unknown_dispatch ─────────────────────
print("-- scout delegation phrases → unknown_dispatch strategy --")

SCOUT_DISPATCH_MESSAGES = [
    "can your scouts figure it out?",
    "I don't know the answer, can your scouts figure it out?",
    "Can Hermes find the best affiliate offer for the funding checklist?",
    "Can Hermes research the best credit repair programs?",
    "I don't know, can hermes look into it?",
    "have the scouts look at competitor pricing",
]
for msg in SCOUT_DISPATCH_MESSAGES:
    ctx = build_cfo_context(msg)
    strategy = select_cfo_response_strategy(msg, ctx)
    check(f"strategy=unknown_dispatch: {msg[:50]!r}", strategy == "unknown_dispatch")

# ── run_command produces I DON'T HAVE VERIFIED for unknown messages ──────────
print("\n-- run_command produces scout dispatch header --")

UNKNOWN_MESSAGES = [
    "I don't know the answer, can your scouts figure it out?",
    "Can Hermes find the best affiliate offer for the funding checklist?",
]
for msg in UNKNOWN_MESSAGES:
    r = run_command(msg) or ""
    check(f"starts with I DON'T HAVE VERIFIED: {msg[:45]!r}",
          r.startswith("I DON'T HAVE VERIFIED"))
    check(f"mentions scout: {msg[:45]!r}",
          "scout" in r.lower())

# ── Scout dispatch does NOT produce old scout status ─────────────────────────
print("\n-- scout dispatch does not produce old scout status format --")
OLD_SCOUT_STATUS_MARKERS = [
    "SCOUT STATUS:", "Scout intelligence check:", "No scouts available",
    "OANDA", "trade execution", "live trading started",
]
for msg in UNKNOWN_MESSAGES:
    r = (run_command(msg) or "").lower()
    for marker in OLD_SCOUT_STATUS_MARKERS:
        check(f"no old scout marker {marker!r}: {msg[:40]!r}",
              marker.lower() not in r)

# ── Research queue is updated after scout dispatch ────────────────────────────
print("\n-- scout dispatch persists to research queue --")
import time
pre_msg = f"phase7a_test_unknown_{int(time.time())}"
run_command(f"can your scouts figure out: {pre_msg}")

from lib.hermes_cfo_conversation_layer import load_research_queue
queue = load_research_queue(status="open")
found = any(pre_msg.lower() in e.get("question", "").lower() for e in queue)
check("scout dispatch adds entry to research queue", found)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
