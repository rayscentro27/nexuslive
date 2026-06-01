"""
simulate_telegram_memory_safety.py
End-to-end simulation of the Telegram message pipeline to verify no stale
executive memory defaults leak into user-facing responses.

Run:  python3 scripts/simulate_telegram_memory_safety.py
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
        PASS += 1
        print(f"  PASS  {label}")
    else:
        FAIL += 1
        print(f"  FAIL  {label}")

print("=" * 60)
print("Telegram Memory Safety Simulation")
print("=" * 60)

# ── 1. Active memory reader (simulates Telegram context builder) ──────────
print("\n[1] Active Memory Reader (Telegram context)")
from lib.hermes_active_memory_reader import (
    load_active_memory,
    build_telegram_context,
    build_context_block,
    status_summary,
)

mem = load_active_memory(force_refresh=True)
ctx = build_telegram_context(max_chars=400)
block = build_context_block(max_items_per_category=3)

check("Active memory has no Ollama offline",
      "Ollama" not in ctx and "Ollama" not in str(mem.get("infrastructure_problems", [])))
check("Active memory has no Beehiiv pending",
      "Beehiiv" not in ctx and "Beehiiv" not in str(mem.get("unfinished_systems", [])))
check("Active memory has no OpenRouter not configured",
      "OpenRouter" not in ctx and "OpenRouter" not in str(mem.get("unfinished_systems", [])))
check("Context block has no stale data",
      "Ollama" not in block and "Beehiiv" not in block)
summary_text = status_summary()
check("Status summary has content",
      "Hermes" in summary_text or "Active" in summary_text or "Memory" in summary_text or
      "empty" in summary_text.lower() or "unavailable" in summary_text.lower())
check("Context is safe when empty",
      "Ollama" not in ctx and "Beehiiv" not in ctx)

# ── 2. Memory sources command (new format) ────────────────────────────────
print("\n[2] Memory Sources Command")
from hermes_command_router.router import _run_memory_sources, run_command as router_run

status, evidence, _ = _run_memory_sources()
full = "\n".join(evidence)
check("Memory sources returns healthy", status == "healthy")
check("Memory sources has HERMES MEMORY SOURCES header", "HERMES MEMORY SOURCES" in full)
check("Memory sources lists active sources", "Current content artifacts" in full)
check("Memory sources lists blocked sources", "archived executive memory" in full)
check("Memory sources has no Hermes Executive Memory v1", "Hermes Executive Memory (v1" not in full)
check("Memory sources has no stale defaults", "Ollama" not in full)

# ── 3. Answer source command ──────────────────────────────────────────────
print("\n[3] Answer Source Command")
from hermes_command_router.router import _run_answer_source

status2, evidence2, _ = _run_answer_source()
full2 = "\n".join(evidence2)
check("Answer source returns healthy", status2 == "healthy")
check("Answer source has ANSWER SOURCE header", "ANSWER SOURCE" in full2)
check("Answer source no artifact_inventory dump", "artifact_inventory" not in full2)
check("Answer source no handoff dump", "handoff" not in full2[:800])
check("Answer source says no archived memory used", "did not use archived executive memory" in full2)

# ── 4. Archived memory command ────────────────────────────────────────────
print("\n[4] Archived Memory Command")
from hermes_command_router.intake import classify_intent
from hermes_command_router.router import _run_archived_executive_memory

for phrase in ["show archived memory", "load archived defaults", "what were the old defaults"]:
    intent, _, _ = classify_intent(phrase)
    check(f"Intent for '{phrase}' is archived_executive_memory",
          intent == "archived_executive_memory")

status, evidence, rec = _run_archived_executive_memory()
first = evidence[0] if evidence else ""
check("Archived memory starts with warning", first == "ARCHIVED EXECUTIVE MEMORY — NOT CURRENT TRUTH")
check("Archived evidence references stale defaults",
      any("Ollama" in e for e in evidence))

# Non-archived phrase should NOT match
intent, _, _ = classify_intent("system health")
check("Non-archived phrase does not trigger intent",
      intent != "archived_executive_memory")

# ── 5. Stale memory debug command ─────────────────────────────────────────
print("\n[5] Stale Memory Debug Command")
from hermes_command_router.router import _run_stale_memory_debug

status4, evidence4, _ = _run_stale_memory_debug()
first4 = evidence4[0] if evidence4 else ""
check("Stale debug starts with STALE MEMORY DEBUG — BLOCKED",
      "STALE MEMORY DEBUG" in first4 and "BLOCKED" in first4)
check("Stale debug mentions explicit request", "explicitly requested" in " ".join(evidence4))
check("Stale debug shows blocked Ollama", "Ollama" in " ".join(evidence4) or "(BLOCKED)" in " ".join(evidence4))

# ── 6. Quality escalation fallback ────────────────────────────────────────
print("\n[6] Quality Escalation Fallback")
from lib.hermes_response_quality import _fallback_data_block, quality_check

fake_stale = "Ollama OFFLINE\nBeehiiv pending\nYouTube Studio offline"
result = _fallback_data_block("something random", fake_stale)
check("Fallback does not contain Ollama", "Ollama" not in result)
check("Fallback does not contain Beehiiv", "Beehiiv" not in result)
check("Fallback returns actionable guidance",
      "specific" in result.lower() or "nexus ceo briefing" in result.lower())

qc = quality_check("This is a great question about system status. Let me check.", chat_id="sim_test")
check("Quality check passes on clean response", not qc.flagged or qc.score > 0.5)

# ── 7. Router routing ─────────────────────────────────────────────────────
print("\n[7] Command Router")
from hermes_command_router.router import run_command

report = run_command("show archived memory", source="telegram", sender="raymond")
check("Router handles archived memory command", "NOT CURRENT TRUTH" in report)

report2 = run_command("system health", source="telegram", sender="raymond")
check("Router handles normal command", len(report2) > 20)

report3 = run_command("show memory sources", source="telegram", sender="raymond")
check("Router memory sources has header", "HERMES MEMORY SOURCES" in report3)
check("Router memory sources no Executive Memory v1", "Hermes Executive Memory (v1" not in report3)

report4 = run_command("where did that answer come from", source="telegram", sender="raymond")
check("Router answer source has header", "ANSWER SOURCE" in report4)

report5 = run_command("show stale memory debug", source="telegram", sender="raymond")
check("Router stale debug has warning", "STALE MEMORY DEBUG" in report5)
check("Router stale debug no quality fallback", "wasn't able" not in report5)

# ── 8. _try_memory_command intercept ──────────────────────────────────────
print("\n[8] Live Telegram Intercept")
from telegram_bot import NexusTelegramBot

bot = NexusTelegramBot.__new__(NexusTelegramBot)
bot._current_chat_id = "sim"

reply = bot._try_memory_command("show memory sources")
check("Intercept catches memory_sources", reply is not None and "HERMES MEMORY SOURCES" in reply)

reply2 = bot._try_memory_command("where did that answer come from")
check("Intercept catches answer_source", reply2 is not None and "ANSWER SOURCE" in reply2)

reply3 = bot._try_memory_command("show archived executive memory")
check("Intercept catches archived_executive_memory", reply3 is not None and "NOT CURRENT TRUTH" in reply3)

reply4 = bot._try_memory_command("show stale memory debug")
check("Intercept catches stale_memory_debug", reply4 is not None and "STALE MEMORY DEBUG" in reply4)

reply5 = bot._try_memory_command("system health")
check("Intercept passes through non-memory", reply5 is None)

# ── 9. Executive memory direct safety ─────────────────────────────────────
print("\n[9] Executive Memory Direct Safety")
from lib.hermes_executive_memory import load_memory, load_archived_executive_memory_defaults

live = load_memory(force_refresh=True)
archived = load_archived_executive_memory_defaults()

check("Live memory has empty infrastructure_problems",
      live.get("infrastructure_problems", []) == [])
check("Live memory has operational_philosophy present",
      len(live.get("operational_philosophy", [])) > 0)
check("Live memory has DRY_RUN in philosophy",
      any("DRY_RUN" in str(p) for p in live.get("operational_philosophy", [])))
check("Archived defaults contain Ollama",
      any("Ollama" in str(i) for i in archived.get("infrastructure_problems", [])))

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Simulation complete: {PASS} passed, {FAIL} failed")
print(f"{'=' * 60}")
sys.exit(FAIL)
