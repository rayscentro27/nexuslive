"""
test_active_memory_reader_smoke.py
Verifies the active memory reader returns empty/neutral (not stale defaults).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_active_memory_reader import (
    load_active_memory,
    build_telegram_context,
    build_context_block,
    status_summary,
    active_memory_available,
)


def test_load_active_memory_returns_dict():
    mem = load_active_memory(force_refresh=True)
    assert isinstance(mem, dict)
    assert "infrastructure_problems" in mem
    assert "monetization_priorities" in mem


def test_load_active_memory_no_stale_defaults():
    mem = load_active_memory(force_refresh=True)
    for cat in ["infrastructure_problems", "monetization_priorities"]:
        items = mem.get(cat, [])
        for item in items:
            assert "Ollama" not in item, f"Stale Ollama default leaked in {cat}"
            assert "Beehiiv" not in item, f"Stale Beehiiv default leaked in {cat}"
            assert "OpenRouter" not in item, f"Stale OpenRouter default leaked in {cat}"


def test_build_telegram_context_no_stale():
    ctx = build_telegram_context(max_chars=400)
    assert "Ollama" not in ctx
    assert "Beehiiv" not in ctx


def test_build_context_block_no_stale():
    block = build_context_block(max_items_per_category=3)
    assert "Ollama" not in block
    assert "Beehiiv" not in block


def test_status_summary_available():
    summary = status_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_active_memory_available_returns_bool():
    avail = active_memory_available()
    assert isinstance(avail, bool)


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
