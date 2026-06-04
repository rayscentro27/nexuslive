"""test_nav_relay_no_supabase_writes.py — Nav/Relay routing adds no Supabase write path."""
import sys
from pathlib import Path

source = Path("telegram_bot.py").read_text(encoding="utf-8")
start = source.index("def _cmd_nav_relay_approval_summary")
end = source.index("def _safe_operator_fallback")
slice_text = source[start:end].lower()

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


for marker in ("from supabase", "import supabase", "supabase.table(", ".insert(", ".upsert(", "rest/v1/"):
    check(f"nav/relay slice omits '{marker}'", marker not in slice_text)

print(f"\nNav/Relay no Supabase writes: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
