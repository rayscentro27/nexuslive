"""test_phase9_command_cleanup_plan_exists.py — command cleanup plan exists with priority candidates."""
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


data = latest_json("docs/reports/audits/hermes_command_cleanup_plan_*.json")
candidates = data.get("top_cleanup_candidates") or []
summary = data.get("summary") or {}
check("report type present", data.get("report_type") == "hermes_command_cleanup_plan")
check("cleanup candidates >= 50", len(candidates) >= 50)
check("summary includes inventory size", int(summary.get("inventory_count", 0)) >= 1000)
check("summary includes classification counts", len(summary.get("classification_counts", {})) >= 3)

print(f"\nPhase 9 command cleanup plan exists: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
