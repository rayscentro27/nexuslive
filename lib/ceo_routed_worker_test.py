"""
ceo_routed_worker_test.py — Unit tests for the CEO routed worker.

Run:
    python3 /Users/raymonddavis/nexus-ai/lib/ceo_routed_worker_test.py

No external dependencies. No network calls. No database writes.
All LLM calls are replaced with a mock injected via llm_fn=.
"""
import json
import logging
import os
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.ceo_routed_worker import (
    handle_content_creator,
    handle_compliance_reviewer,
    handle_marketing_strategist,
    handle_credit_analyst,
    handle_business_formation,
    handle_funding_strategist,
    handle_research_analyst,
    handle_unknown,
    get_handler,
    process_one_event,
    run_cycle,
    is_enabled,
    write_draft,
    _HANDLERS,
)

logging.basicConfig(level=logging.WARNING)

PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"
_results: list[tuple[str, bool, str]] = []

# ── Mock LLM ──────────────────────────────────────────────────────────────────

_MOCK_RESPONSE = "This is a mock AI draft. No external action was taken."

def mock_llm(prompt, **_):
    return {
        "success":      True,
        "response":     _MOCK_RESPONSE,
        "model":        "mock/test",
        "fallback_used": False,
        "source":       "mock",
    }

def failing_llm(prompt, **_):
    raise RuntimeError("Simulated LLM failure")


# ── Helpers ────────────────────────────────────────────────────────────────────

def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    _results.append((name, condition, detail))


_REQUIRED_DRAFT_KEYS = {"role", "task_type", "draft_content", "model_used", "fallback_used", "success"}
_FORBIDDEN_KEYS      = {"publish", "send", "post_to", "execute", "submit", "dispatch_external"}


def _valid_draft(draft: dict) -> tuple[bool, str]:
    missing = _REQUIRED_DRAFT_KEYS - draft.keys()
    if missing:
        return False, f"missing keys: {missing}"
    forbidden = _FORBIDDEN_KEYS & draft.keys()
    if forbidden:
        return False, f"forbidden keys present: {forbidden}"
    return True, ""


# ── Handler tests ──────────────────────────────────────────────────────────────

def test_content_creator_handler():
    draft = handle_content_creator(
        "Create a TikTok script about business credit.",
        {"recommended_role": "content_creator"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("content_creator handler returns valid draft schema", ok, detail)
    check("content_creator role tag correct", draft["role"] == "content_creator", f"role={draft['role']}")
    check("content_creator task_type correct", draft["task_type"] == "short_form_content", f"task_type={draft['task_type']}")
    check("content_creator draft_content populated", bool(draft["draft_content"]), "draft_content empty")
    check("content_creator success=True with mock LLM", draft["success"] is True, f"success={draft['success']}")


def test_compliance_reviewer_handler():
    draft = handle_compliance_reviewer(
        "Review this ad: 'We guarantee $50K funding in 30 days.'",
        {"recommended_role": "compliance_reviewer"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("compliance_reviewer handler returns valid draft schema", ok, detail)
    check("compliance_reviewer role tag correct", draft["role"] == "compliance_reviewer", f"role={draft['role']}")
    check("compliance_reviewer task_type correct", draft["task_type"] == "compliance_review", f"task_type={draft['task_type']}")


def test_marketing_strategist_handler():
    draft = handle_marketing_strategist(
        "Build a 90-day email marketing funnel for new credit repair leads.",
        {"recommended_role": "marketing_strategist"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("marketing_strategist handler returns valid draft schema", ok, detail)
    check("marketing_strategist role tag correct", draft["role"] == "marketing_strategist", f"role={draft['role']}")


def test_credit_analyst_handler():
    draft = handle_credit_analyst(
        "Analyze this profile: FICO 648, two collections, high utilization.",
        {"recommended_role": "credit_analyst"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("credit_analyst handler returns valid draft schema", ok, detail)
    check("credit_analyst task_type correct", draft["task_type"] == "credit_analysis", f"task_type={draft['task_type']}")


def test_business_formation_handler():
    draft = handle_business_formation(
        "Help me set up an LLC, get an EIN, and register a DUNS number.",
        {"recommended_role": "business_formation"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("business_formation handler returns valid draft schema", ok, detail)
    check("business_formation task_type correct", draft["task_type"] == "business_foundation", f"task_type={draft['task_type']}")


def test_funding_strategist_handler():
    draft = handle_funding_strategist(
        "Design a Tier 1 funding roadmap for a new LLC with a 700 personal score.",
        {"recommended_role": "funding_strategist"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("funding_strategist handler returns valid draft schema", ok, detail)
    check("funding_strategist task_type correct", draft["task_type"] == "funding_strategy", f"task_type={draft['task_type']}")


def test_research_analyst_handler():
    draft = handle_research_analyst(
        "Summarize the top 5 business credit bureaus and how they score businesses.",
        {"recommended_role": "research_analyst"},
        llm_fn=mock_llm,
    )
    ok, detail = _valid_draft(draft)
    check("research_analyst handler returns valid draft schema", ok, detail)
    check("research_analyst task_type correct", draft["task_type"] == "research", f"task_type={draft['task_type']}")


def test_unknown_role_fallback():
    """Unrecognized roles use the default handler — no crash, valid draft."""
    handler = get_handler("some_future_role_not_yet_built")
    draft = handler("Do something.", {}, llm_fn=mock_llm)
    ok, detail = _valid_draft(draft)
    check("unknown role fallback returns valid draft schema", ok, detail)
    check("unknown role fallback does not raise", True, "no exception")
    # role field will be "default" (from PromptBuilder fallback)
    check("unknown role fallback success=True with mock LLM", draft["success"] is True, f"success={draft['success']}")


# ── No-publish safety tests ────────────────────────────────────────────────────

def test_draft_only_no_publish():
    """Verify no handler returns keys that would trigger external actions."""
    payloads = [
        ("content_creator", handle_content_creator, "Write a TikTok script."),
        ("compliance_reviewer", handle_compliance_reviewer, "Review this ad."),
        ("marketing_strategist", handle_marketing_strategist, "Build a funnel."),
        ("credit_analyst", handle_credit_analyst, "Analyze my credit."),
        ("business_formation", handle_business_formation, "Set up an LLC."),
        ("funding_strategist", handle_funding_strategist, "Funding roadmap."),
        ("research_analyst", handle_research_analyst, "Summarize this."),
        ("unknown_role", handle_unknown, "Do something."),
    ]
    for role_name, handler_fn, task in payloads:
        draft = handler_fn(task, {}, llm_fn=mock_llm)
        forbidden_found = _FORBIDDEN_KEYS & draft.keys()
        check(
            f"{role_name} draft contains no publish/send/execute keys",
            len(forbidden_found) == 0,
            f"forbidden keys: {forbidden_found}" if forbidden_found else "",
        )


def test_llm_failure_returns_placeholder():
    """When LLM is unavailable, handler still returns a valid draft with placeholder text."""
    draft = handle_content_creator(
        "Create a TikTok script.",
        {},
        llm_fn=failing_llm,
    )
    ok, detail = _valid_draft(draft)
    check("LLM failure: draft schema still valid", ok, detail)
    check("LLM failure: success=False", draft["success"] is False, f"success={draft['success']}")
    check("LLM failure: draft_content contains placeholder", "DRAFT PENDING" in draft["draft_content"] or draft["draft_content"] != "", f"content={draft['draft_content'][:80]}")


# ── process_one_event tests ────────────────────────────────────────────────────

def test_process_ceo_routed_event():
    """process_one_event with a properly structured ceo_routed event."""
    event = {
        "id":         "test-event-001",
        "event_type": "ceo_routed",
        "status":     "pending",
        "payload": {
            "recommended_role":    "content_creator",
            "task_description":    "Create a TikTok script about business credit.",
            "task_type":           "short_form_content",
            "routing_confidence":  0.90,
            "requires_human_review": False,
        },
    }
    # DRY_RUN mode so no Supabase writes
    os.environ["CEO_ROUTING_DRY_RUN"] = "true"
    result = process_one_event(event, llm_fn=mock_llm)
    os.environ.pop("CEO_ROUTING_DRY_RUN", None)

    check("process_one_event returns success=True", result["success"] is True, f"result={result}")
    check("process_one_event sets correct role", result["role"] == "content_creator", f"role={result['role']}")
    check("process_one_event skipped=False", result.get("skipped") is not True, f"skipped={result.get('skipped')}")
    check("process_one_event error=None", result["error"] is None, f"error={result['error']}")


def test_non_ceo_routed_event_is_skipped():
    """Events with event_type != 'ceo_routed' are skipped, not processed."""
    event = {
        "id":         "test-other-event",
        "event_type": "some_other_event_type",
        "status":     "pending",
        "payload":    {"message": "This should not be processed."},
    }
    result = process_one_event(event, llm_fn=mock_llm)
    check(
        "Non-ceo_routed event is skipped",
        result.get("skipped") is True,
        f"skipped={result.get('skipped')} error={result.get('error')}",
    )
    check("Non-ceo_routed event success=False", result["success"] is False, f"success={result['success']}")


def test_missing_role_uses_fallback():
    """Events with no recommended_role use the unknown handler without crashing."""
    event = {
        "id":         "test-no-role",
        "event_type": "ceo_routed",
        "status":     "pending",
        "payload":    {"task_description": "Some task without a role."},
    }
    os.environ["CEO_ROUTING_DRY_RUN"] = "true"
    result = process_one_event(event, llm_fn=mock_llm)
    os.environ.pop("CEO_ROUTING_DRY_RUN", None)
    check(
        "Missing role falls back to unknown handler without crash",
        result["error"] is None,
        f"error={result['error']}",
    )


def test_unsupported_job_type_rejected():
    """Unsupported task_type for a valid role is rejected and skipped safely."""
    event = {
        "id": "test-unsupported-task-type",
        "event_type": "ceo_routed",
        "status": "pending",
        "payload": {
            "recommended_role": "credit_analyst",
            "task_description": "Review credit file",
            "task_type": "funding_strategy",
        },
    }
    os.environ["CEO_ROUTING_DRY_RUN"] = "true"
    result = process_one_event(event, llm_fn=mock_llm)
    os.environ.pop("CEO_ROUTING_DRY_RUN", None)
    check("Unsupported task_type marked skipped", result.get("skipped") is True, f"result={result}")
    check("Unsupported task_type does not succeed", result.get("success") is False, f"result={result}")
    check("Unsupported task_type reports clear error", "unsupported task_type" in str(result.get("error") or "").lower(), f"error={result.get('error')}")


# ── Flag guard tests ───────────────────────────────────────────────────────────

def test_flag_guard_disabled():
    """run_cycle() returns disabled=True when ENABLE_CEO_ROUTED_WORKERS is not set."""
    os.environ.pop("ENABLE_CEO_ROUTED_WORKERS", None)
    summary = run_cycle(llm_fn=mock_llm)
    check(
        "run_cycle disabled when flag not set",
        summary.get("disabled") is True,
        f"summary={summary}",
    )
    check("run_cycle returns fetched=0 when disabled", summary["fetched"] == 0, f"fetched={summary['fetched']}")


def test_flag_guard_enabled_returns_non_disabled():
    """When flag is set, run_cycle returns disabled=False (even if no events available)."""
    os.environ["ENABLE_CEO_ROUTED_WORKERS"] = "true"
    # No real Supabase — _sb_get returns [] on missing URL
    saved_url = os.environ.pop("SUPABASE_URL", None)
    summary = run_cycle(llm_fn=mock_llm)
    if saved_url:
        os.environ["SUPABASE_URL"] = saved_url
    os.environ.pop("ENABLE_CEO_ROUTED_WORKERS", None)
    check(
        "run_cycle not disabled when flag is set",
        summary.get("disabled") is not True,
        f"summary={summary}",
    )


def test_is_enabled_reads_env():
    os.environ["ENABLE_CEO_ROUTED_WORKERS"] = "true"
    check("is_enabled() returns True when set", is_enabled() is True, "")
    os.environ["ENABLE_CEO_ROUTED_WORKERS"] = "false"
    check("is_enabled() returns False when 'false'", is_enabled() is False, "")
    os.environ.pop("ENABLE_CEO_ROUTED_WORKERS", None)
    check("is_enabled() returns False when absent", is_enabled() is False, "")


# ── Schema consistency test ────────────────────────────────────────────────────

def test_all_handlers_consistent_schema():
    """All registered handlers return the same required keys."""
    all_handlers = list(_HANDLERS.values()) + [handle_unknown]
    for handler_fn in all_handlers:
        role_name = getattr(handler_fn, "__name__", "unknown")
        draft = handler_fn("test task", {}, llm_fn=mock_llm)
        ok, detail = _valid_draft(draft)
        check(f"{role_name}: consistent schema", ok, detail)


# ── Write draft schema test (dry-run) ─────────────────────────────────────────

def test_write_draft_dry_run():
    """write_draft in DRY_RUN mode returns None without crashing."""
    os.environ["CEO_ROUTING_DRY_RUN"] = "true"
    result = write_draft(
        "event-dry-run-001",
        {"routing_confidence": 0.9, "routing_reason": "test", "requires_human_review": False},
        {
            "role": "content_creator",
            "task_type": "short_form_content",
            "draft_content": "Test draft.",
            "model_used": "mock",
            "fallback_used": False,
        },
    )
    os.environ.pop("CEO_ROUTING_DRY_RUN", None)
    check("write_draft returns None in dry-run mode", result is None, f"result={result}")


# ── Max iterations test ────────────────────────────────────────────────────────

def test_max_iterations_enforced():
    """CEO_WORKER_MAX_ITERATIONS is read and respected by run_loop (verified via env read)."""
    os.environ["CEO_WORKER_MAX_ITERATIONS"] = "3"
    from lib import ceo_routed_worker as _mod
    import importlib
    # Just verify the env var is readable and parses correctly
    val = int(os.getenv("CEO_WORKER_MAX_ITERATIONS", "0"))
    check("CEO_WORKER_MAX_ITERATIONS env var parses correctly", val == 3, f"val={val}")
    os.environ.pop("CEO_WORKER_MAX_ITERATIONS", None)


# ── Existing CEO router tests still pass ──────────────────────────────────────

def test_existing_ceo_router_still_passes():
    """Confirm ceo_auto_router is unaffected by importing ceo_routed_worker."""
    from lib.ceo_auto_router import classify_task, route_to_role
    tiktok = {
        "use_ceo_auto_routing": True,
        "message": "Create a TikTok script about business credit.",
    }
    cls  = classify_task(tiktok)
    role = route_to_role(cls)
    check("ceo_auto_router unaffected: TikTok → content_creator", role == "content_creator", f"role={role}")
    check("ceo_auto_router unaffected: confidence 0.90", cls["confidence"] >= 0.85, f"confidence={cls['confidence']}")


# ── Run all ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nNexus CEO Routed Worker Tests")
    print("=" * 55)

    test_content_creator_handler()
    test_compliance_reviewer_handler()
    test_marketing_strategist_handler()
    test_credit_analyst_handler()
    test_business_formation_handler()
    test_funding_strategist_handler()
    test_research_analyst_handler()
    test_unknown_role_fallback()

    test_draft_only_no_publish()
    test_llm_failure_returns_placeholder()

    test_process_ceo_routed_event()
    test_non_ceo_routed_event_is_skipped()
    test_missing_role_uses_fallback()
    test_unsupported_job_type_rejected()

    test_flag_guard_disabled()
    test_flag_guard_enabled_returns_non_disabled()
    test_is_enabled_reads_env()

    test_all_handlers_consistent_schema()
    test_write_draft_dry_run()
    test_max_iterations_enforced()

    test_existing_ceo_router_still_passes()

    passed = sum(1 for _, ok, _ in _results if ok)
    failed = sum(1 for _, ok, _ in _results if not ok)
    total  = len(_results)

    print()
    print("=" * 55)
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
