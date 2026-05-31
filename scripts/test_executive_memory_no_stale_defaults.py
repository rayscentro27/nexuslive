"""
test_executive_memory_no_stale_defaults.py
Verifies that load_memory() returns empty/neutral, not archived stale defaults.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.hermes_executive_memory import (
    load_memory,
    load_archived_executive_memory_defaults,
)


STALE_MARKERS = ["Ollama", "Beehiiv", "OpenRouter", "YouTube Studio"]


def test_load_memory_does_not_contain_stale_defaults():
    mem = load_memory(force_refresh=True)
    for cat in ["infrastructure_problems", "unfinished_systems", "monetization_priorities"]:
        items = mem.get(cat, [])
        for item in items:
            for marker in STALE_MARKERS:
                assert marker not in item, (
                    f"Stale marker '{marker}' found in load_memory() category '{cat}': {item}"
                )


def test_load_memory_returns_empty_categories_when_no_supabase():
    mem = load_memory(force_refresh=True)
    for cat in mem:
        if cat in ("updated_at", "version", "source"):
            continue
        assert isinstance(mem[cat], list), f"Category {cat} should be a list"


def test_archived_defaults_separate_from_live():
    archived = load_archived_executive_memory_defaults()
    live = load_memory(force_refresh=True)
    for cat in ["infrastructure_problems", "unfinished_systems"]:
        archived_items = archived.get(cat, [])
        live_items = live.get(cat, [])
        if archived_items:
            assert archived_items != live_items, (
                f"Archived defaults for {cat} should differ from live memory"
            )


def test_archived_defaults_contain_known_stale():
    archived = load_archived_executive_memory_defaults()
    problems = " ".join(archived.get("infrastructure_problems", []))
    assert "Ollama" in problems, "Archived defaults should still contain Ollama OFFLINE"


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
