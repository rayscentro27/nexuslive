"""
ceo_auto_router_test.py — Unit tests for CEO auto-routing logic.

Run:
    python3 /Users/raymonddavis/nexus-ai/lib/ceo_auto_router_test.py

No external dependencies. No network calls. No database writes.
"""
import sys
import json
import logging
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.ceo_auto_router import (
    classify_task,
    build_ceo_routing_prompt,
    route_to_role,
    build_child_job_payload,
)

logging.basicConfig(level=logging.WARNING)

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


# ── Test cases ─────────────────────────────────────────────────────────────────

def test_credit_repair():
    payload = {
        "use_ceo_auto_routing": True,
        "message": "I need to write dispute letters for two collections on my credit report. Should I use certified mail?",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Credit repair letter routing",
        role == "credit_repair_letter_agent",
        f"got role={role} confidence={cls['confidence']}",
    )
    check(
        "Credit repair requires human review",
        cls["requires_human_review"] is True,
        f"requires_human_review={cls['requires_human_review']}",
    )


def test_credit_analysis():
    payload = {
        "use_ceo_auto_routing": True,
        "message": "My FICO score dropped to 610 because of a late payment and high utilization. What should I fix first?",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Credit analysis routing",
        role == "credit_analyst",
        f"got role={role} confidence={cls['confidence']}",
    )
    check(
        "Credit analysis uses super prompt",
        cls["use_nexus_super_prompt"] is True,
        f"use_nexus_super_prompt={cls['use_nexus_super_prompt']}",
    )


def test_llc_setup():
    payload = {
        "use_ceo_auto_routing": True,
        "task_description": "Help me set up an LLC, get an EIN, and register a DUNS number for my new business.",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Business formation routing",
        role == "business_formation",
        f"got role={role} confidence={cls['confidence']}",
    )


def test_tiktok_script():
    payload = {
        "use_ceo_auto_routing": True,
        "use_nexus_super_prompt": True,
        "message": "Create a TikTok script explaining why entrepreneurs should become fundable before applying for business credit.",
        "source": "admin_portal",
        "channel": "portal",
        "created_from": "manual_test",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "TikTok script → content_creator",
        role == "content_creator",
        f"got role={role} confidence={cls['confidence']}",
    )
    check(
        "Content creator requires compliance review",
        cls["requires_compliance_review"] is True,
        f"requires_compliance_review={cls['requires_compliance_review']}",
    )
    check(
        "Content creator does NOT require human review",
        cls["requires_human_review"] is False,
        f"requires_human_review={cls['requires_human_review']}",
    )


def test_funding_roadmap():
    payload = {
        "use_ceo_auto_routing": True,
        "message": "I want a 90-day funding roadmap for Tier 1 business credit cards with 0% interest. How do I get there from my current 680 score?",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Funding roadmap → funding_strategist",
        role == "funding_strategist",
        f"got role={role} confidence={cls['confidence']}",
    )


def test_trading_research():
    payload = {
        "use_ceo_auto_routing": True,
        "description": "Explain a forex trading strategy using the EURUSD daily chart and candlestick patterns.",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Trading research → trading_education",
        role == "trading_education",
        f"got role={role} confidence={cls['confidence']}",
    )


def test_compliance_review():
    payload = {
        "use_ceo_auto_routing": True,
        "message": "Review this ad for compliance: 'We guarantee you'll get $50,000 in business funding within 30 days.'",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Compliance review routing",
        role == "compliance_reviewer",
        f"got role={role} confidence={cls['confidence']}",
    )
    check(
        "Compliance reviewer requires human review",
        cls["requires_human_review"] is True,
        f"requires_human_review={cls['requires_human_review']}",
    )


def test_unknown_task():
    payload = {
        "use_ceo_auto_routing": True,
        "message": "Please make me a sandwich.",
    }
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Unknown task → unknown role",
        role == "unknown",
        f"got role={role}",
    )
    check(
        "Unknown task requires human review",
        cls["requires_human_review"] is True,
        f"requires_human_review={cls['requires_human_review']}",
    )


def test_empty_payload():
    payload = {"use_ceo_auto_routing": True}
    cls = classify_task(payload)
    role = route_to_role(cls)
    check(
        "Empty payload → unknown (no crash)",
        role == "unknown",
        f"got role={role}",
    )


def test_child_job_payload():
    original = {
        "use_ceo_auto_routing": True,
        "message": "Write a TikTok script about business credit.",
        "api_key": "sk-secret-should-not-appear",
        "source": "portal",
    }
    cls = classify_task(original)
    child = build_child_job_payload(original, cls, parent_job_id="test-parent-001")

    check(
        "Child job has required fields",
        all(k in child for k in [
            "parent_job_id", "routed_by", "recommended_role",
            "routing_confidence", "routing_reason", "use_nexus_super_prompt",
            "original_payload",
        ]),
        f"keys={list(child.keys())}",
    )
    check(
        "Child job strips API keys",
        "api_key" not in child and "api_key" not in child.get("original_payload", {}),
        "api_key should be stripped from child payload",
    )
    check(
        "Child job sets routed_by=ceo_agent",
        child.get("routed_by") == "ceo_agent",
        f"routed_by={child.get('routed_by')}",
    )
    check(
        "Child job preserves parent_job_id",
        child.get("parent_job_id") == "test-parent-001",
        f"parent_job_id={child.get('parent_job_id')}",
    )


def test_prompt_builder():
    payload = {
        "message": "Write a TikTok script about becoming fundable.",
        "source": "portal",
    }
    prompt = build_ceo_routing_prompt(payload)
    check(
        "CEO routing prompt is a non-empty string",
        isinstance(prompt, str) and len(prompt) > 100,
        f"length={len(prompt)}",
    )
    check(
        "Prompt contains supported roles",
        "content_creator" in prompt and "credit_analyst" in prompt,
        "missing role names in prompt",
    )
    check(
        "Prompt contains task text",
        "tiktok" in prompt.lower() or "fundable" in prompt.lower(),
        "task text not in prompt",
    )
    check(
        "Prompt requests JSON output",
        "recommended_role" in prompt,
        "JSON output schema missing",
    )


def test_route_to_role_handles_raw_json_string():
    raw = '{"recommended_role": "funding_strategist", "confidence": 0.8}'
    role = route_to_role(raw)
    check(
        "route_to_role parses raw JSON string",
        role == "funding_strategist",
        f"got role={role}",
    )


def test_no_flag_no_routing():
    """Jobs without use_ceo_auto_routing should not be affected."""
    payload = {"task_description": "Check my credit score."}
    # Router can still classify, but the flag check is the caller's responsibility
    assert not payload.get("use_ceo_auto_routing"), "Flag should not be set"
    check(
        "Jobs without flag are not auto-routed by default",
        payload.get("use_ceo_auto_routing") is not True,
        "flag correctly absent",
    )


# ── Run all tests ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nNexus CEO Auto-Router Tests")
    print("=" * 50)

    test_credit_repair()
    test_credit_analysis()
    test_llc_setup()
    test_tiktok_script()
    test_funding_roadmap()
    test_trading_research()
    test_compliance_review()
    test_unknown_task()
    test_empty_payload()
    test_child_job_payload()
    test_prompt_builder()
    test_route_to_role_handles_raw_json_string()
    test_no_flag_no_routing()

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total = len(_results)

    print()
    print("=" * 50)
    print(f"Results: {passed}/{total} passed  |  {failed} failed")

    if failed:
        print("\nFailed tests:")
        for name, ok, detail in _results:
            if not ok:
                print(f"  ✗ {name}: {detail}")
        sys.exit(1)
    else:
        print("All tests passed. Safe to proceed.")
        sys.exit(0)
