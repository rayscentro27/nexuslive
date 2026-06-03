"""
test_phase7a_contextual_followup.py
Phase 7A: "what should we do about that?" threads back to prior CFO context.
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


print("=== test_phase7a_contextual_followup ===\n")

from hermes_command_router.router import run_command
from lib.hermes_cfo_conversation_layer import (
    load_cfo_context_state, save_cfo_context_state, update_cfo_context_state,
    _CFO_CONTEXT_STATE_DEFAULT,
)

# ── Context state functions work ─────────────────────────────────────────────
print("-- CFO context state functions --")

state = update_cfo_context_state(
    topic="hermes_behavior_feedback",
    concern_summary="Hermes is acting like a command bot, not a CFO",
    recommendation="Add CFO conversation layer",
)
check("update_cfo_context_state returns dict", isinstance(state, dict))
check("state has last_cfo_topic", state.get("last_cfo_topic") == "hermes_behavior_feedback")
check("state has last_concern_summary", "command bot" in (state.get("last_concern_summary") or ""))
check("state has created_at", state.get("created_at") is not None)

# ── Load state after save ─────────────────────────────────────────────────────
print("\n-- load state after save --")
loaded = load_cfo_context_state()
check("loaded state has topic", loaded.get("last_cfo_topic") == "hermes_behavior_feedback")
check("loaded state has concern", "command bot" in (loaded.get("last_concern_summary") or ""))

# ── Contextual follow-up uses prior context ───────────────────────────────────
print("\n-- contextual follow-up threads prior concern --")

# First, send concern to set context state
r1 = run_command("I am worried Hermes is becoming a command bot and not a CFO.") or ""
check("concern produces CFO response", r1.startswith("RAY, I UNDERSTAND"))

# Then send follow-up
r2 = run_command("what should we do about that?") or ""
check("follow-up produces CFO response (not quality fallback)",
      r2.startswith("RAY, I UNDERSTAND") or r2.startswith("I DON'T HAVE VERIFIED")
      or r2.startswith("IMPLEMENTATION PROMPT"))
check("follow-up is non-empty", len(r2.strip()) > 30)
check("follow-up does not start with HERMES generic report", "════" not in r2[:80])

# ── Follow-up with fresh context state ───────────────────────────────────────
print("\n-- follow-up with loaded context threads back --")
loaded_after = load_cfo_context_state()
check("context state updated after concern message",
      loaded_after.get("last_cfo_topic") is not None)

# ── Stale state default ───────────────────────────────────────────────────────
print("\n-- stale context state returns default --")
stale_state = dict(_CFO_CONTEXT_STATE_DEFAULT)
stale_state["created_at"] = "2020-01-01T00:00:00+00:00"  # Very old
stale_state["last_cfo_topic"] = "should_be_cleared"
stale_state["stale_after_hours"] = 24
save_cfo_context_state(stale_state)

reloaded = load_cfo_context_state()
check("stale context returns empty topic", reloaded.get("last_cfo_topic") is None)

# ── Restore fresh state ───────────────────────────────────────────────────────
update_cfo_context_state(topic="hermes_behavior_feedback", concern_summary="test restored")
final = load_cfo_context_state()
check("fresh context loads correctly", final.get("last_cfo_topic") == "hermes_behavior_feedback")

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
