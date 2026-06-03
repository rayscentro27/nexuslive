"""
test_phase7c_failure_learning_routing.py
Phase 7C tests: failure feedback and failure learning route correctly.
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
    handle_failure_feedback,
    process_with_cfo_brain,
)
from lib.hermes_conversation_state import update_conversation_state, load_conversation_state

# ── Failure feedback intent classification ────────────────────────────────────

failure_msgs = [
    "that is not what i meant",
    "that's not what i meant",
    "that's wrong",
    "that was wrong",
    "wrong answer",
    "that's not right",
    "that is not right",
    "not what i asked",
    "log this as a bad response",
    "learn from that",
    "that was not right",
]
for msg in failure_msgs:
    check(f"'{msg}' → failure_feedback",
          classify_cfo_intent(msg) == "failure_feedback")

check("should_use: that is not what i meant",
      should_use_cfo_brain("that is not what i meant"))
check("should_use: that's not right",
      should_use_cfo_brain("that's not right"))
check("should_use: learn from that",
      should_use_cfo_brain("learn from that"))

# ── handle_failure_feedback returns CORRECTING COURSE ────────────────────────

update_conversation_state(
    user_message="explain your recommendation",
    hermes_response="HERMES REPORT\n\nLive answer sources: ...\nConfidence: 50%",
    tool_used="evidence_dump",
)

state = load_conversation_state()
r = handle_failure_feedback("that is not what i meant", state)

check("failure feedback returns string", isinstance(r, str) and len(r) > 10)
check("failure feedback has CORRECTING COURSE", "CORRECTING COURSE" in r)
check("failure feedback no evidence dump", "Live answer sources:" not in r)
check("failure feedback no quality fallback", "quality response" not in r.lower())
check("failure feedback has approval boundary", "approval" in r.lower())
check("failure feedback logged message", "logged" in r.lower() or "training" in r.lower())
check("failure feedback offers what to do next", "show failed" in r.lower() or "ask me" in r.lower())

# ── process_with_cfo_brain for failure feedback ───────────────────────────────

r2 = process_with_cfo_brain("that is not what i meant", "that is not what i meant")
check("process: failure feedback returns string", isinstance(r2, str) and len(r2) > 10)
check("process: CORRECTING COURSE in response", "CORRECTING COURSE" in (r2 or ""))
check("process: no evidence dump", "live answer sources:" not in (r2 or "").lower())
check("process: no quality fallback", "quality response" not in (r2 or "").lower())

r3 = process_with_cfo_brain("that's wrong", "that's wrong")
check("process: 'that's wrong' returns string", isinstance(r3, str) and len(r3) > 10)
check("process: 'that's wrong' CORRECTING COURSE", "CORRECTING COURSE" in (r3 or ""))

# ── Failure learning module is importable ─────────────────────────────────────

try:
    from lib.hermes_failure_learning import (
        log_failed_response,
        format_failure_review,
        FAILURE_TYPES,
    )
    check("hermes_failure_learning importable", True)
    check("FAILURE_TYPES is set or dict", isinstance(FAILURE_TYPES, (set, dict)))
    check("FAILURE_TYPES has expected keys",
          "evidence_dump" in FAILURE_TYPES or "lost_context" in FAILURE_TYPES)
except ImportError as e:
    check(f"hermes_failure_learning importable (FAIL: {e})", False)

# ── format_failure_review returns structured response ────────────────────────

from lib.hermes_failure_learning import format_failure_review
review = format_failure_review()
check("format_failure_review returns string", isinstance(review, str))
check("format_failure_review has FAILED RESPONSES header",
      "FAILED RESPONSES" in review)
# Note: the review intentionally shows logged bad responses (may include evidence dump content)
check("format_failure_review has structured content",
      "No failed responses" in review or "unreviewed" in review or "failure" in review.lower())

# Print summary
print(f"\nPhase 7C failure learning routing: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
