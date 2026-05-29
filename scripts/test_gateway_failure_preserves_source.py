"""
test_gateway_failure_preserves_source.py
Verifies that source intake records survive even when hermes_gateway fails.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_gateway_failure_preserves_source ===")

from lib.hermes_telegram_source_intake import HermesTelegramSourceIntake
from pathlib import Path

intake = HermesTelegramSourceIntake()

# 1. Source intake always returns a record even without a gateway
msg = "check this https://www.youtube.com/watch?v=TESTFAILURE123"
record = intake.process(msg, attached_intent=msg)
check("intake returns record on any input", record is not None)
check("intake_id is set", bool(record.intake_id))
check("source_type detected", record.source_type == "youtube_video")
check("status is registered", record.status == "registered")

# 2. Intake log exists on disk after process()
log_path = Path(__file__).resolve().parent.parent / "docs" / "reports" / "intake" / "telegram_source_intake.jsonl"
check("intake log file exists", log_path.exists())
if log_path.exists():
    lines = log_path.read_text().splitlines()
    last = json.loads(lines[-1]) if lines else {}
    check("last log entry matches intake_id", last.get("intake_id") == record.intake_id)

# 3. Gateway failure artifact writer does not crash
from lib.hermes_reasoning_layer import _write_gateway_failure_artifact
_write_gateway_failure_artifact("http://127.0.0.1:8642", "Connection error: test")
evidence_dir = Path(__file__).resolve().parent.parent / "docs" / "reports" / "evidence"
artifacts = list(evidence_dir.glob("hermes_gateway_failure_*.md"))
check("gateway failure artifact created", len(artifacts) > 0)
if artifacts:
    content = artifacts[-1].read_text()
    check("artifact has timestamp", "timestamp:" in content)
    check("artifact does NOT contain raw key", "HERMES_GATEWAY_KEY" not in content)
    check("artifact has next_action", "next_action:" in content)

# 4. reason() with unreachable gateway falls through to evidence_only, not exception
os.environ["HERMES_GATEWAY_URL"] = "http://127.0.0.1:19999"  # nothing here
os.environ["HERMES_GATEWAY_KEY"] = "testkey_fake"
import lib.hermes_provider_policy as pp
pp.get_policy(refresh=True)  # force re-detect with bad URL
from lib.hermes_reasoning_layer import reason
result = reason("test question after gateway failure", evidence_text="")
check("reason() does not raise on gateway failure", True)  # if we get here, no exception
check("fallback result has a reply", bool(result.reply))
check("reply is not empty string", len(result.reply) > 5)

# cleanup
del os.environ["HERMES_GATEWAY_URL"]
del os.environ["HERMES_GATEWAY_KEY"]

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
