"""
test_simplification_followup_no_evidence_dump.py
Tests: simplification follow-up phrases return SIMPLIFICATION STATUS,
never fall into evidence dump, and offer correct next-step options.
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
    "I can answer from verified artifacts", "═══", "HERMES REPORT",
]


def check(label: str, cond: bool):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  PASS  {label}")
    else:    FAIL += 1; print(f"  FAIL  {label}")


def no_dump(text: str) -> bool:
    return not any(m in text for m in DUMP_MARKERS)


print("=== test_simplification_followup_no_evidence_dump ===\n")

# ── continuity keys exist for simplification follow-ups ──────────────────────
print("-- continuity dict has simplification follow-up keys --")
import inspect
import telegram_bot as _tbot
src = inspect.getsource(_tbot.NexusTelegramBot.handle_inbound_message)

SIMPLIFICATION_KEYS = [
    "why cant you make it simpler",
    "why can't you make it simpler",
    "why cant you make it simplier",
    "why can't you make it simplier",
    "can you make it simpler",
    "make it even simpler",
    "simplify it again",
    "simplify again",
    "make this easier to understand",
]
for key in SIMPLIFICATION_KEYS:
    # Keys use double-quotes in source — search for key text directly, not repr()
    check(f"continuity key {repr(key[:50])} present", key in src)

# ── _cmd_simplification_status handler exists ─────────────────────────────────
print("\n-- _cmd_simplification_status handler --")
check("_cmd_simplification_status method exists",
      hasattr(_tbot.NexusTelegramBot, "_cmd_simplification_status"))

# ── simplification status output structure ────────────────────────────────────
print("\n-- simplification status output structure --")
# Create a minimal bot instance (read-only, no Telegram connection)
import unittest.mock as _mock
with _mock.patch("telegram_bot.NexusTelegramBot.__init__", lambda self: None):
    bot = _tbot.NexusTelegramBot.__new__(_tbot.NexusTelegramBot)

resp = bot._cmd_simplification_status()
check("non-empty", bool(resp))
check("starts with SIMPLIFICATION STATUS", resp.startswith("SIMPLIFICATION STATUS"))
check("no dump markers", no_dump(resp))
check("no ═══", "═══" not in resp)
check("no HERMES REPORT", not resp.strip().startswith("HERMES REPORT"))
check("contains 'make it simpler' next option", "make it simpler" in resp.lower())
check("contains approval boundary", "approval" in resp.lower())
check("contains 'show it' or 'show'", "show" in resp.lower())
check("no 'old executive memory'", "old executive memory" not in resp.lower())

# ── _cmd_simplification_status is reachable via bot instance ─────────────────
print("\n-- _cmd_simplification_status output is clean --")
# Simplification follow-up phrases route via Telegram continuity dict,
# not via run_command (CLI). Verify the handler itself returns clean output.
check("SIMPLIFICATION STATUS: no dump markers", no_dump(resp))
check("SIMPLIFICATION STATUS: no ═══", "═══" not in resp)
check("SIMPLIFICATION STATUS: approval boundary present", "approval" in resp.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
