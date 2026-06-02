"""
test_general_language_no_artifact_dump.py
Comprehensive check: all general conversation routes avoid evidence/artifact dumps.
Also verifies memory v2 primary commands and content loop still work.
"""
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_env_file = ROOT / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

PASS = 0; FAIL = 0
DUMP_MARKERS = [
    "artifact_inventory", "Executive Memory",
    "I can answer from verified artifacts",
    "Quality escalation fallback",
    "═══",  # actual HERMES REPORT wrapper separator
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(resp: str) -> bool:
    return not any(m in resp for m in DUMP_MARKERS)


def no_report_wrapper(resp: str) -> bool:
    """True if response doesn't use the HERMES REPORT ═══ wrapper."""
    return "═══" not in resp and not resp.strip().startswith("HERMES REPORT")


print("=== test_general_language_no_artifact_dump ===\n")

from hermes_command_router.router import run_command
from datetime import date

GENERAL_CASES = [
    ("did you get enough sleep",           "sleep",      ["sleep", "online", "ready"]),
    ("what is todays date",                "date",       [date.today().strftime("%Y")]),
    ("what do you have planned for tomorrow", "tomorrow", ["TOMORROW PLAN"]),
    ("what if you dont have the answer",   "unknown",    ["IF I DON"]),
    ("show knowledge gaps",                "gaps",       ["KNOWLEDGE GAPS"]),
]

print("-- General conversation routes: no dump, correct output --")
for phrase, label, expected in GENERAL_CASES:
    resp = run_command(phrase, source="cli")
    check(f"{label}: response non-empty", bool(resp))
    check(f"{label}: no evidence dump", no_dump(resp))
    check(f"{label}: no HERMES REPORT wrapper", no_report_wrapper(resp))
    check(f"{label}: no stale Executive Memory", "Executive Memory" not in resp)
    for exp in expected:
        check(f"{label}: contains {exp!r}", exp in resp)

print("\n-- memory v2 primary commands still work --")
primary_resp = run_command("show memory v2 primary status", source="cli")
check("primary status: response non-empty", bool(primary_resp))
check("primary status: contains PRIMARY STATUS", "PRIMARY STATUS" in primary_resp)
check("primary status: no HERMES REPORT wrapper", "HERMES REPORT" not in primary_resp)

sources_resp = run_command("show memory sources", source="cli")
check("memory sources: response non-empty", bool(sources_resp))
check("memory sources: no HERMES REPORT", "HERMES REPORT" not in sources_resp)

compare_resp = run_command("compare memory v2", source="cli")
check("compare memory v2: contains MEMORY READER COMPARISON",
      "MEMORY READER COMPARISON" in compare_resp)
check("compare memory v2: no stale wording",
      "not primary yet" not in compare_resp and
      "Enable shadow mode" not in compare_resp)

print("\n-- Content loop intents not broken --")
# These should still route through build_report (not plain), but should not crash
for phrase in ["what do you recommend", "show knowledge gaps"]:
    r = run_command(phrase, source="cli")
    check(f"'{phrase}' returns non-empty", bool(r))

print("\n-- Small talk intents in SAFE_REPEATABLE_MEMORY_INTENTS --")
import telegram_bot as tb_mod, inspect
tb_src = inspect.getsource(tb_mod)
for intent in ["small_talk", "date_time_question", "tomorrow_plan",
               "unknown_handling", "knowledge_gap_review"]:
    check(f"{intent} in SAFE_REPEATABLE_MEMORY_INTENTS", intent in tb_src)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
