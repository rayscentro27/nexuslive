"""
test_backfill_hermes_memory_v2_guardrails.py
Verifies apply guards in backfill_hermes_memory_v2.py:
- _SUPABASE_WRITE_ATTEMPTED = False sentinel present
- --require-ray-approval flag required
- exact confirm text checked per batch
- env vars checked
- JSONL existence checked
- manifest checked
"""
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "backfill_hermes_memory_v2.py"
JSONL = ROOT / "docs" / "reports" / "memory" / "hermes_memory_v2_batch1_20260602_021258.jsonl"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run(*extra, timeout=15):
    cmd = [sys.executable, str(SCRIPT)] + list(extra)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


print("=== test_backfill_hermes_memory_v2_guardrails ===\n")

print("-- Script exists --")
check("backfill_hermes_memory_v2.py exists", SCRIPT.exists())
if not SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = SCRIPT.read_text(encoding="utf-8")

print("\n-- Sentinel checks --")
check("_SUPABASE_WRITE_ATTEMPTED = False sentinel present", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("sentinel never set to True", "_SUPABASE_WRITE_ATTEMPTED = True" not in src)

print("\n-- Guard source checks --")
check("--require-ray-approval guard present", "require_ray_approval" in src)
check("confirm text guard present", "confirm_text" in src and "BATCH_CONFIRM_TEXTS" in src)
check("_check_env() guard present", "_check_env" in src)
check("_check_manifest() guard present", "_check_manifest" in src)
check("JSONL existence guard present", "jsonl_path.exists" in src)

print("\n-- Batch confirm texts defined --")
check("batch1 confirm text defined", "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 1" in src)
check("batch2 confirm text defined", "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 2" in src)
check("batch3 confirm text defined", "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 3" in src)

print("\n-- OLD_TABLES defined (no old table writes) --")
check("OLD_TABLES set defined", "OLD_TABLES" in src)
check("ai_memory in OLD_TABLES", '"ai_memory"' in src or "'ai_memory'" in src)
check("hermes_executive_memory in OLD_TABLES", "hermes_executive_memory" in src)
check("knowledge_items in OLD_TABLES", "knowledge_items" in src)

print("\n-- Apply blocked without --require-ray-approval --")
if JSONL.exists():
    code, out = run(
        "--apply",
        "--batch-name", "batch1",
        "--source-jsonl", str(JSONL),
        "--confirm-text", "I APPROVE HERMES MEMORY V2 BACKFILL BATCH 1",
    )
    check("apply without --require-ray-approval exits non-zero", code != 0)
    check("apply output mentions approval flag", "require_ray_approval" in out or "approval" in out.lower() or "BLOCKED" in out)
else:
    check("JSONL exists (skipping runtime guard test)", False)
    check("runtime guard test skipped", True)

print("\n-- Apply blocked with wrong confirm text --")
if JSONL.exists():
    code2, out2 = run(
        "--apply",
        "--batch-name", "batch1",
        "--source-jsonl", str(JSONL),
        "--require-ray-approval",
        "--confirm-text", "WRONG TEXT",
    )
    check("apply with wrong confirm text exits non-zero", code2 != 0)
    check("apply output mentions mismatch or BLOCKED", "mismatch" in out2.lower() or "BLOCKED" in out2 or "Confirm text" in out2)
else:
    check("JSONL exists (skipping confirm-text guard test)", False)
    check("runtime test skipped", True)

print("\n-- Dry-run succeeds without approval flags --")
if JSONL.exists():
    code3, out3 = run(
        "--dry-run",
        "--batch-name", "batch1",
        "--source-jsonl", str(JSONL),
        "--types", "operating_rule,ray_preference,approval_policy,project_context",
        "--limit", "5",
    )
    check("dry-run exits 0 without approval flags", code3 == 0)
    check("dry-run output says No writes", "No writes" in out3)
else:
    check("JSONL exists (skipping dry-run test)", False)
    check("runtime test skipped", True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
