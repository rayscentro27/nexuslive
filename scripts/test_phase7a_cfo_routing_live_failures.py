"""
test_phase7a_cfo_routing_live_failures.py
Phase 7A: Verify the 5 Telegram live failures now produce correct outputs via run_command.
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


print("=== test_phase7a_cfo_routing_live_failures ===\n")

from hermes_command_router.router import run_command

# ── Failure 1: Strategic concern ─────────────────────────────────────────────
print("-- Failure 1: strategic concern produces CFO response --")
msg1 = "I am worried Hermes is becoming a command bot and not a CFO."
r1 = run_command(msg1) or ""
check("starts with RAY, I UNDERSTAND", r1.startswith("RAY, I UNDERSTAND"))
check("mentions real issue or concern", "real issue" in r1.lower() or "concern" in r1.lower())
check("does not start with HERMES REPORT header",
      "════" not in r1[:100] and "HERMES REPORT" not in r1[:100])
check("mentions command bot or cfo",
      "command" in r1.lower() or "cfo" in r1.lower() or "dispatcher" in r1.lower())
check("has Options or recommendation", "option" in r1.lower() or "recommendation" in r1.lower())

# ── Failure 2: Contextual follow-up ──────────────────────────────────────────
print("\n-- Failure 2: contextual follow-up threads prior concern --")
msg2 = "What should we do about that?"
r2 = run_command(msg2) or ""
check("follow-up produces CFO response (not quality fallback)",
      r2.startswith("RAY, I UNDERSTAND") or r2.startswith("I DON'T HAVE") or
      r2.startswith("IMPLEMENTATION PROMPT") or r2.startswith("STRATEGIC"))
check("follow-up does not produce HERMES generic report",
      "════" not in r2[:80])
check("follow-up is non-empty", len(r2.strip()) > 30)

# ── Failure 3: Unknown / scout dispatch ──────────────────────────────────────
print("\n-- Failure 3: unknown answer triggers scout dispatch --")
msg3 = "I don't know the answer, can your scouts figure it out?"
r3 = run_command(msg3) or ""
check("produces I DON'T HAVE VERIFIED EVIDENCE", r3.startswith("I DON'T HAVE VERIFIED"))
check("mentions scout or research", "scout" in r3.lower() or "research" in r3.lower())
check("mentions research id or assignment", "research_id" in r3.lower() or "rq_" in r3.lower()
      or "research id" in r3.lower() or "assigned" in r3.lower())
check("does not start with HERMES report header", "════" not in r3[:80])

# ── Failure 4: Scout delegation for specific task ────────────────────────────
print("\n-- Failure 4: affiliate offer → scout dispatch --")
msg4 = "Can Hermes find the best affiliate offer for the funding checklist?"
r4 = run_command(msg4) or ""
check("produces I DON'T HAVE VERIFIED or CFO response",
      r4.startswith("I DON'T HAVE VERIFIED") or r4.startswith("RAY, I UNDERSTAND"))
check("mentions scout or research", "scout" in r4.lower() or "research" in r4.lower())
check("does not produce TODAY'S MONEY PLAN (old wrong output)", "today's money plan" not in r4.lower())

# ── Failure 5: Implementation prompt ─────────────────────────────────────────
print("\n-- Failure 5: create prompt for Claude → IMPLEMENTATION PROMPT --")
msg5 = "create a prompt for Claude to fix this"
r5 = run_command(msg5) or ""
check("starts with IMPLEMENTATION PROMPT", r5.startswith("IMPLEMENTATION PROMPT"))
check("mentions Goal", "Goal:" in r5 or "goal:" in r5.lower())
check("mentions Safety", "Safety:" in r5 or "safety" in r5.lower())
check("does not start with HERMES blocked report", "════" not in r5[:80])

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
