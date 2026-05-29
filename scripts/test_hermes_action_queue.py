"""
test_hermes_action_queue.py
Verifies action queue creates and updates actions correctly.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PASS = 0; FAIL = 0

def check(label, cond):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ✅ {label}")
    else:
        FAIL += 1; print(f"  ❌ {label}")

print("=== test_hermes_action_queue ===")

# Use a temp file to avoid polluting real queue
import lib.hermes_action_queue as aq
from pathlib import Path

orig_jsonl = aq._QUEUE_JSONL
orig_md = aq._QUEUE_MD

with tempfile.TemporaryDirectory() as tmpdir:
    aq._QUEUE_JSONL = Path(tmpdir) / "test_queue.jsonl"
    aq._QUEUE_MD = Path(tmpdir) / "test_queue.md"

    try:
        # 1. Create action
        action = aq.create_action(
            title="Test: Process YouTube video",
            description="Assign YouTube video to research scout",
            goal_id="goal_content_engine",
            assigned_scout="youtube_research_scout",
            priority=70,
            autonomous_allowed=True,
            status="queued",
        )
        check("create_action returns Action", action is not None)
        check("action has action_id", bool(action.action_id))
        check("action has created_at", bool(action.created_at))
        check("action title correct", action.title == "Test: Process YouTube video")
        check("action status is queued", action.status == "queued")
        check("action autonomous_allowed", action.autonomous_allowed is True)
        check("action goal_id set", action.goal_id == "goal_content_engine")

        # 2. Create approval-required action
        action2 = aq.create_action(
            title="Publish content to website",
            requires_ray_approval=True,
            approval_reason="public publishing requires approval",
            status="needs_ray_approval",
        )
        check("approval action created", action2 is not None)
        check("approval action requires_ray_approval", action2.requires_ray_approval is True)
        check("approval action status", action2.status == "needs_ray_approval")

        # 3. Load open actions
        open_actions = aq.get_open_actions()
        check("open actions loads list", isinstance(open_actions, list))
        check("2 open actions found", len(open_actions) >= 2)

        # 4. Get pending approval
        approval_needed = aq.get_pending_approval_actions()
        check("pending approval list has 1 action", len(approval_needed) >= 1)
        if approval_needed:
            check("approval action in pending list",
                  any(a.action_id == action2.action_id for a in approval_needed))

        # 5. Top priority actions (autonomous only)
        top = aq.top_priority_actions(limit=5)
        check("top priority actions returns list", isinstance(top, list))
        for a in top:
            check(f"top action '{a.title[:30]}' is autonomous",
                  a.autonomous_allowed is True)

        # 6. Plain English summary
        summary = aq.action_queue_plain_english()
        check("plain English summary non-empty", len(summary) > 20)
        check("summary mentions approval", "approval" in summary.lower() or "ray" in summary.lower())

        # 7. to_plain_english on action
        pe = action.to_plain_english()
        check("action to_plain_english has title", action.title in pe)

    finally:
        aq._QUEUE_JSONL = orig_jsonl
        aq._QUEUE_MD = orig_md

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
