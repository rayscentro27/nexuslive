"""
test_telegram_provider_status_commands.py
Verify intake + router handle provider/brain status commands correctly.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


from hermes_command_router.intake import classify_intent


def test_what_brain_routes_to_provider_status():
    intent, priority, _ = classify_intent("what brain are you using?")
    if intent == "provider_status":
        ok("what_brain_routes_to_provider_status")
    else:
        fail("what_brain_routes_to_provider_status", f"got intent={intent}")


def test_show_provider_status_routes():
    intent, priority, _ = classify_intent("show provider status")
    if intent == "provider_status":
        ok("show_provider_status_routes")
    else:
        fail("show_provider_status_routes", f"got intent={intent}")


def test_are_you_using_openrouter_routes():
    intent, priority, _ = classify_intent("are you using OpenRouter right now?")
    if intent == "provider_status":
        ok("are_you_using_openrouter_routes")
    else:
        fail("are_you_using_openrouter_routes", f"got intent={intent}")


def test_are_you_using_chatgpt_routes():
    intent, priority, _ = classify_intent("are you using ChatGPT auth?")
    if intent == "provider_status":
        ok("are_you_using_chatgpt_routes")
    else:
        fail("are_you_using_chatgpt_routes", f"got intent={intent}")


def test_which_llm_routes():
    intent, priority, _ = classify_intent("which llm are you using?")
    if intent == "provider_status":
        ok("which_llm_routes")
    else:
        fail("which_llm_routes", f"got intent={intent}")


def test_disable_openrouter_routes():
    intent, priority, _ = classify_intent("disable OpenRouter fallback")
    if intent == "provider_status":
        ok("disable_openrouter_routes")
    else:
        fail("disable_openrouter_routes", f"got intent={intent}")


def test_brain_status_routes():
    intent, priority, _ = classify_intent("brain status")
    if intent == "provider_status":
        ok("brain_status_routes")
    else:
        fail("brain_status_routes", f"got intent={intent}")


def test_provider_status_handler_in_router():
    from hermes_command_router.router import _INTENT_HANDLERS
    if "provider_status" in _INTENT_HANDLERS:
        ok("provider_status_handler_in_router")
    else:
        fail("provider_status_handler_in_router", "provider_status not in _INTENT_HANDLERS")


def test_run_provider_status_returns_tuple():
    from hermes_command_router.router import _run_provider_status
    status, evidence, rec = _run_provider_status()
    if isinstance(status, str) and isinstance(evidence, list) and isinstance(rec, str):
        ok(f"run_provider_status_returns_tuple — status={status}")
    else:
        fail("run_provider_status_returns_tuple", f"status={status} evidence={evidence[:1]}")


def test_run_provider_status_evidence_has_strategic():
    from hermes_command_router.router import _run_provider_status
    status, evidence, rec = _run_provider_status()
    has_strategic = any("strategic_provider" in e for e in evidence)
    if has_strategic:
        ok("run_provider_status_evidence_has_strategic")
    else:
        fail("run_provider_status_evidence_has_strategic", f"evidence: {evidence[:3]}")


def test_run_provider_status_openrouter_mention():
    from hermes_command_router.router import _run_provider_status
    status, evidence, rec = _run_provider_status()
    has_openrouter = any("openrouter" in e.lower() for e in evidence)
    if has_openrouter:
        ok("run_provider_status_openrouter_mention")
    else:
        fail("run_provider_status_openrouter_mention", f"evidence does not mention openrouter: {evidence}")


if __name__ == "__main__":
    print("=== test_telegram_provider_status_commands ===")
    test_what_brain_routes_to_provider_status()
    test_show_provider_status_routes()
    test_are_you_using_openrouter_routes()
    test_are_you_using_chatgpt_routes()
    test_which_llm_routes()
    test_disable_openrouter_routes()
    test_brain_status_routes()
    test_provider_status_handler_in_router()
    test_run_provider_status_returns_tuple()
    test_run_provider_status_evidence_has_strategic()
    test_run_provider_status_openrouter_mention()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
