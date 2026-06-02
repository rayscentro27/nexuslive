"""
test_hermes_learning_loop_deprecation.py
Tests: deprecate_lesson — only works for lesson-type records in hermes_memory_v2.
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


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_hermes_learning_loop_deprecation ===\n")

from lib.hermes_learning_loop import deprecate_lesson, _env_available

print("-- deprecate_lesson: non-existent memory_id --")
result = deprecate_lesson("lesson_doesnotexist_in_v2")
if _env_available():
    check("not_found returns ok=False", not result.get("ok"))
    check("not_found has error message", bool(result.get("error")))
else:
    check("no-creds returns ok=False", not result.get("ok"))
    check("no-creds error mentions credentials", "credential" in result.get("error", "").lower())

print("\n-- deprecate_lesson: no-credentials path --")
import lib.hermes_learning_loop as _ll
_orig_url = os.environ.get("SUPABASE_URL", "")
_orig_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
try:
    os.environ["SUPABASE_URL"] = ""
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
    os.environ["SUPABASE_KEY"] = ""
    result_nocreds = deprecate_lesson("lesson_test_abc123")
    check("no-creds: ok=False", not result_nocreds.get("ok"))
    check("no-creds: error message present", bool(result_nocreds.get("error")))
finally:
    if _orig_url:
        os.environ["SUPABASE_URL"] = _orig_url
    if _orig_key:
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = _orig_key

print("\n-- deprecate_lesson: only targets lesson memory_type --")
import inspect
src = inspect.getsource(deprecate_lesson)
check("deprecate_lesson checks memory_type == lesson",
      "LESSON_TYPE" in src or "lesson" in src)
check("deprecate_lesson updates status to deprecated",
      "deprecated" in src)
check("deprecate_lesson uses deprecated_reason column",
      "deprecated_reason" in src)
check("deprecate_lesson does not use internal_notes",
      "internal_notes" not in src)
check("deprecate_lesson does not touch old tables", "ai_memory" not in src)

print("\n-- deprecate_lesson: function signature --")
import inspect as _inspect
sig = _inspect.signature(deprecate_lesson)
params = list(sig.parameters.keys())
check("deprecate_lesson has memory_id param", "memory_id" in params)
check("deprecate_lesson has reason param", "reason" in params)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
