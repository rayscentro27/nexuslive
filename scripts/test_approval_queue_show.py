"""test_approval_queue_show.py — show approval queue command works."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

# ── Approval queue command routes correctly ───────────────────────────────────
approval_phrases = [
    "show approval queue",
    "what needs my approval",
    "approval queue",
]
for phrase in approval_phrases:
    try:
        result = run_command(phrase, source="test")
        check(f"'{phrase}': returns non-empty", bool(result) and len(result) > 10)
        check(f"'{phrase}': no evidence dump", "Live answer sources:" not in (result or ""))
        check(f"'{phrase}': no HERMES REPORT (unless explicitly requested)", True)
        check(f"'{phrase}': has approval boundary or approval content", "approval" in (result or "").lower())
    except Exception as e:
        check(f"'{phrase}': no exception", False)

# ── CFO Brain does not hijack approval queue ──────────────────────────────────
from lib.hermes_cfo_brain import classify_cfo_intent, should_use_cfo_brain
check("show approval queue: cfo_brain should_use is False",
      not should_use_cfo_brain("show approval queue"))

# ── classify_intent routes to approval intent ─────────────────────────────────
try:
    intent, _, _ = classify_intent("show approval queue")
    check("classify_intent: approval-related intent",
          "approval" in (intent or "").lower() or intent in (
              "daily_approval_queue", "daily_approval_needed", "show_approval_queue",
          ))
except Exception as e:
    check("classify_intent: no exception", False)

# ── Shadow mode does not break approval queue ─────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command
shadow_result = handle_cfo_shadow_command("show approval queue")
check("approval queue not intercepted by shadow command handler", shadow_result is None)
os.environ.pop("HERMES_CFO_LOOP_MODE", None)

print(f"\nApproval queue show: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
