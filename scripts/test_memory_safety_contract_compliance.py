"""
test_memory_safety_contract_compliance.py
Verifies all rules of the Hermes Memory Safety Contract.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.hermes_executive_memory as em
import lib.hermes_response_quality as rq
from lib.hermes_active_memory_reader import (
    load_active_memory,
    build_telegram_context as safe_build_context,
)


STALE_MARKERS = ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter"]


def check_no_stale(text: str, label: str):
    for m in STALE_MARKERS:
        assert m not in text, f"RULE VIOLATION: stale marker '{m}' in {label}: {text[:100]}"


def test_rule1_no_stale_defaults_in_live_paths():
    """Rule 1: load_memory() must return empty/neutral when no live data."""
    mem = em.load_memory(force_refresh=True)
    problems = " ".join(mem.get("infrastructure_problems", []))
    unfinished = " ".join(mem.get("unfinished_systems", []))
    check_no_stale(problems, "load_memory().infrastructure_problems")
    check_no_stale(unfinished, "load_memory().unfinished_systems")


def test_rule2_archived_defaults_not_in_live():
    """Rule 2: load_archived_executive_memory_defaults() NOT reachable from load_memory()."""
    archived = em.load_archived_executive_memory_defaults()
    live = em.load_memory(force_refresh=True)
    for cat in ["infrastructure_problems", "unfinished_systems"]:
        arch_items = archived.get(cat, [])
        live_items = live.get(cat, [])
        if arch_items:
            assert arch_items != live_items, (
                f"Rule 2 violation: archived {cat} == live {cat}"
            )


def test_rule3_active_memory_reader_is_entry_point():
    """Rule 3: active memory reader used for Telegram context."""
    ctx = safe_build_context(max_chars=400)
    check_no_stale(ctx, "build_telegram_context()")


def test_rule4_quality_escalation_no_stale():
    """Rule 4: Quality escalation fallback returns clean clarification."""
    result = rq._fallback_data_block(
        "something totally random test here",
        "Ollama OFFLINE\nBeehiiv pending\nYouTube Studio not configured",
    )
    check_no_stale(result, "_fallback_data_block")
    assert "specific question" in result.lower() or "nexus ceo briefing" in result.lower()


def test_rule5_memory_writes_log_source():
    """Rule 5: update_category requires source parameter."""
    import inspect
    sig = inspect.signature(em.update_category)
    assert "source" in sig.parameters, "update_category() missing 'source' parameter"
    assert sig.parameters["source"].default == "user"


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
