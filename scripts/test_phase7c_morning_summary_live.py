"""
test_phase7c_morning_summary_live.py
Phase 7C tests: morning summary returns structured response, not evidence dump.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

PASS = 0
FAIL = 0


def check(label: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


from lib.hermes_cfo_brain import (
    classify_cfo_intent,
    should_use_cfo_brain,
    handle_morning_activity,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import update_conversation_state, load_conversation_state

# ── Morning intent classification ─────────────────────────────────────────────

morning_msgs = [
    "what did you do this morning",
    "what happened this morning",
    "what did you work on",
    "catch me up",
    "while i was out",
    "morning summary",
    "what have you been doing",
]
for msg in morning_msgs:
    check(f"'{msg}' → morning_activity_question",
          classify_cfo_intent(msg) == "morning_activity_question")

check("should_use: what did you do this morning",
      should_use_cfo_brain("what did you do this morning"))
check("should_use: catch me up",
      should_use_cfo_brain("catch me up"))

# ── handle_morning_activity returns MORNING SUMMARY structure ─────────────────

state = load_conversation_state()
r = handle_morning_activity("what did you do this morning", state)

check("morning returns string", isinstance(r, str) and len(r) > 20)
check("morning has MORNING SUMMARY header", "MORNING SUMMARY" in r)
check("morning no evidence dump", "Live answer sources:" not in r)
check("morning no quality fallback", "quality response" not in r.lower())
check("morning no 'plain-language mode enabled'", "plain-language mode enabled" not in r.lower())
check("morning has approval boundary", "approval" in r.lower())

# Content structure checks
lines = r.splitlines()
header_line = lines[0] if lines else ""
check("first line is MORNING SUMMARY", header_line.strip() == "MORNING SUMMARY")
check("response has multiple lines", len(lines) > 3)

# ── process_with_cfo_brain for morning ────────────────────────────────────────

r2 = process_with_cfo_brain("what did you do this morning", "what did you do this morning")
check("process: morning returns string", isinstance(r2, str) and len(r2) > 10)
check("process: MORNING SUMMARY in response", "MORNING SUMMARY" in (r2 or ""))
check("process: no evidence dump", "live answer sources:" not in (r2 or "").lower())
check("process: no quality fallback", "quality response" not in (r2 or "").lower())

r3 = process_with_cfo_brain("catch me up", "catch me up")
check("process: 'catch me up' returns string", isinstance(r3, str) and len(r3) > 10)
check("process: 'catch me up' has MORNING SUMMARY or summary",
      "MORNING SUMMARY" in (r3 or "") or "summary" in (r3 or "").lower())

r4 = process_with_cfo_brain("what happened this morning", "what happened this morning")
check("process: 'what happened this morning' returns string",
      isinstance(r4, str) and len(r4) > 10)
check("process: 'what happened this morning' no evidence dump",
      "live answer sources:" not in (r4 or "").lower())

# ── Morning summary does not call Ollama ─────────────────────────────────────

# Verify the response doesn't contain AI synthesis markers
check("morning not an AI-generated synthesis",
      "HERMES REPORT" not in (r or ""))
check("morning not evidence dump format",
      "Confidence:" not in (r or "") and "Source 1:" not in (r or ""))

# Print summary
print(f"\nPhase 7C morning summary live: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
