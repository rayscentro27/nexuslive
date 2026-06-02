"""
test_hermes_memory_reader_active_only.py
Verifies lib/hermes_active_memory_reader.py:
- never returns stale/blocked/OFFLINE values in live memory
- _empty_memory() produces a safe neutral dict
- stale markers are defined and applied
- no Supabase write calls in the module
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_memory_reader_active_only ===\n")

print("-- Module source safety --")
reader_path = ROOT / "lib" / "hermes_active_memory_reader.py"
check("hermes_active_memory_reader.py exists", reader_path.exists())

if not reader_path.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = reader_path.read_text(encoding="utf-8")

check("_STALE_MARKERS defined", "_STALE_MARKERS" in src)
check("_empty_memory() defined", "_empty_memory" in src)
check("load_active_memory() defined", "load_active_memory" in src)
check("no INSERT INTO calls", "INSERT INTO" not in src.upper())
check("no .post( write calls", ".post(" not in src)
check("no .upsert( write calls", ".upsert(" not in src)
check("no .patch( write calls", ".patch(" not in src)

print("\n-- Stale markers defined --")
for marker in ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter", "NitroTrades"]:
    check(f"stale marker '{marker}' in _STALE_MARKERS", f'"{marker}"' in src or f"'{marker}'" in src)

print("\n-- _empty_memory() returns safe neutral dict --")
try:
    from lib.hermes_active_memory_reader import _empty_memory, _has_stale_content, _STALE_MARKERS
    empty = _empty_memory()
    check("_empty_memory() returns dict", isinstance(empty, dict))
    check("_empty_memory() has 'source' field", "source" in empty)
    check("_empty_memory() source is not a stale default",
          empty.get("source", "") not in ["", None] and
          "OFFLINE" not in str(empty.get("source", "")) and
          "pending" not in str(empty.get("source", "")).lower())

    print("\n-- _has_stale_content() detection --")
    for marker in _STALE_MARKERS:
        check(f"stale '{marker}' detected", _has_stale_content(marker))
    check("clean text not flagged as stale", not _has_stale_content("Revenue: $1,000"))
    check("empty string not flagged as stale", not _has_stale_content(""))

    print("\n-- _STALE_MARKERS is a list/frozenset with entries --")
    check("_STALE_MARKERS is non-empty", len(_STALE_MARKERS) >= 5)

except ImportError as e:
    check(f"module importable: {e}", False)
    check("_empty_memory importable", False)
    check("_has_stale_content importable", False)
    check("_STALE_MARKERS importable", False)

print("\n-- load_active_memory() has safe fallback --")
try:
    from lib.hermes_active_memory_reader import load_active_memory
    # Should return a dict even without Supabase connection (uses _empty_memory fallback)
    mem = load_active_memory()
    check("load_active_memory() returns dict", isinstance(mem, dict))
    check("load_active_memory() returns non-empty dict", len(mem) > 0)
    check("load_active_memory() has 'source' field", "source" in mem)
    # The source should NOT be a stale hardcoded default
    mem_source = str(mem.get("source", ""))
    check("memory source is not empty string", mem_source != "")
    check("memory source is not 'OFFLINE' stale value",
          "OFFLINE" not in mem_source and "offline" not in mem_source.lower())
    check("memory source is not 'NitroTrades'", "NitroTrades" not in str(mem))
    check("memory source is not 'Beehiiv pending'", "Beehiiv pending" not in str(mem))
except Exception as e:
    check(f"load_active_memory() callable: {e}", False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
