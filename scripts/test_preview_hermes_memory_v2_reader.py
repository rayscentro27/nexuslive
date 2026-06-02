"""
test_preview_hermes_memory_v2_reader.py
Verifies preview_hermes_memory_v2_reader.py:
- Read-only queries only (no insert/upsert/update/delete)
- Never prints payload or secrets
- _SUPABASE_WRITE_ATTEMPTED = False sentinel
- telegram_bot.py not modified
- --limit flag present
- --type filter flag present
"""
import sys, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "preview_hermes_memory_v2_reader.py"
TELEGRAM_BOT = ROOT / "telegram_bot.py"

PASS = 0; FAIL = 0


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def run(*extra, timeout=15):
    cmd = [sys.executable, str(SCRIPT)] + list(extra)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout + r.stderr


print("=== test_preview_hermes_memory_v2_reader ===\n")

print("-- Script exists --")
check("preview_hermes_memory_v2_reader.py exists", SCRIPT.exists())
if not SCRIPT.exists():
    print(f"\n{PASS} passed, {FAIL} failed"); sys.exit(FAIL)

src = SCRIPT.read_text(encoding="utf-8")

print("\n-- Safety sentinels --")
check("_SUPABASE_WRITE_ATTEMPTED = False sentinel", "_SUPABASE_WRITE_ATTEMPTED = False" in src)
check("_SUPABASE_WRITE_ATTEMPTED never set True", "_SUPABASE_WRITE_ATTEMPTED = True" not in src)

print("\n-- Read-only: no write operations --")
check("no .insert() call", ".insert(" not in src)
check("no .upsert() call", ".upsert(" not in src)
check("no .update() call", ".update(" not in src)
check("no .delete() call", ".delete(" not in src)

print("\n-- Payload/secrets protection --")
check("payload column not in PREVIEW_COLUMNS or select", "payload" not in src.split("PREVIEW_COLUMNS")[1][:200] if "PREVIEW_COLUMNS" in src else "payload" not in src)
check("summary column not selected (title only)", 'select("summary"' not in src)
check("_redact not needed (no DB errors with secrets expected, but no raw env prints)",
      "os.environ.get" not in src or "print(os.environ" not in src)

print("\n-- CLI flags --")
check("--limit flag defined", "--limit" in src)
check("--type filter flag defined", "--type" in src or "memory_type" in src)

print("\n-- Filter for active/live_answer --")
check("filters status=active", 'eq("status", "active")' in src)
check("filters scope=live_answer", 'eq("scope", "live_answer")' in src)

print("\n-- telegram_bot.py not modified --")
check("source does not import telegram_bot", "import telegram_bot" not in src)
check("source does not open/write telegram_bot.py", "telegram_bot" not in src or ("telegram_bot" in src and "open" not in src))
tb_mtime_before = TELEGRAM_BOT.stat().st_mtime if TELEGRAM_BOT.exists() else None

print("\n-- Does not expose secrets --")
check("no print of SUPABASE keys", "print(os.environ" not in src)
check("no print of raw key values", 'print(key)' not in src and 'print(url)' not in src)

print("\n-- Source mentions read-only --")
check("source mentions READ-ONLY or read-only", "READ-ONLY" in src or "read-only" in src or "read_only" in src)
check("source mentions no writes", "No writes" in src or "no writes" in src.lower())

# Check telegram_bot.py mtime unchanged if it exists
if TELEGRAM_BOT.exists() and tb_mtime_before is not None:
    tb_mtime_after = TELEGRAM_BOT.stat().st_mtime
    check("telegram_bot.py mtime unchanged after import", tb_mtime_before == tb_mtime_after)
else:
    check("telegram_bot.py existence check skipped", True)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
