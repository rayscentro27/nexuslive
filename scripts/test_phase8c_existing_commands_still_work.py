"""test_phase8c_existing_commands_still_work.py — exact commands still work after grounding patch."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
PASS = 0; FAIL = 0
def check(label, condition):
    global PASS, FAIL
    if condition: PASS += 1
    else: FAIL += 1; print(f"FAIL: {label}")

os.environ["HERMES_CFO_LOOP_MODE"] = "limited_primary"
os.environ["HERMES_CFO_LOOP_PROVIDER"] = "mock"

from hermes_command_router.router import run_command
from lib.hermes_cfo_loop_shadow import handle_cfo_shadow_command
import telegram_bot

# ── Phase 8B status commands still work ──────────────────────────────────────
phase8b_cmds = [
    "show cfo shadow status",
    "cfo shadow status",
    "show cfo loop mode",
    "show cfo shadow traces",
    "cfo shadow traces",
    "compare cfo shadow",
    "cfo shadow compare",
]
for cmd in phase8b_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"Phase 8B '{cmd}': returns non-empty", bool(result) and len(result or "") > 10)

# ── Phase 8C status commands work ────────────────────────────────────────────
phase8c_cmds = [
    "show cfo limited primary status",
    "show cfo primary status",
    "rollback cfo loop to shadow",
]
for cmd in phase8c_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"Phase 8C '{cmd}': returns non-empty", bool(result) and len(result or "") > 10)
    if "status" in cmd:
        lower = (result or "").lower()
        check(f"Phase 8C '{cmd}': has primary used count", "primary used count" in lower)
        check(f"Phase 8C '{cmd}': has mock-blocked count", "mock-blocked count" in lower)
        check(f"Phase 8C '{cmd}': has grounded data paths checked", "grounded data paths checked" in lower)

# ── Approval queue still works ────────────────────────────────────────────────
try:
    result = run_command("show approval queue", source="test")
    check("show approval queue: non-empty", bool(result) and len(result) > 10)
    check("show approval queue: has approval content", "approval" in (result or "").lower())
    check("show approval queue: no live answer sources", "live answer sources:" not in (result or ""))
except Exception as e:
    check("show approval queue: no exception", False)
    print(f"  Exception: {e}")

# ── Memory v2 status command still works ──────────────────────────────────────
try:
    result = run_command("show memory v2 primary status", source="test")
    check("show memory v2 primary status: non-empty", bool(result) and len(result) > 10)
    check("show memory v2 primary status: has memory v2 wording", "memory v2" in (result or "").lower())
except Exception as e:
    check("show memory v2 primary status: no exception", False)
    print(f"  Exception: {e}")

# ── Telegram routing still honors exact commands in limited_primary ───────────
try:
    telegram_bot.NexusTelegramBot.test_connection = lambda self: None
    bot = telegram_bot.NexusTelegramBot()
    draft_resp = bot.handle_inbound_message("what changed in the draft")
    check("telegram draft comparison avoids last-plan fallback",
          "which draft should i compare" in (draft_resp or "").lower()
          or "here is what changed in the draft" in (draft_resp or "").lower())
    check("telegram draft comparison not routed to daily-plan compare",
          "what changed since the last plan" not in (draft_resp or "").lower())

    clarify_resp = bot.handle_inbound_message("ask me a better clarifying question")
    check("telegram clarifying question primary used",
          "clarifying question" in (clarify_resp or "").lower())

    impl_resp = bot.handle_inbound_message("create the implementation prompt now")
    check("telegram implementation prompt avoids stale generic research option",
          "selected option: research the question and return with verified evidence" not in (impl_resp or "").lower())

    mem_resp = bot.handle_inbound_message("show memory v2 primary status")
    check("telegram memory v2 status still works",
          "memory v2 primary status" in (mem_resp or "").lower())
except Exception as e:
    check("telegram limited_primary exact commands: no exception", False)
    print(f"  Exception: {e}")

# ── CFO shadow command handler does NOT intercept non-CFO commands ────────────
non_shadow_cmds = [
    "show approval queue",
    "show memory v2 primary status",
    "daily operating cycle plan",
    "how do we make money this week",
    "what are we working on",
]
for cmd in non_shadow_cmds:
    result = handle_cfo_shadow_command(cmd)
    check(f"'{cmd}': handle_cfo_shadow_command returns None (not intercepted)", result is None)

# ── Approval queue not intercepted by limited_primary in test context ─────────
from lib.hermes_cfo_loop_shadow import should_run_cfo_limited_primary
check("should_run_cfo_limited_primary=False for CFO status cmds",
      not should_run_cfo_limited_primary("show cfo limited primary status"))
check("should_run_cfo_limited_primary=False for rollback",
      not should_run_cfo_limited_primary("rollback cfo loop to shadow"))

# Cleanup
os.environ.pop("HERMES_CFO_LOOP_MODE", None)
os.environ.pop("HERMES_CFO_LOOP_PROVIDER", None)

print(f"\nPhase 8C existing commands: {PASS} pass, {FAIL} fail")
if FAIL: sys.exit(1)
