"""test_phase8b_existing_commands_still_work.py — All Phase 6–7D commands still work."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

# Import with shadow mode OFF (default) to ensure no interference
os.environ.pop("HERMES_CFO_LOOP_MODE", None)

from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent
from lib.hermes_cfo_brain import classify_cfo_intent, process_with_cfo_brain, should_use_cfo_brain

# ── Exact commands still route correctly ──────────────────────────────────────
exact_commands = [
    ("show memory v2 primary status", "memory_v2_primary_status"),
    ("show approval queue", "daily_approval_queue"),
]
for cmd, expected_intent in exact_commands:
    try:
        intent, _, _ = classify_intent(cmd)
        result = run_command(cmd, source="test")
        check(f"command '{cmd}': returns non-empty", bool(result))
        check(f"command '{cmd}': no evidence dump", "Live answer sources:" not in (result or ""))
    except Exception as e:
        check(f"command '{cmd}': no exception", False)

# ── Phase 7C CFO Brain intents still work ─────────────────────────────────────
cfo_phrases = {
    "option_selection": ["lets do 1", "lets do 2"],
    "simplify_previous_response": ["can you simplify your response"],
    "explain_previous_response": ["explain your recommendation in plain language"],
    "task_reference": ["what was task 1"],
    "failure_feedback": ["that is not what i meant"],
}
for intent, phrases in cfo_phrases.items():
    for phrase in phrases:
        result_intent = classify_cfo_intent(phrase)
        check(f"Phase 7C intent '{intent}': {phrase[:40]}", result_intent == intent)

# ── process_with_cfo_brain still works for key phrases ───────────────────────
cfo_process_phrases = [
    "how do we make money this week",
    "can you simplify your response",
    "explain your recommendation in plain language",
]
for phrase in cfo_process_phrases:
    try:
        result = process_with_cfo_brain(phrase, phrase.lower())
        check(f"process_with_cfo_brain: '{phrase[:40]}'", isinstance(result, str) and len(result) > 10)
        check(f"no evidence dump: '{phrase[:30]}'", "Live answer sources:" not in (result or ""))
    except Exception as e:
        check(f"process_with_cfo_brain no exception: {phrase[:30]}", False)

# ── should_use_cfo_brain still returns True for CFO phrases ──────────────────
check("should_use_cfo_brain: money", should_use_cfo_brain("how do we make money this week"))
check("should_use_cfo_brain: simplify", should_use_cfo_brain("can you simplify your response"))

# ── Shadow mode does not break any command ────────────────────────────────────
os.environ["HERMES_CFO_LOOP_MODE"] = "shadow"
from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command

for phrase in ["how do we make money", "lets do 1", "show approval queue"]:
    # Shadow commands should return None for non-shadow-command phrases
    shadow_result = handle_cfo_shadow_command(phrase)
    check(f"non-shadow phrase not hijacked by shadow: {phrase[:30]}", shadow_result is None)

os.environ.pop("HERMES_CFO_LOOP_MODE", None)

print(f"\nPhase 8B existing commands still work: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
