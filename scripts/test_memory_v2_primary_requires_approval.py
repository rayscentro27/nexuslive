"""
test_memory_v2_primary_requires_approval.py
Verifies that primary mode cannot activate without the approval file and all guards.
"""
import sys, os, json, tempfile, shutil
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


print("=== test_memory_v2_primary_requires_approval ===\n")

import lib.hermes_memory_v2_shadow as shadow

APPROVAL_FILE = shadow.APPROVAL_FILE
REQUIRED_PHRASE = shadow.REQUIRED_APPROVAL_PHRASE

print("-- Approval constants --")
check("REQUIRED_APPROVAL_PHRASE is non-empty", bool(REQUIRED_PHRASE))
check("REQUIRED_APPROVAL_PHRASE is the right phrase",
      REQUIRED_PHRASE == "I APPROVE HERMES MEMORY V2 PRIMARY MODE SWITCH")
check("APPROVAL_FILE path is in docs/reports/memory/",
      "docs/reports/memory" in str(APPROVAL_FILE))
check("APPROVAL_FILE name ends in .json", APPROVAL_FILE.suffix == ".json")
check("PRIMARY_MIN_ROWS == 26", shadow.PRIMARY_MIN_ROWS == 26)
check("PRIMARY_REQUIRED_TYPES has 8 entries", len(shadow.PRIMARY_REQUIRED_TYPES) == 8)

print("\n-- Without approval file: primary is blocked --")
os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
_backup = None
if APPROVAL_FILE.exists():
    _backup = APPROVAL_FILE.read_bytes()
    APPROVAL_FILE.unlink()

try:
    mode = shadow.get_memory_v2_mode()
    check("mode falls back to shadow when approval file missing", mode == "shadow")
    check("is_primary_mode_active() is False without approval file",
          shadow.is_primary_mode_active() is False)
    failures = shadow.get_primary_guard_failures()
    check("get_primary_guard_failures() is non-empty", len(failures) > 0)
    check("failure mentions 'approval file'",
          any("approval file" in f for f in failures))
finally:
    if _backup is not None:
        APPROVAL_FILE.write_bytes(_backup)
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- Wrong approval phrase: primary is blocked --")
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", dir=APPROVAL_FILE.parent,
    delete=False
) as tmp:
    json.dump({
        "approved_by": "test",
        "approval_phrase": "WRONG PHRASE",
        "mode": "primary",
    }, tmp)
    tmp_path = Path(tmp.name)

_backup2 = APPROVAL_FILE.read_bytes() if APPROVAL_FILE.exists() else None
try:
    shutil.copy(tmp_path, APPROVAL_FILE)
    os.environ["HERMES_MEMORY_V2_MODE"] = "primary"
    mode2 = shadow.get_memory_v2_mode()
    check("mode falls back to shadow with wrong phrase", mode2 == "shadow")
    failures2 = shadow.get_primary_guard_failures()
    check("failure mentions 'approval_phrase mismatch'",
          any("approval_phrase" in f or "mismatch" in f for f in failures2))
finally:
    tmp_path.unlink(missing_ok=True)
    if _backup2 is not None:
        APPROVAL_FILE.write_bytes(_backup2)
    elif APPROVAL_FILE.exists():
        APPROVAL_FILE.unlink()
    os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print("\n-- Approval file exists with correct phrase --")
check("approval file exists", APPROVAL_FILE.exists())
if APPROVAL_FILE.exists():
    doc = json.loads(APPROVAL_FILE.read_text())
    check("approval file has approval_phrase", "approval_phrase" in doc)
    check("approval file phrase matches required",
          doc.get("approval_phrase") == REQUIRED_PHRASE)
    check("approval file mode is 'primary'", doc.get("mode") == "primary")
    check("approval file has approved_by", bool(doc.get("approved_by")))
    check("approval file has approved_at", bool(doc.get("approved_at")))
    check("approval file has rollback field", bool(doc.get("rollback")))

print("\n-- is_primary_approved() returns (bool, list) --")
approved, failures3 = shadow.is_primary_approved()
check("is_primary_approved() returns tuple", isinstance(failures3, list))
check("is_primary_approved approved is bool", isinstance(approved, bool))

print("\n-- SUPABASE_WRITE_ATTEMPTED remains False --")
check("_SUPABASE_WRITE_ATTEMPTED is False", shadow._SUPABASE_WRITE_ATTEMPTED is False)

os.environ.pop("HERMES_MEMORY_V2_MODE", None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
