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

# ── 2. Archived memory command ────────────────────────────────────────────
print("\n[2] Archived Memory Command")
from hermes_command_router.intake import classify_intent
from hermes_command_router.router import _run_archived_executive_memory

for phrase in ["show archived memory", "load archived defaults", "what were the old defaults"]:
    intent, _, _ = classify_intent(phrase)
    check(f"Intent for '{phrase}' is archived_executive_memory",
          intent == "archived_executive_memory")

status, evidence, rec = _run_archived_executive_memory()
check("Archived memory handler returns OK", status == "healthy")
check("Archived evidence references stale defaults",
      any("Ollama" in e for e in evidence))

# Non-archived phrase should NOT match
intent, _, _ = classify_intent("system health")
check("Non-archived phrase does not trigger intent",
      intent != "archived_executive_memory")

# ── 3. Quality escalation fallback ────────────────────────────────────────
print("\n[3] Quality Escalation Fallback")
from lib.hermes_response_quality import _fallback_data_block, escalate, quality_check

# The fallback should never dump stale data
fake_stale = "Ollama OFFLINE\nBeehiiv pending\nYouTube Studio offline"
result = _fallback_data_block("something random", fake_stale)
check("Fallback does not contain Ollama", "Ollama" not in result)
check("Fallback does not contain Beehiiv", "Beehiiv" not in result)
check("Fallback returns actionable guidance",
      "specific" in result.lower() or "nexus ceo briefing" in result.lower())

# Quality check should be clean
qc = quality_check("This is a great question about system status. Let me check.", chat_id="sim_test")
check("Quality check passes on clean response", not qc.flagged or qc.score > 0.5)

# ── 4. Router command routing ─────────────────────────────────────────────
print("\n[4] Command Router")
from hermes_command_router.router import run_command

# Send an archived memory command through the router
report = run_command("show archived memory", source="telegram", sender="raymond")
check("Router handles archived memory command", "Archived" in report or "archived" in report.lower() or "archived_executive_memory" in report)

# Normal command should work fine
report2 = run_command("system health", source="telegram", sender="raymond")
check("Router handles normal command", len(report2) > 20)

# ── 5. Executive memory direct safety ─────────────────────────────────────
print("\n[5] Executive Memory Direct Safety")
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
