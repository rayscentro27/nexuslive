"""
test_phase7a_existing_commands_still_work.py
Phase 7A: All Phase 6A–6F commands continue to work unchanged after Phase 7A routing fix.
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


print("=== test_phase7a_existing_commands_still_work ===\n")

from hermes_command_router.router import run_command

# ── Phase 6A daily cycle ──────────────────────────────────────────────────────
print("-- Phase 6A daily cycle commands --")
r = run_command("run daily operating cycle") or ""
check("daily cycle: NEXUS PLAN header", "NEXUS PLAN" in r.upper())
check("daily cycle: not CFO", not r.startswith("RAY, I UNDERSTAND"))

# ── Phase 6C approval queue ───────────────────────────────────────────────────
print("\n-- Phase 6C approval queue --")
r = run_command("show approval queue") or ""
check("approval queue: APPROVAL QUEUE header", "APPROVAL QUEUE" in r.upper())
check("approval queue: not CFO", not r.startswith("RAY, I UNDERSTAND"))

# ── Phase 6D revenue asset packet ────────────────────────────────────────────
print("\n-- Phase 6D revenue asset packet --")
r = run_command("show revenue asset packet") or ""
check("revenue packet: REVENUE ASSET PACKET header", "REVENUE ASSET PACKET" in r.upper())
check("revenue packet: not CFO", not r.startswith("RAY, I UNDERSTAND"))

# ── Phase 6F rescore after fixes ─────────────────────────────────────────────
print("\n-- Phase 6F rescore after fixes --")
r = run_command("rescore after fixes") or ""
check("rescore: REVENUE PACKET RESCORED header", "REVENUE PACKET RESCORED" in r.upper())
check("rescore: not CFO", not r.startswith("RAY, I UNDERSTAND"))

# ── Phase 7 research queue / scout assignments ────────────────────────────────
print("\n-- Phase 7 research queue commands --")
r = run_command("show research queue") or ""
check("research queue: RESEARCH QUEUE header", "RESEARCH QUEUE" in r.upper())

r = run_command("show scout assignments") or ""
check("scout assignments: SCOUT ASSIGNMENTS header", "SCOUT ASSIGNMENTS" in r.upper())

r = run_command("what are you still trying to figure out") or ""
check("unresolved questions: UNRESOLVED QUESTIONS header", "UNRESOLVED QUESTIONS" in r.upper())

# ── Memory v2 primary ────────────────────────────────────────────────────────
print("\n-- Memory v2 primary --")
r = run_command("show memory v2 primary status") or ""
check("memory v2: some memory content returned", len(r.strip()) > 10)

# ── Learning loop ─────────────────────────────────────────────────────────────
print("\n-- Learning loop --")
r = run_command("show pending lessons") or ""
check("pending lessons: some content returned", len(r.strip()) > 10)

# ── Phase 7A new command ─────────────────────────────────────────────────────
print("\n-- Phase 7A dedupe research queue --")
r = run_command("dedupe research queue") or ""
check("dedupe: RESEARCH QUEUE DEDUPED header", "RESEARCH QUEUE DEDUPED" in r.upper())

# ── None of the exact commands produce CFO intercept ─────────────────────────
print("\n-- Exact commands not intercepted by CFO layer --")
EXACT_CMDS = [
    ("show revenue asset packet", "REVENUE ASSET PACKET"),
    ("run daily operating cycle", "NEXUS PLAN"),
    ("show approval queue", "APPROVAL QUEUE"),
    ("rescore after fixes", "REVENUE PACKET RESCORED"),
    ("show research queue", "RESEARCH QUEUE"),
]
for cmd, expected_hdr in EXACT_CMDS:
    r = run_command(cmd) or ""
    check(f"{cmd!r} → expected header", expected_hdr.upper() in r.upper())
    check(f"{cmd!r} → not CFO intercept", not r.startswith("RAY, I UNDERSTAND"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
