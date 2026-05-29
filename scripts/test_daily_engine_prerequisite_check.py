"""test_daily_engine_prerequisite_check.py — verify prerequisite checker works."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
PASS = 0; FAIL = 0
def check(label, cond):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  ✅ {label}")
    else: FAIL += 1; print(f"  ❌ {label}")

print("=== test_daily_engine_prerequisite_check ===")
from scripts.run_daily_engine_prerequisite_check import check_all, EXISTING_RUNNERS, OPERATING_STRUCTURE

result = check_all()
check("check_all returns dict", isinstance(result, dict))
check("has runners list", isinstance(result.get("runners"), list))
check("has operating_structure list", isinstance(result.get("operating_structure"), list))
check("has safe_to_proceed bool", isinstance(result.get("safe_to_proceed"), bool))
check("has checked_at timestamp", bool(result.get("checked_at")))

runners_found = [r for r in result["runners"] if r["exists"]]
check("at least 5 runners found", len(runners_found) >= 5)

struct_ok = [s for s in result["operating_structure"] if s["exists"]]
check("all 14 operating structure files present", len(struct_ok) == len(OPERATING_STRUCTURE))
check("safe to proceed (no blockers)", result["safe_to_proceed"])
check("no blockers", len(result["blockers"]) == 0)

# Check specific critical files
paths = {r["path"] for r in result["runners"]}
check("run_hermes_operating_loop.py found", "scripts/run_hermes_operating_loop.py" in paths)
check("run_youtube_intelligence_cycle.py found", "scripts/run_youtube_intelligence_cycle.py" in paths)

struct_paths = {s["path"] for s in result["operating_structure"]}
check("hermes_action_queue.py in structure", "lib/hermes_action_queue.py" in struct_paths)
check("nexus_artifact_registry.py in structure", "lib/nexus_artifact_registry.py" in struct_paths)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
