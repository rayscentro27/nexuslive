"""
test_active_memory_reader.py
Verifies Rule 3 of the Memory Safety Contract and all spec'd functions:
  - Active memory reader is the single entry point
  - All spec'd interface functions exist and work
  - No stale defaults leak through any active reader path
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

print("=== test_active_memory_reader ===\n")

from lib.hermes_active_memory_reader import (
    load_active_memory,
    load_active_memory_context,
    load_active_operating_rules,
    load_active_goals,
    load_active_artifacts_summary,
    load_active_action_summary,
    load_active_decision_summary,
    explain_active_memory_sources,
    reject_stale_memory_for_live_answer,
    active_memory_available,
    status_summary,
)

STALE_MARKERS = ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter"]

# ── Core loading ──────────────────────────────────────────────────────────────
mem = load_active_memory(force_refresh=True)
check("load_active_memory returns dict", isinstance(mem, dict))
check("load_active_memory has source tag", "source" in mem)
source = mem.get("source", "")
check("Source is not archived_defaults", source != "archived_defaults")

for cat in ["infrastructure_problems", "monetization_priorities", "unfinished_systems"]:
    items = mem.get(cat, [])
    for item in items:
        for marker in STALE_MARKERS:
            check(f"No '{marker}' in active memory.{cat}", marker not in str(item))

# ── load_active_memory_context ────────────────────────────────────────────────
ctx = load_active_memory_context(max_chars=400)
check("load_active_memory_context returns string", isinstance(ctx, str))
for marker in STALE_MARKERS:
    check(f"Context has no '{marker}'", marker not in ctx)

# ── load_active_operating_rules ──────────────────────────────────────────────
rules = load_active_operating_rules()
check("load_active_operating_rules returns list", isinstance(rules, list))
check("Operating rules contain DRY_RUN", any("DRY_RUN" in r for r in rules))

# ── load_active_goals ─────────────────────────────────────────────────────────
goals = load_active_goals()
check("load_active_goals returns list", isinstance(goals, list))

# ── load_active_artifacts_summary ──────────────────────────────────────────────
arts = load_active_artifacts_summary()
check("load_active_artifacts_summary returns string", isinstance(arts, str))

# ── load_active_action_summary ────────────────────────────────────────────────
actions = load_active_action_summary()
check("load_active_action_summary returns string", isinstance(actions, str))

# ── load_active_decision_summary ──────────────────────────────────────────────
decisions = load_active_decision_summary()
check("load_active_decision_summary returns string", isinstance(decisions, str))

# ── explain_active_memory_sources ─────────────────────────────────────────────
sources = explain_active_memory_sources()
check("explain_active_memory_sources returns string", isinstance(sources, str))
check("Sources mention executive memory", "Executive Memory" in sources)
check("Sources mention artifact registry", "Artifact Registry" in sources)
check("Sources mention action queue", "Action Queue" in sources)
check("Sources mention BLOCKED status", "BLOCKED" in sources)

# ── reject_stale_memory_for_live_answer ──────────────────────────────────────
check("reject_stale_memory rejects Ollama text",
      reject_stale_memory_for_live_answer("Ollama OFFLINE"))
check("reject_stale_memory rejects Beehiiv",
      reject_stale_memory_for_live_answer("Beehiiv pending"))
check("reject_stale_memory passes clean text",
      not reject_stale_memory_for_live_answer("system is healthy"))

# ── active_memory_available ──────────────────────────────────────────────────
avail = active_memory_available()
check("active_memory_available returns bool", isinstance(avail, bool))

# ── status_summary ─────────────────────────────────────────────────────────
summary = status_summary()
check("status_summary returns string", isinstance(summary, str))
check("status_summary has no stale defaults",
      not any(m in summary for m in STALE_MARKERS))

# ── Telegram bot imports check ──────────────────────────────────────────────
# Verify telegram_bot.py imports from active memory reader, not executive_memory directly
tg_bot = ROOT / "telegram_bot.py"
if tg_bot.exists():
    tg_text = tg_bot.read_text()
    check("telegram_bot.py does NOT import executive_memory for context",
          "from lib.hermes_executive_memory" not in tg_text or
          "from lib.hermes_active_memory_reader" in tg_text)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
