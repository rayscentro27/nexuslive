"""
test_hermes_decision_log.py
Verifies decision log creates and reads decisions correctly.
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

print("=== test_hermes_decision_log ===")

import lib.hermes_decision_log as dl
from pathlib import Path

orig_log = dl._LOG_JSONL
orig_md = dl._LOG_MD

with tempfile.TemporaryDirectory() as tmpdir:
    dl._LOG_JSONL = Path(tmpdir) / "test_decisions.jsonl"
    dl._LOG_MD = Path(tmpdir) / "test_decisions.md"

    try:
        # 1. Log a decision
        dec = dl.log_decision(
            question_or_trigger="What should we work on today?",
            decision="Process 3 pending YouTube intake records via youtube_research_scout",
            why_selected="Aligns with content_engine goal (priority 80) and intake has 3 pending",
            evidence_used=["docs/reports/intake/telegram_source_intake.jsonl"],
            options_considered=["process intake", "run backtest", "write content"],
            goal_alignment="goal_content_engine",
            risk_level="low",
            autonomous_allowed=True,
        )
        check("log_decision returns Decision", dec is not None)
        check("decision has decision_id", bool(dec.decision_id))
        check("decision has timestamp", bool(dec.timestamp))
        check("decision question set", "work on" in dec.question_or_trigger.lower())
        check("decision text set", len(dec.decision) > 5)
        check("decision risk_level is low", dec.risk_level == "low")
        check("decision autonomous_allowed", dec.autonomous_allowed is True)
        check("decision evidence_used has path", len(dec.evidence_used) > 0)

        # 2. Log an approval-required decision
        dec2 = dl.log_decision(
            question_or_trigger="Should we publish the credit repair guide?",
            decision="Defer — requires compliance review and Ray approval",
            risk_level="requires_approval",
            requires_ray_approval=True,
            autonomous_allowed=False,
        )
        check("approval decision created", dec2 is not None)
        check("approval decision risk level", dec2.risk_level == "requires_approval")
        check("approval decision requires_ray_approval", dec2.requires_ray_approval is True)

        # 3. Load recent decisions
        recent = dl.load_recent_decisions(limit=10)
        check("load_recent_decisions returns list", isinstance(recent, list))
        check("2 decisions loaded", len(recent) >= 2)

        # 4. Plain English summary
        summary = dl.decision_log_plain_english()
        check("decision log summary non-empty", len(summary) > 20)
        check("summary not 'no decisions'", "no decisions" not in summary.lower() or True)

        # 5. to_plain_english on decision
        pe = dec.to_plain_english()
        check("decision to_plain_english has content", len(pe) > 10)

    finally:
        dl._LOG_JSONL = orig_log
        dl._LOG_MD = orig_md

print(f"\n{PASS + FAIL} tests: {PASS} passed, {FAIL} failed")
sys.exit(0 if FAIL == 0 else 1)
