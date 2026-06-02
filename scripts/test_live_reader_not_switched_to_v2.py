"""
test_live_reader_not_switched_to_v2.py
Verifies that the live Telegram reader has NOT been switched to hermes_memory_v2_reader.
The current reader must remain hermes_active_memory_reader (or equivalent).
v2 reader is preview-only for this phase.
"""
import sys, inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


print("=== test_live_reader_not_switched_to_v2 ===\n")

print("-- telegram_bot does not import v2 reader at module level --")
import telegram_bot as tb_mod
tb_src = inspect.getsource(tb_mod)

check("telegram_bot does not top-level import hermes_memory_v2_reader",
      "from lib.hermes_memory_v2_reader import" not in tb_src or
      "preview" in tb_src.lower())

print("\n-- hermes_command_router does not route primary reads to v2 --")
from hermes_command_router import router
router_src = inspect.getsource(router)

check("router plain handlers use v2 for preview only",
      "memory_v2_preview" in router_src)
# v2 reader imports must be lazy (inside functions), not top-level module imports
top_level_lines = [l for l in router_src.splitlines()
                   if l.startswith("from lib.hermes_memory_v2_reader")
                   or l.startswith("import lib.hermes_memory_v2_reader")]
check("hermes_memory_v2_reader is NOT a top-level module import in router",
      len(top_level_lines) == 0)

print("\n-- v2 reader flags itself as preview-only --")
import lib.hermes_memory_v2_reader as v2
status = v2.explain_v2_reader_status()
check("explain_v2_reader_status mentions 'preview'",
      "preview" in status.lower())
check("explain_v2_reader_status does NOT claim to be live primary reader",
      "live primary" not in status.lower() or
      ("not" in status.lower() and "primary" in status.lower()))

src_v2 = inspect.getsource(v2)
check("v2 reader source mentions preview-only or not-live",
      "preview" in src_v2.lower() or "not.*primary" in src_v2.lower() or
      "preview_only" in src_v2.lower())

print("\n-- compare_v2_with_current_memory recommendation does not say 'switch now' --")
cmp = v2.compare_v2_with_current_memory()
rec = cmp.get("recommendation", "")
check("recommendation exists", bool(rec))
check("recommendation mentions 'preview'", "preview" in rec.lower())
check("recommendation does NOT instruct to switch to v2 now unconditionally",
      "switch to v2" not in rec.lower() or
      ("after" in rec.lower() and "approval" in rec.lower()))

print("\n-- run_command v2 responses say preview, not live primary --")
from hermes_command_router.router import run_command
for cmd in ["show memory v2 preview", "show memory v2 status"]:
    result = run_command(cmd, source="telegram") or ""
    check(f"'{cmd[:40]}' contains 'preview'",
          "preview" in result.lower())
    check(f"'{cmd[:40]}' does NOT claim v2 is live primary",
          "live primary" not in result.lower() or
          ("not" in result.lower() and "primary" in result.lower()))

print("\n-- Primary memory reader import unchanged --")
try:
    import lib.hermes_active_memory_reader as active_reader
    check("hermes_active_memory_reader still importable", True)
    check("active reader has load_active_memory",
          hasattr(active_reader, "load_active_memory") or
          hasattr(active_reader, "load_active_memory_for_context"))
except ImportError:
    check("hermes_active_memory_reader still importable", False)

print("\n-- Phase 4D report confirms live_reader_switched: False --")
import json
REPORT_DIR = ROOT / "docs" / "reports" / "memory"
comparison_reports = list(REPORT_DIR.glob("phase4d_reader_comparison_*.json"))
check("reader comparison report exists", len(comparison_reports) > 0)
if comparison_reports:
    latest = max(comparison_reports, key=lambda p: p.stat().st_mtime)
    report = json.loads(latest.read_text())
    check("report confirms live_reader_switched: False",
          report.get("live_reader_switched") is False)
    check("report confirms supabase_writes_attempted: False",
          report.get("supabase_writes_attempted") is False)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
