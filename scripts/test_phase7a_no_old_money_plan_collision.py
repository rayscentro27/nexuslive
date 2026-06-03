"""
test_phase7a_no_old_money_plan_collision.py
Phase 7A: Affiliate offer and CFO-category messages do not produce "TODAY'S MONEY PLAN".
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


print("=== test_phase7a_no_old_money_plan_collision ===\n")

from hermes_command_router.router import run_command

# ── CFO messages must not produce TODAY'S MONEY PLAN ──────────────────────────
print("-- CFO messages do not produce TODAY'S MONEY PLAN --")

CFO_MESSAGES = [
    "Can Hermes find the best affiliate offer for the funding checklist?",
    "I don't know the answer, can your scouts figure it out?",
    "I am worried Hermes is becoming a command bot and not a CFO.",
    "What should we do about that?",
]

for msg in CFO_MESSAGES:
    r = (run_command(msg) or "").lower()
    check(f"not money plan: {msg[:50]!r}", "today's money plan" not in r)
    check(f"not generic fallback: {msg[:50]!r}", "i wasn't sure what you meant" not in r)

# ── CFO messages produce correct CFO headers ──────────────────────────────────
print("\n-- CFO messages produce correct headers --")

concern_r = run_command("Can Hermes find the best affiliate offer for the funding checklist?") or ""
check("affiliate offer → CFO dispatch (not money plan)",
      concern_r.startswith("I DON'T HAVE VERIFIED") or concern_r.startswith("RAY, I UNDERSTAND"))

unknown_r = run_command("I don't know the answer, can your scouts figure it out?") or ""
check("unknown → I DON'T HAVE VERIFIED", unknown_r.startswith("I DON'T HAVE VERIFIED"))

# ── Legitimate revenue/money commands still work ──────────────────────────────
print("\n-- Legitimate revenue commands still produce correct output --")

# "show revenue asset packet" should NOT produce CFO response
r_packet = run_command("show revenue asset packet") or ""
check("show revenue asset packet → REVENUE ASSET PACKET", "REVENUE ASSET PACKET" in r_packet.upper())
check("show revenue asset packet → not CFO", not r_packet.startswith("RAY, I UNDERSTAND"))

# "run daily operating cycle" should NOT produce CFO response
r_daily = run_command("run daily operating cycle") or ""
check("daily cycle → TODAY'S NEXUS PLAN", "NEXUS PLAN" in r_daily.upper())
check("daily cycle → not CFO", not r_daily.startswith("RAY, I UNDERSTAND"))

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
