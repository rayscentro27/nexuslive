"""
test_final_response_gate.py
Verify hermes_final_response_gate.py blocks unsupported operational claims.
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


from lib.hermes_final_response_gate import inspect, gate, GateResult


def test_clean_text_passes():
    result = inspect("I'm online and ready. Ask me to run a status check.")
    if result.passed:
        ok("clean_text_passes")
    else:
        fail("clean_text_passes", f"blocked: {result.blocked_reasons}")


def test_nitrotrades_blocked():
    result = inspect("NitroTrades system is reporting 6 signals today.")
    if not result.passed and "fabricated_task_name_nitrotrades" in result.blocked_reasons:
        ok("nitrotrades_blocked")
    else:
        fail("nitrotrades_blocked", f"passed={result.passed} reasons={result.blocked_reasons}")


def test_approval_count_blocked():
    result = inspect("You have 6 pending approvals waiting for your review.")
    if not result.passed and "fabricated_approval_count" in result.blocked_reasons:
        ok("approval_count_blocked")
    else:
        fail("approval_count_blocked", f"passed={result.passed} reasons={result.blocked_reasons}")


def test_approval_count_2_blocked():
    result = inspect("There are 3 items that need approval before deployment.")
    if not result.passed:
        ok("approval_count_2_blocked")
    else:
        fail("approval_count_2_blocked", "should have been blocked")


def test_sba_deadline_blocked():
    result = inspect("The SBA deadline is July 15 for this grant application.")
    if not result.passed and "fabricated_sba_deadline" in result.blocked_reasons:
        ok("sba_deadline_blocked")
    else:
        fail("sba_deadline_blocked", f"passed={result.passed} reasons={result.blocked_reasons}")


def test_slide_reference_blocked():
    result = inspect("As shown in Slide 12 of the presentation deck.")
    if not result.passed and "fabricated_slide_reference" in result.blocked_reasons:
        ok("slide_reference_blocked")
    else:
        fail("slide_reference_blocked", f"passed={result.passed} reasons={result.blocked_reasons}")


def test_no_verified_data_is_safe_override():
    result = inspect("No verified data for that yet. Ask me to run a status check.")
    if result.passed:
        ok("no_verified_data_is_safe_override")
    else:
        fail("no_verified_data_is_safe_override", f"blocked: {result.blocked_reasons}")


def test_evidence_packet_text_is_safe():
    text = "Evidence collected at 2026-05-28:\n  [verified_file] report: nexus_status.json"
    result = inspect(text)
    if result.passed:
        ok("evidence_packet_text_is_safe")
    else:
        fail("evidence_packet_text_is_safe", f"blocked: {result.blocked_reasons}")


def test_gate_warn_mode_delivers_original():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"HERMES_FINAL_GATE_ACTION": "warn"}, clear=False):
        # reimport to pick up env
        import importlib
        import lib.hermes_final_response_gate as fg
        importlib.reload(fg)
        text = "NitroTrades system is active."
        safe = fg.gate(text)
        # In warn mode, original is delivered (but logged)
        if safe == text:
            ok("gate_warn_mode_delivers_original")
        else:
            fail("gate_warn_mode_delivers_original", f"text was modified in warn mode")
        importlib.reload(fg)  # reset


def test_gate_block_mode_replaces_text():
    import os
    from unittest.mock import patch
    import importlib
    import lib.hermes_final_response_gate as fg
    original_action = fg.GATE_ACTION
    fg.GATE_ACTION = "block"
    text = "You have 6 pending approvals right now."
    safe = fg.gate(text)
    fg.GATE_ACTION = original_action
    if safe != text and "verified" in safe.lower():
        ok("gate_block_mode_replaces_text")
    else:
        fail("gate_block_mode_replaces_text", f"safe='{safe[:80]}'")


def test_inspect_returns_gate_result():
    result = inspect("Hello, I am online.")
    if type(result).__name__ == "GateResult":
        ok("inspect_returns_gate_result")
    else:
        fail("inspect_returns_gate_result", f"got {type(result)}")


def test_gate_disabled_env():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {"HERMES_FINAL_GATE_ENABLED": "false"}, clear=False):
        import importlib
        import lib.hermes_final_response_gate as fg
        importlib.reload(fg)
        text = "NitroTrades has 6 pending approvals."
        safe = fg.gate(text)
        if safe == text:
            ok("gate_disabled_env — gate passes through when disabled")
        else:
            fail("gate_disabled_env", "gate modified text when disabled")
        importlib.reload(fg)


if __name__ == "__main__":
    print("=== test_final_response_gate ===")
    test_clean_text_passes()
    test_nitrotrades_blocked()
    test_approval_count_blocked()
    test_approval_count_2_blocked()
    test_sba_deadline_blocked()
    test_slide_reference_blocked()
    test_no_verified_data_is_safe_override()
    test_evidence_packet_text_is_safe()
    test_gate_warn_mode_delivers_original()
    test_gate_block_mode_replaces_text()
    test_inspect_returns_gate_result()
    test_gate_disabled_env()

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
