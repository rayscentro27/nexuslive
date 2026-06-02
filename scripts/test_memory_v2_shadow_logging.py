"""
test_memory_v2_shadow_logging.py
Verifies shadow log writes safe metadata, no secrets, no raw payloads.
"""
import sys, os, json, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_memory_v2_shadow_logging ===\n")

import lib.hermes_memory_v2_shadow as shadow

print("-- log_shadow_memory_result writes safe record --")
test_record = {
    "timestamp":            "2026-06-02T10:00:00Z",
    "message_hash":         "abc123def456",
    "mode":                 "shadow",
    "current_sources":      ["active_operating_rules"],
    "v2_record_count":      26,
    "v2_types":             {"lesson": 3, "goal": 3},
    "overlap_summary":      "8/8 planned types present",
    "missing_summary":      "none",
    "coverage_pct":         100,
    "risk_flags":           [],
    "recommendation":       "Batch 1/2 coverage complete.",
    "live_response_changed": False,
}
shadow.log_shadow_memory_result(test_record)

log_path = shadow.SHADOW_LOG_PATH
check("shadow log file was created", log_path.exists())

lines = [json.loads(l) for l in log_path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]
check("at least one log entry", len(lines) >= 1)
latest = lines[-1]
check("log entry has 'timestamp'", "timestamp" in latest)
check("log entry has 'message_hash'", "message_hash" in latest)
check("log entry has 'mode'", "mode" in latest)
check("log entry has 'live_response_changed'", "live_response_changed" in latest)
check("log entry 'live_response_changed' is False",
      latest.get("live_response_changed") is False)

print("\n-- log does NOT contain secrets --")
log_text = log_path.read_text(encoding="utf-8")
check("no 'secret_key' in log", "secret_key" not in log_text.lower())
check("no 'api_token' in log", "api_token" not in log_text.lower())
check("no 'eyJ' (JWT) in log", "eyJ" not in log_text)
check("no SUPABASE_SERVICE_ROLE_KEY in log",
      "SUPABASE_SERVICE_ROLE_KEY" not in log_text)
check("no raw user message in log (not 'raw_message' field)",
      '"raw_message"' not in log_text)

print("\n-- run_shadow_memory_comparison auto-logs --")
os.environ["HERMES_MEMORY_V2_MODE"] = "shadow"
before_count = len([l for l in log_path.read_text().strip().splitlines() if l.strip()])
shadow.run_shadow_memory_comparison("test message for log", {}, "test response")
time.sleep(0.1)  # allow async to flush if needed (sync path also writes directly)
after_count = len([l for l in log_path.read_text().strip().splitlines() if l.strip()])
check("run_shadow_memory_comparison writes to log",
      after_count > before_count)

print("\n-- shadow log directory is in docs/reports/memory/shadow/ --")
check("SHADOW_LOG_DIR parent is docs/reports/memory",
      shadow.SHADOW_LOG_DIR.parent.name == "memory")
check("SHADOW_LOG_DIR name is 'shadow'",
      shadow.SHADOW_LOG_DIR.name == "shadow")
check("SHADOW_LOG_PATH name ends with '.jsonl'",
      shadow.SHADOW_LOG_PATH.suffix == ".jsonl")

print("\n-- _SUPABASE_WRITE_ATTEMPTED remains False after logging --")
check("sentinel still False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
