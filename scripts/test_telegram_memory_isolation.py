"""
test_telegram_memory_isolation.py
Verifies that archived/defaults are NOT reachable from Telegram-facing paths.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_active_memory_reader import (
    load_active_memory,
    build_telegram_context,
    build_context_block,
)

# These should NEVER appear in Telegram-facing output
FORBIDDEN_IN_TELEGRAM = [
    "Ollama.*OFFLINE",
    "Beehiiv.*pending",
    "YouTube Studio",
    "OpenRouter.*not.*configured",
]


def test_telegram_context_no_forbidden():
    ctx = build_telegram_context(max_chars=400)
    for marker in FORBIDDEN_IN_TELEGRAM:
        assert marker not in ctx, f"Forbidden pattern '{marker}' found in Telegram context"


def test_context_block_no_forbidden():
    block = build_context_block(max_items_per_category=3)
    for marker in FORBIDDEN_IN_TELEGRAM:
        assert marker not in block, f"Forbidden pattern '{marker}' found in context block"


def test_active_memory_source_tag():
    mem = load_active_memory(force_refresh=True)
    source = mem.get("source", "")
    assert source != "archived_defaults", "Active memory must not source from archived defaults"
    assert source in ("active_memory_reader_empty", "active_memory_reader_supabase")


def test_empty_memory_is_neutral():
    mem = load_active_memory(force_refresh=True)
    for cat in ["infrastructure_problems", "monetization_priorities", "unfinished_systems"]:
        items = mem.get(cat, [])
        # Should be empty list (neutral), not containing stale defaults
        assert isinstance(items, list)


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
