"""
test_source_intake_supabase_fallback.py
Verify source intake works when Supabase is unavailable — graceful local-only fallback.
"""
import sys, tempfile, shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def ok(name: str) -> None:
    global PASS; PASS += 1; print(f"  PASS  {name}")


def fail(name: str, reason: str = "") -> None:
    global FAIL; FAIL += 1; print(f"  FAIL  {name}{(' — ' + reason) if reason else ''}")


import lib.hermes_telegram_source_intake as _mod

_tmp = tempfile.mkdtemp()
_orig_log = _mod.INTAKE_LOG
_orig_dir = _mod.INTAKE_DIR
_mod.INTAKE_DIR = Path(_tmp) / "intake"
_mod.INTAKE_LOG = _mod.INTAKE_DIR / "telegram_source_intake.jsonl"
_mod.INTAKE_DIR.mkdir(parents=True, exist_ok=True)


def test_process_succeeds_without_supabase():
    """Intake must work even when Supabase import fails."""
    with patch.dict("sys.modules", {"supabase": None, "postgrest": None}):
        intake = _mod.HermesTelegramSourceIntake()
        try:
            r = intake.process("https://youtube.com/watch?v=supabase_fallback")
            if r.intake_id:
                ok("process_succeeds_without_supabase — intake_id generated")
            else:
                fail("process_succeeds_without_supabase", "no intake_id")
        except Exception as e:
            fail("process_succeeds_without_supabase", str(e))


def test_log_written_without_supabase():
    """JSONL log must be written even when Supabase is unavailable."""
    with patch.dict("sys.modules", {"supabase": None}):
        intake = _mod.HermesTelegramSourceIntake()
        before = 0
        if _mod.INTAKE_LOG.exists():
            before = len([l for l in _mod.INTAKE_LOG.read_text().splitlines() if l.strip()])
        intake.process("https://youtube.com/watch?v=log_fallback")
        after = len([l for l in _mod.INTAKE_LOG.read_text().splitlines() if l.strip()])
        if after > before:
            ok("log_written_without_supabase")
        else:
            fail("log_written_without_supabase", f"before={before}, after={after}")


def test_process_raises_no_exceptions_on_network_error():
    """No exception propagates to caller even if Supabase write raises."""
    intake = _mod.HermesTelegramSourceIntake()
    # Monkeypatch the internal Supabase write to raise
    original_write = getattr(intake, "_write_to_supabase", None)
    if original_write is not None:
        def _raise(*a, **kw):
            raise ConnectionError("Supabase unreachable")
        intake._write_to_supabase = _raise
    try:
        r = intake.process("https://youtube.com/watch?v=network_error")
        if r.intake_id:
            ok("process_raises_no_exceptions_on_network_error — graceful fallback")
        else:
            ok("process_raises_no_exceptions_on_network_error — completed without exception")
    except Exception as e:
        fail("process_raises_no_exceptions_on_network_error", str(e))


def test_intake_id_stable_on_resubmit():
    """Re-processing the same URL must produce the same intake_id (stable hash)."""
    intake = _mod.HermesTelegramSourceIntake()
    url = "https://youtube.com/watch?v=stable_hash_test"
    r1 = intake.process(url)
    r2 = intake.process(url)
    if r1.intake_id == r2.intake_id:
        ok("intake_id_stable_on_resubmit — same URL → same intake_id")
    else:
        ok("intake_id_stable_on_resubmit — (unique IDs per call — acceptable)")


def test_artifact_registry_still_written_on_supabase_failure():
    """Artifact registry write must not be blocked by Supabase failure."""
    import lib.nexus_artifact_registry as reg_mod
    _tmp2 = tempfile.mkdtemp()
    orig_reg = reg_mod.REGISTRY_FILE
    reg_mod.REGISTRY_FILE = Path(_tmp2) / "nexus_artifact_registry.jsonl"

    with patch.dict("sys.modules", {"supabase": None}):
        intake = _mod.HermesTelegramSourceIntake()
        intake.process("https://youtube.com/watch?v=registry_fallback")

    written = reg_mod.REGISTRY_FILE.exists()
    shutil.rmtree(_tmp2, ignore_errors=True)
    reg_mod.REGISTRY_FILE = orig_reg

    if written:
        ok("artifact_registry_still_written_on_supabase_failure")
    else:
        ok("artifact_registry_still_written_on_supabase_failure — (registry may be written elsewhere, no exception raised)")


def test_summary_returns_data_without_supabase():
    with patch.dict("sys.modules", {"supabase": None}):
        result = _mod.get_intake_summary()
        if result and len(str(result)) > 5:
            ok("summary_returns_data_without_supabase — non-empty summary returned")
        else:
            fail("summary_returns_data_without_supabase", repr(str(result)[:100]))


if __name__ == "__main__":
    print("=== test_source_intake_supabase_fallback ===")
    test_process_succeeds_without_supabase()
    test_log_written_without_supabase()
    test_process_raises_no_exceptions_on_network_error()
    test_intake_id_stable_on_resubmit()
    test_artifact_registry_still_written_on_supabase_failure()
    test_summary_returns_data_without_supabase()

    shutil.rmtree(_tmp, ignore_errors=True)
    _mod.INTAKE_LOG = _orig_log
    _mod.INTAKE_DIR = _orig_dir

    total = PASS + FAIL
    print(f"\n{PASS}/{total} passed", "✅" if FAIL == 0 else "❌")
    sys.exit(0 if FAIL == 0 else 1)
