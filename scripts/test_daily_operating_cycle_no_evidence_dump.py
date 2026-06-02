"""
test_daily_operating_cycle_no_evidence_dump.py
Tests: all daily operating cycle commands produce clean output — no evidence dump.
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
    "artifact_inventory",
    "handoff dump",
    "Executive Memory",
    "I can answer from verified artifacts",
    "Strategic context from evidence",
    "Quality escalation fallback",
    "═══",
    "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_daily_operating_cycle_no_evidence_dump ===\n")

from hermes_command_router.router import run_command

# ── All daily operating cycle commands must produce no evidence dump ───────
print("-- all daily cycle commands: no evidence dump --")
DAILY_COMMANDS = [
    "run daily operating cycle",
    "hermes run daily operating cycle",
    "what should i work on today",
    "what should we work on today",
    "show today's nexus plan",
    "show today's plan",
    "daily plan",
    "today's nexus plan",
    "show approval queue",
    "show items needing approval",
    "approval queue",
    "what needs ray approval",
    "continue while i am out",
    "keep working while i am out",
    "what can you do while i am gone",
    "continue work",
    "show today's top revenue move",
    "show today's top money move",
    "top revenue move",
    "top money move today",
    "show today's blockers",
    "show blockers",
    "what is blocked",
    "what is stopping us",
]

for cmd in DAILY_COMMANDS:
    resp = run_command(cmd, source="cli")
    check(f"'{cmd[:45]}': non-empty",    bool(resp))
    check(f"'{cmd[:45]}': no dump",      no_dump(resp))
    check(f"'{cmd[:45]}': no ═══",       "═══" not in resp)
    check(f"'{cmd[:45]}': no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── Old Executive Memory never appears ─────────────────────────────────────
print("\n-- old Executive Memory never appears --")
EXEC_MEM_MARKERS = [
    "old executive memory",
    "executive memory snapshot",
    "stale memory",
    ".hermes_executive_memory",
]
for cmd in ["run daily operating cycle", "show blockers", "show approval queue"]:
    resp = run_command(cmd, source="cli")
    check(f"'{cmd}': no old exec memory",
          not any(m in resp.lower() for m in EXEC_MEM_MARKERS))

# ── Responses are plain language, not raw reports ──────────────────────────
print("\n-- responses are plain language --")
resp_plan = run_command("run daily operating cycle", source="cli")
resp_cwo  = run_command("continue while i am out", source="cli")
resp_blk  = run_command("show blockers", source="cli")

check("daily plan: starts with TODAY'S NEXUS PLAN",        resp_plan.startswith("TODAY'S NEXUS PLAN"))
check("continue while out: starts with CONTINUE WHILE",    resp_cwo.startswith("CONTINUE WHILE YOU ARE OUT"))
check("blockers: starts with TODAY'S BLOCKERS",            resp_blk.startswith("TODAY'S BLOCKERS"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
