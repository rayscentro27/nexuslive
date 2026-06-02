"""
test_approval_queue_show_queue_command.py
Tests: show_approval_queue intent routing and APPROVAL QUEUE response format.
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
    "artifact_inventory", "handoff dump", "Executive Memory",
    "I can answer from verified artifacts", "Strategic context from evidence",
    "Quality escalation", "═══", "HERMES REPORT",
    "old executive memory", "executive memory snapshot",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_approval_queue_show_queue_command ===\n")

from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

SHOW_QUEUE_PHRASES = [
    "show approval queue",
    "what needs my approval",
    "show pending approvals",
    "approval needed",
    "what approvals are pending",
    "show items needing approval",
    "pending approvals",
    "approval queue",
    "what needs approval",
]

# ── routing ───────────────────────────────────────────────────────────────────
print("-- classify_intent routes all phrases to show_approval_queue --")
for phrase in SHOW_QUEUE_PHRASES:
    intent, _, _ = classify_intent(phrase)
    check(f"[{phrase[:50]}] → show_approval_queue", intent == "show_approval_queue")

# ── response format ───────────────────────────────────────────────────────────
print("\n-- APPROVAL QUEUE response format --")
for phrase in SHOW_QUEUE_PHRASES:
    resp = run_command(phrase, source="cli")
    check(f"[{phrase[:45]}] starts with APPROVAL QUEUE",
          resp.startswith("APPROVAL QUEUE"))
    check(f"[{phrase[:45]}] no dump markers", no_dump(resp))
    check(f"[{phrase[:45]}] no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))

# ── content when empty ────────────────────────────────────────────────────────
print("\n-- empty queue content --")
resp = run_command("show approval queue", source="cli")
check("mentions safe internal work", "Safe internal work" in resp)
check("mentions approval boundary", "Approval boundary" in resp or "approval boundary" in resp.lower())
check("no ═══", "═══" not in resp)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
