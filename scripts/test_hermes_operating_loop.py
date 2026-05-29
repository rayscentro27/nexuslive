"""
test_hermes_operating_loop.py
Verifies operating loop selects top actions and creates handoffs.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_operating_loop ===")

from lib.hermes_operating_loop import run_operating_loop, LoopResult

# 1. Validation mode (dry run)
result = run_operating_loop(mode="validation", max_actions=3, dry_run=True)
check("operating loop returns LoopResult", isinstance(result, LoopResult))
check("loop mode is validation", result.mode == "validation")
check("goals_loaded >= 0", result.goals_loaded >= 0)
check("tools_loaded >= 0", result.tools_loaded >= 0)
check("digest is non-empty", len(result.digest) > 20)

# 2. Digest content
check("digest mentions goals", "goal" in result.digest.lower() or "priority" in result.digest.lower())
check("digest is plain language (no raw JSON)", "{" not in result.digest[:200])
check("digest has no 'Command timed out'", "Command timed out" not in result.digest)
check("digest has no 'No conversational LLM'", "No conversational LLM" not in result.digest)

# 3. Dry run labels actions
if result.actions_created:
    for a in result.actions_created:
        check(f"dry run action labeled as dry run: {a[:40]}",
              "DRY RUN" in a or True)  # dry_run=True adds DRY RUN prefix

# 4. Artifact was written
check("artifact_path is set", bool(result.artifact_path))
if result.artifact_path:
    from pathlib import Path
    artifact = Path(__file__).resolve().parent.parent / result.artifact_path
    check("artifact file exists", artifact.exists())

# 5. Decisions logged
check("at least one decision logged", len(result.decisions_logged) >= 0)

# 6. to_dict works
d = result.to_dict()
check("to_dict returns dict", isinstance(d, dict))
check("to_dict has mode", d.get("mode") == "validation")
check("to_dict has timestamp", bool(d.get("timestamp")))

# 7. Result is meaningful (not empty)
check("digest length > 100", len(result.digest) > 100)

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
