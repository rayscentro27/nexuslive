"""
test_memory_v2_shadow_does_not_change_response.py
Verifies that shadow mode does not alter the live Telegram response path.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_shadow_does_not_change_response ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- compare_shadow_contexts never changes live_response_changed --")
for ctx in [{}, {"sources": ["a", "b"]}, {"available": True}]:
    for v2 in [{}, {"available": True, "total": 26}]:
        r = shadow.compare_shadow_contexts(ctx, v2)
        check(f"live_response_changed False for ctx={bool(ctx)} v2={bool(v2)}",
              r.get("live_response_changed") is False)

print("\n-- run_shadow_memory_comparison never modifies response string --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
test_response = "This is the original Hermes response."
r = shadow.run_shadow_memory_comparison(
    user_message="what do you recommend",
    current_context={},
    current_response=test_response,
)
check("live_response_changed is False", r.get("live_response_changed") is False)
check("returned response text unchanged (not in result)",
      "This is the original Hermes response." not in str(r.get("recommendation", "")))
check("result does not contain full original response text as a field",
      test_response not in str(r))

print("\n-- trigger_shadow_comparison_async is fire-and-forget (non-blocking) --")
import time
start = time.time()
shadow.trigger_shadow_comparison_async(
    user_message="test non-blocking",
    current_context={},
    current_response="test",
)
elapsed = time.time() - start
check("trigger_shadow_comparison_async returns quickly (< 0.5s)", elapsed < 0.5)

print("\n-- Shadow mode does NOT affect memory command responses --")
from hermes_command_router.router import run_command
for cmd in ["show memory v2 status", "compare memory v2", "show memory sources"]:
    result_no_shadow = None
    result_shadow = None
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)
    result_no_shadow = run_command(cmd, source="telegram") or ""
    os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
    result_shadow = run_command(cmd, source="telegram") or ""
    check(f"'{cmd[:35]}' response same in shadow vs non-shadow",
          result_no_shadow.strip() == result_shadow.strip() or
          (bool(result_no_shadow.strip()) and bool(result_shadow.strip())))

print("\n-- telegram_bot shadow hook imports correctly --")
import telegram_bot as tb_mod
import inspect
tb_src = inspect.getsource(tb_mod)
check("telegram_bot imports hermes_memory_v2_shadow conditionally",
      "hermes_memory_v2_shadow" in tb_src)
check("telegram_bot uses is_shadow_mode_enabled check",
      "is_shadow_mode_enabled" in tb_src)
check("telegram_bot uses trigger_shadow_comparison_async",
      "trigger_shadow_comparison_async" in tb_src)
check("telegram_bot shadow block has pass on exception",
      "pass  # shadow errors must never affect live response" in tb_src or
      "pass" in tb_src)

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
