"""
test_verified_approval_queue.py
================================
Verify that handoff_check reads ONLY real artifact files.
No pending handoffs = no invented approval items.
"""
import sys
import json
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def check(desc: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  ✅ {desc}")
        PASS += 1
    else:
        print(f"  ❌ FAIL: {desc}")
        FAIL += 1


print("\n=== test_verified_approval_queue ===\n")

# Test 1: _run_handoff_check with no files → "No pending handoffs"
from hermes_command_router.router import _run_handoff_check
import glob as _glob
import os

# Point to a temp empty dir by monkey-patching _nexus_ai_root
original_root = None
try:
    import hermes_command_router.router as _router
    original_root = _router._nexus_ai_root

    with tempfile.TemporaryDirectory() as tmpdir:
        _router._nexus_ai_root = lambda: tmpdir
        # No files in tmpdir → no handoffs
        status, evidence, rec = _run_handoff_check()
        check("empty dir → 'No pending handoffs'",
              any("no pending" in e.lower() for e in evidence) or status == "healthy")
        check("status is healthy when no handoffs", status == "healthy")

    # Test 2: with one pending_ray handoff file
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_dir = Path(tmpdir) / "docs" / "reports" / "hermes_handoffs"
        handoff_dir.mkdir(parents=True)
        handoff_file = handoff_dir / "handoff_test_001.json"
        handoff_file.write_text(json.dumps({
            "handoff_id": "test_001",
            "status": "pending_ray",
            "title": "Review Beehiiv alternative",
            "action_required": "Approve Ghost self-hosted as newsletter tool replacement",
        }))
        _router._nexus_ai_root = lambda: tmpdir
        status2, evidence2, rec2 = _run_handoff_check()
        check("pending_ray file detected", status2 == "warning")
        check("handoff title appears in evidence",
              any("Beehiiv" in e or "Ghost" in e or "Review" in e for e in evidence2))
        check("recommendation mentions approval",
              "approval" in rec2.lower())

    # Test 3: with a "completed" handoff (should NOT appear)
    with tempfile.TemporaryDirectory() as tmpdir:
        handoff_dir = Path(tmpdir) / "docs" / "reports" / "hermes_handoffs"
        handoff_dir.mkdir(parents=True)
        handoff_file = handoff_dir / "handoff_completed_001.json"
        handoff_file.write_text(json.dumps({
            "handoff_id": "completed_001",
            "status": "completed",
            "title": "Old completed handoff",
        }))
        _router._nexus_ai_root = lambda: tmpdir
        status3, evidence3, _ = _run_handoff_check()
        check("completed handoff NOT shown as pending",
              not any("Old completed" in e for e in evidence3))
        check("status is healthy when only completed handoffs", status3 == "healthy")

finally:
    if original_root:
        _router._nexus_ai_root = original_root

# Test 4: HermesActionHandoff.pending_handoffs() returns list
try:
    from lib.hermes_action_handoff import HermesActionHandoff
    handoff_service = HermesActionHandoff()
    pending = handoff_service.pending_handoffs()
    check("pending_handoffs() returns a list", isinstance(pending, list))
    check("pending_handoffs() items are dicts", all(isinstance(h, dict) for h in pending))
except Exception as e:
    print(f"  [SKIP] HermesActionHandoff: {e}")

print(f"\nResults: {PASS} passed, {FAIL} failed")
if FAIL:
    sys.exit(1)
