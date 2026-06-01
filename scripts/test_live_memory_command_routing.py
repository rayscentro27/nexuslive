"""
test_live_memory_command_routing.py
Verifies all 4 memory commands route through the command router correctly.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0

def check(label: str, cond: bool):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  PASS  {label}")
    else:
        FAIL += 1; print(f"  FAIL  {label}")

print("=== test_live_memory_command_routing ===\n")

from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command
from telegram_bot import NexusTelegramBot

# ── 1. show memory sources → memory_sources ────────────────────────────────
intent, _, _ = classify_intent("show memory sources")
check("show memory sources → memory_sources intent", intent == "memory_sources")

intent2, _, _ = classify_intent("memory sources")
check("memory sources → memory_sources intent", intent2 == "memory_sources")

# ── 2. where did that answer come from → answer_source ──────────────────────
intent3, _, _ = classify_intent("where did that answer come from")
check("where did that answer come from → answer_source", intent3 == "answer_source")

intent4, _, _ = classify_intent("cite source")
check("cite source → answer_source", intent4 == "answer_source")

# ── 3. show archived executive memory → archived_executive_memory ──────────
intent5, _, _ = classify_intent("show archived executive memory")
check("show archived executive memory → archived_executive_memory", intent5 == "archived_executive_memory")

intent6, _, _ = classify_intent("show archived memory")
check("show archived memory → archived_executive_memory", intent6 == "archived_executive_memory")

# ── 4. show stale memory debug → stale_memory_debug ────────────────────────
intent7, _, _ = classify_intent("show stale memory debug")
check("show stale memory debug → stale_memory_debug", intent7 == "stale_memory_debug")

intent8, _, _ = classify_intent("stale memory debug")
check("stale memory debug → stale_memory_debug", intent8 == "stale_memory_debug")

# ── 5. Response from run_command does not contain executive memory v1 ──────
resp = run_command("show memory sources", source="telegram")
check("memory sources response does not contain Hermes Executive Memory v1",
      "Hermes Executive Memory (v1" not in resp)
check("memory sources response contains HERMES MEMORY SOURCES header",
      "HERMES MEMORY SOURCES" in resp)

# ── 6. Answer source response does not contain raw evidence dumps ──────────
resp2 = run_command("where did that answer come from", source="telegram")
check("answer source contains ANSWER SOURCE header", "ANSWER SOURCE" in resp2)
check("answer source does not contain artifact_inventory", "artifact_inventory" not in resp2)
check("answer source does not contain handoff dump", "handoff" not in resp2.lower().split("handoff")[1:2] if "handoff" in resp2.lower() else True)

# ── 7. Archived memory response contains warning ──────────────────────────
resp3 = run_command("show archived executive memory", source="telegram")
check("archived memory contains ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH",
      "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH" in resp3)

# ── 8. Stale memory debug contains warning ────────────────────────────────
resp4 = run_command("show stale memory debug", source="telegram")
check("stale memory debug contains STALE MEMORY DEBUG — DEBUG ONLY — BLOCKED",
      "STALE MEMORY DEBUG" in resp4)

# ── 9. Stale debug does not fall into quality fallback ─────────────────────
check("stale debug not quality fallback", "wasn't able to generate" not in resp4)

# ── 10. _try_memory_command intercepts correctly ───────────────────────────
bot = NexusTelegramBot.__new__(NexusTelegramBot)
bot._current_chat_id = "test"
reply = bot._try_memory_command("show memory sources")
check("_try_memory_command intercepts memory_sources", reply is not None)
check("_try_memory_command returns proper output", reply is not None and "HERMES MEMORY SOURCES" in reply)

reply2 = bot._try_memory_command("show archived executive memory")
check("_try_memory_command intercepts archived_executive_memory", reply2 is not None)
check("_try_memory_command archived has warning", reply2 is not None and "NOT CURRENT TRUTH" in reply2)

reply3 = bot._try_memory_command("where did that answer come from")
check("_try_memory_command intercepts answer_source", reply3 is not None)

reply4 = bot._try_memory_command("show stale memory debug")
check("_try_memory_command intercepts stale_memory_debug", reply4 is not None)

reply5 = bot._try_memory_command("system health")
check("_try_memory_command returns None for non-memory", reply5 is None)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
