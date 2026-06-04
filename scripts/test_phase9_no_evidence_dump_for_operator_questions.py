"""test_phase9_no_evidence_dump_for_operator_questions.py — operator questions never evidence-dump."""
import sys

from phase9_test_helpers import BANNED_EVIDENCE_MARKERS, cleanup_env, make_bot

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


MESSAGES = [
    "Review the Funding Readiness Launch Packet and give me the approval decision summary.",
    "what changed in the draft",
    "i approve them all",
    "create the implementation prompt now",
    "what did we work on today",
    "what are all the scouts doing right now",
    "what should i approve first",
    "what is the current revenue packet score",
    "which asset is closest to launch ready",
    "ask me a better clarifying question",
]

bot = make_bot()
try:
    for message in MESSAGES:
        response = bot.handle_inbound_message(message)
        lower = (response or "").lower()
        for marker in BANNED_EVIDENCE_MARKERS:
            check(f"'{message[:40]}' omits '{marker}'", marker not in lower)
        check(f"'{message[:40]}' omits HERMES REPORT wrapper", "hermes report" not in lower)
finally:
    cleanup_env()

print(f"\nPhase 9 no evidence dump: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
