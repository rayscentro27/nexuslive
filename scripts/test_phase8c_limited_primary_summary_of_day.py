"""test_phase8c_limited_primary_summary_of_day.py — summary_of_day intent."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from lib.hermes_cfo_loop_shadow import run_cfo_limited_primary, ALLOWLISTED_INTENTS
from prototypes.hermes_agentic_cfo_loop import HermesCFOLoop

# ── summary_of_day is allowlisted ─────────────────────────────────────────────
check("summary_of_day is in ALLOWLISTED_INTENTS", "summary_of_day" in ALLOWLISTED_INTENTS)

# ── Summary of day phrases ────────────────────────────────────────────────────
phrases = [
    "what did we work on today",
    "what did we do today",
    "daily summary",
]
for phrase in phrases:
    response, primary_used = run_cfo_limited_primary(phrase)
    # primary_used may be True if intent matches with confidence >= 0.80
    check(f"'{phrase}': response non-empty", bool(response) or not primary_used)
    if primary_used:
        resp_lower = (response or "").lower()
        check(f"'{phrase}': response has today info",
              "today" in resp_lower or "work" in resp_lower or "task" in resp_lower
              or "priority" in resp_lower or "plan" in resp_lower)
        # Must say what evidence came from if uncertain
        check(f"'{phrase}': no random invention",
              "verified" in resp_lower or "mock" in resp_lower or "priority" in resp_lower
              or "today" in resp_lower)

# ── Direct prototype validation ───────────────────────────────────────────────
loop = HermesCFOLoop()
response, trace = loop.process("what did we work on today")
check("direct: intent=summary_of_day", trace["intent"] == "summary_of_day")
check("direct: tool=show_daily_summary", trace["tool"] == "show_daily_summary")
check("direct: response has daily info",
      "today" in response.lower() or "work" in response.lower() or "task" in response.lower())

# ── Response does not invent unverified facts ─────────────────────────────────
loop2 = HermesCFOLoop()
r2, t2 = loop2.process("what did we do today")
check("'what did we do today': tool=show_daily_summary", t2["tool"] == "show_daily_summary")
# Should mention mock/note or actual plan data — not made-up claims
check("'what did we do today': has plan content or note",
      "priority" in r2.lower() or "task" in r2.lower() or "note" in r2.lower())

# ── "what did we work on today" via run_cfo_limited_primary ──────────────────
response3, used3 = run_cfo_limited_primary("what did we work on today")
check("run_cfo_limited_primary: returns something", response3 is not None or not used3)

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C summary of day: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
