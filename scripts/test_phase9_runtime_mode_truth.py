"""test_phase9_runtime_mode_truth.py — runtime truth report exists and resolves the memory discrepancy."""
import sys

from phase9_test_helpers import latest_json

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


data = latest_json("docs/reports/audits/hermes_runtime_mode_truth_*.json")
check("report type present", data.get("report_type") == "hermes_runtime_mode_truth")
check("telegram pid present", bool(data.get("telegram_pid")))
check("launchd requests memory primary", data.get("requested_modes", {}).get("HERMES_MEMORY_V2_MODE") == "primary")
check("effective memory mode recorded", bool(data.get("effective_modes", {}).get("memory_v2_effective_mode")))
check("discrepancy explanation present", bool(data.get("memory_v2_discrepancy_resolution")))
check("limited primary active recorded", data.get("effective_modes", {}).get("phase8c_limited_primary_active") is True)

print(f"\nPhase 9 runtime mode truth: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
