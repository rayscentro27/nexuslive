"""
test_draft_recommendation_engine.py
Tests for hermes_draft_recommendation_engine evaluation and formatting.
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_draft_recommendation_engine import (
    evaluate_checklist_draft,
    recommend_next_step_for_draft,
    format_draft_recommendation_response,
    format_action_recommendation_response,
    format_opportunity_recommendation_response,
)

SIMPLIFIED_DRAFT = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*

## Start Here

Work through these in order.

## Who This Checklist Is For

Business owners who want to apply for business funding.

## 1. Business Setup Readiness

- [ ] **Business entity formed** — LLC, S-Corp, or C-Corp (LLC is most common)
- [ ] **EIN obtained** — business Tax ID (free at irs.gov)
- [ ] **Business bank account** — keep business and personal money separate
- [ ] **Business address** — real street address

## 2. Credit Profile Readiness

- [ ] **Know your score** — check your current credit score
- [ ] **Credit utilization** — credit card balances below 30%
- [ ] **No recent collections** — no missed payments in last 12 months

## 3. Banking Readiness

- [ ] **6 months history** — consistent deposits for 6+ months
- [ ] **No overdrafts** — no overdrafts in last 3 months

## Compliance Note

*This checklist is for educational purposes only.*

## Nexus Next Step

Use Nexus to track your readiness.

*Internal draft — 20260531_130000_000 UTC — Simplified Edition — Pending Ray's review and approval before any use.*
"""

CLEANED_DRAFT = """\
# Credit/Funding Readiness Checklist
*(Simplified — Plain English Edition)*

## Start Here

Work through these in order.

## Who This Checklist Is For

Business owners.

## 1. Business Setup Readiness

- [ ] **Business entity formed**
- [ ] **EIN obtained**

## Compliance Note

*Educational purposes only.*

*Internal draft — 20260531_140000_000 UTC — Cleaned Edition — Pending Ray's review and approval before any use.*
"""

LEAD_MAGNET_DRAFT = """\
# Credit & Funding Readiness Scorecard

## Score Yourself

- [ ] Business entity: 1 point
- [ ] EIN: 1 point

## What Your Score Means

25+ points: ready.

## Nexus Next Step

Use Nexus.

*Educational purposes only.*
"""


def test_evaluate_simplified_recommends_lead_magnet():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "simplified.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = evaluate_checklist_draft(path)
    assert result["recommendation"] == "lead_magnet"


def test_evaluate_cleaned_recommends_lead_magnet():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cleaned.md"
        path.write_text(CLEANED_DRAFT)
        result = evaluate_checklist_draft(path)
    assert result["recommendation"] == "lead_magnet"


def test_evaluate_lead_magnet_recommends_video_script():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "lead_magnet.md"
        path.write_text(LEAD_MAGNET_DRAFT)
        result = evaluate_checklist_draft(path)
    assert result["recommendation"] == "short_video_script"


def test_evaluate_missing_file_returns_error():
    path = Path("/tmp/nonexistent_draft_12345.md")
    result = evaluate_checklist_draft(path)
    assert "error" in result


def test_evaluate_detects_compliance():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = evaluate_checklist_draft(path)
    assert result["has_compliance"] is True


def test_evaluate_detects_is_simplified():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = evaluate_checklist_draft(path)
    assert result["is_simplified"] is True


def test_evaluate_what_is_good_not_empty():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = evaluate_checklist_draft(path)
    assert len(result["what_is_good"]) > 0


def test_recommend_returns_result_dict():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
    assert "recommendation" in result
    assert "simple_answer" in result
    assert "next_move" in result


def test_recommend_missing_file():
    result = recommend_next_step_for_draft(Path("/tmp/no_such_file_abc.md"))
    assert "error" in result


def test_format_response_has_recommendation_header():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "RECOMMENDATION" in resp


def test_format_response_has_simple_answer():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Simple answer:" in resp
    assert "I recommend" in resp


def test_format_response_has_next_best_move():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Next best move:" in resp


def test_format_response_has_approval_boundary():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Approval" in resp
    assert "publishing" in resp.lower() or "approval required" in resp.lower()


def test_format_response_has_evidence_path():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Evidence:" in resp


def test_format_response_has_reply_options():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "Reply options:" in resp


def test_format_response_no_evidence_dump():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "draft.md"
        path.write_text(SIMPLIFIED_DRAFT)
        result = recommend_next_step_for_draft(path)
        resp = format_draft_recommendation_response(result)
    assert "strategic context from evidence" not in resp.lower()
    assert "artifact_inventory" not in resp.lower()
    assert "OFFLINE" not in resp
    assert "Beehiiv" not in resp


def test_format_error_response():
    result = {"error": "file not found", "path": "/tmp/bad.md"}
    resp = format_draft_recommendation_response(result)
    assert "could not evaluate" in resp.lower() or "I could not" in resp


def test_action_recommendation_response():
    ctx = {
        "primary_object_type": "action",
        "primary_object_title": "Review checklist draft",
        "primary_object_status": "pending",
        "primary_object_path": "docs/reports/actions/act_001.json",
    }
    resp = format_action_recommendation_response(ctx)
    assert "RECOMMENDATION" in resp
    assert "Next best move:" in resp
    assert "Approval" in resp


def test_opportunity_recommendation_response():
    ctx = {
        "primary_object_type": "opportunity",
        "primary_object_title": "Credit repair lead magnet",
        "primary_object_path": "docs/opportunities/opp_001.json",
    }
    resp = format_opportunity_recommendation_response(ctx)
    assert "RECOMMENDATION" in resp
    assert "Next best move:" in resp
    assert "Approval" in resp


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(failed)
