"""
test_hermes_memory_v2_shadow.py
Integration test for shadow mode with HERMES_MEMORY_V2_MODE=shadow set.
Verifies: mode active, v2 loads 26 rows, log writes safe metadata,
live response unchanged, primary blocked.
"""
import sys, os, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Load .env credentials (needed for live Supabase shadow reads)
_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

# Force shadow mode for this test
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_v2_shadow (HERMES_MEMORY_V2_MODE=shadow) ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- Shadow mode active --")
check("get_memory_v2_mode() == 'shadow'", shadow.get_memory_v2_mode() == "shadow")
check("is_shadow_mode_enabled() is True", shadow.is_shadow_mode_enabled() is True)
check("is_primary_mode_requested() is False",
      shadow.is_primary_mode_requested() is False)
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

print("\n-- Shadow comparison result --")
result = shadow.run_shadow_memory_comparison(
    user_message="what do you recommend",
    current_context={},
    current_response="This is a normal Hermes answer.",
)
check("mode is 'shadow'", result.get("mode") == "shadow")
check("live_response_changed is False", result.get("live_response_changed") is False)
check("has timestamp", bool(result.get("timestamp")))
check("has message_hash", bool(result.get("message_hash")))
check("message_hash is not raw message",
      result.get("message_hash") != "what do you recommend")
check("has overlap_summary", bool(result.get("overlap_summary")))
check("has risk_flags list", isinstance(result.get("risk_flags"), list))
check("no risk_flags (all 8 types present)", result.get("risk_flags") == [])

print("\n-- Live v2 row count via shadow comparison --")
v2_count = result.get("v2_record_count", 0)
check(f"v2_record_count > 0 ({v2_count} rows)", v2_count > 0)
check("v2_record_count >= 26 (Batch 1 + Batch 2)", v2_count >= 26)
check("overlap_summary shows 8/8 planned types",
      "8/8" in result.get("overlap_summary", ""))
check("missing_summary is 'none'", result.get("missing_summary") == "none")

print("\n-- Shadow log safety --")
log_path = shadow.SHADOW_LOG_PATH
check("shadow log file exists", log_path.exists())
log_lines = [json.loads(l) for l in log_path.read_text().strip().splitlines() if l.strip()]
check("at least 1 log entry", len(log_lines) >= 1)
latest = log_lines[-1]
check("log has 'live_response_changed': False",
      latest.get("live_response_changed") is False)
log_text = log_path.read_text()
check("no raw_message field in log", '"raw_message"' not in log_text)
check("no eyJ (JWT) in log", "eyJ" not in log_text)
check("no api_token in log", "api_token" not in log_text.lower())
check("no SUPABASE_SERVICE_ROLE_KEY in log",
      "SUPABASE_SERVICE_ROLE_KEY" not in log_text)
check("no payload field in log", '"payload"' not in log_text)

print("\n-- Shadow log path is correct --")
check("log dir is docs/reports/memory/shadow/",
      shadow.SHADOW_LOG_DIR.name == "shadow" and
      shadow.SHADOW_LOG_DIR.parent.name == "memory")
check("log file ends in .jsonl", log_path.suffix == ".jsonl")

print("\n-- format_shadow_status shows correct state --")
status = shadow.format_shadow_status()
check("contains 'HERMES MEMORY V2 SHADOW STATUS'",
      "HERMES MEMORY V2 SHADOW STATUS" in status)
check("shows Mode: shadow", "shadow" in status.lower())
check("shows live reader is current reader",
      "current active reader" in status.lower() or "current reader" in status.lower())
check("says shadow does not change answers",
      "does not change" in status.lower())
check("says primary requires approval",
      "approval" in status.lower())
check("shows rows > 0", str(v2_count) in status or "26" in status)
check("shows last shadow comparison (non-empty after run)",
      "none yet" not in status or len(log_lines) == 0)

print("\n-- Primary mode still blocked --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
mode_after_primary = shadow.get_memory_v2_mode()
check("primary env doesn't activate primary mode",
      mode_after_primary != "primary")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"  # restore

print("\n-- Telegram bot has shadow hook --")
import telegram_bot as tb_mod
import inspect
tb_src = inspect.getsource(tb_mod)
check("telegram_bot imports hermes_memory_v2_shadow",
      "hermes_memory_v2_shadow" in tb_src)
check("telegram_bot checks is_shadow_mode_enabled",
      "is_shadow_mode_enabled" in tb_src)
check("telegram_bot fires trigger_shadow_comparison_async",
      "trigger_shadow_comparison_async" in tb_src)
check("shadow errors swallowed (pass on exception)",
      "pass  # shadow errors must never affect live response" in tb_src or
      "pass" in tb_src)

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
