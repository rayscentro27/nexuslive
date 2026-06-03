"""
test_phase7c_failed_responses_command.py
Phase 7C tests: 'show failed responses' exact command routes through memory path.
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


from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# ── 'show failed responses' classifies correctly ─────────────────────────────

show_failed_msgs = [
    "show failed responses",
    "show failure log",
    "show bad responses",
]
for msg in show_failed_msgs:
    intent, conf, _ = classify_intent(msg)
    check(f"'{msg}' → show_failed_responses", intent == "show_failed_responses")

# ── run_command returns structured response ───────────────────────────────────

r = run_command("show failed responses", source="telegram")
check("run_command returns string", isinstance(r, str))
check("run_command has FAILED RESPONSES header", "FAILED RESPONSES" in (r or ""))
# Note: failure review may contain logged bad responses; the HEADER and structure must be correct
check("run_command has FAILED RESPONSES header", "FAILED RESPONSES" in (r or ""))
check("run_command no quality fallback", "quality response" not in (r or "").lower())
check("run_command no 'plain-language mode enabled'",
      "plain-language mode enabled" not in (r or "").lower())

# ── Failure learning commands classify and route ──────────────────────────────

for cmd in ["log this as a bad response", "hermes, learn from that", "create tests from failures"]:
    intent2, _, _ = classify_intent(cmd)
    check(f"'{cmd}' classifies to a known intent",
          intent2 in {"log_bad_response", "learn_from_that", "create_tests_from_failures"})
    r2 = run_command(cmd, source="telegram")
    check(f"run_command('{cmd}') returns string", isinstance(r2, str) and len(r2) > 5)
    check(f"run_command('{cmd}') no evidence dump",
          "Live answer sources:" not in (r2 or ""))

# ── show_failed_responses is in SAFE_REPEATABLE_MEMORY_INTENTS ────────────────

try:
    from telegram_bot import NexusTelegramBot
    safe_set = NexusTelegramBot.SAFE_REPEATABLE_MEMORY_INTENTS
    check("show_failed_responses in SAFE_REPEATABLE_MEMORY_INTENTS",
          "show_failed_responses" in safe_set)
    check("log_bad_response in SAFE_REPEATABLE_MEMORY_INTENTS",
          "log_bad_response" in safe_set)
    check("learn_from_that in SAFE_REPEATABLE_MEMORY_INTENTS",
          "learn_from_that" in safe_set)
    check("create_tests_from_failures in SAFE_REPEATABLE_MEMORY_INTENTS",
          "create_tests_from_failures" in safe_set)
except Exception as e:
    check(f"SAFE_REPEATABLE_MEMORY_INTENTS check (FAIL: {e})", False)

# Print summary
print(f"\nPhase 7C failed responses command: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
