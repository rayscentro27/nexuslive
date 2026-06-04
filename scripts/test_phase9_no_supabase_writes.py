"""test_phase9_no_supabase_writes.py — Phase 9 routing cleanup adds no Supabase write path."""
import sys
from pathlib import Path

source = Path("telegram_bot.py").read_text(encoding="utf-8").lower()
start = source.index("def _cmd_funding_readiness_approval_summary")
end = source.index("def _enqueue_research")
phase9_slice = source[start:end]

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


for marker in (
    "from supabase",
    "import supabase",
    "supabase.table(",
    ".insert(",
    ".upsert(",
    "rest/v1/",
):
    check(f"phase9 routing slice omits '{marker}'", marker not in phase9_slice)

print(f"\nPhase 9 no Supabase writes: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
