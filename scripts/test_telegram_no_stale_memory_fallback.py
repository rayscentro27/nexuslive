"""
test_telegram_no_stale_memory_fallback.py
Verifies the core rule of the Memory Safety Contract:
  - Normal Telegram fallback paths must not contain stale executive memory
  - Checks all bot files for stale memory import/usage patterns
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

print("=== test_telegram_no_stale_memory_fallback ===\n")

from lib.hermes_response_quality import _fallback_data_block
from lib.hermes_active_memory_reader import (
    load_active_memory,
    build_telegram_context,
    build_context_block,
    reject_stale_memory_for_live_answer,
)

FORBIDDEN_PATTERNS = [
    "Ollama OFFLINE",
    "Beehiiv pending",
    "YouTube Studio pending",
    "OpenRouter not configured",
    "Executive Memory — as of",  # stale header without live data
    "Quality escalation fallback",
]

# 1. Active memory reader paths
ctx = build_telegram_context(max_chars=400)
for pattern in FORBIDDEN_PATTERNS:
    check(f"Telegram context has no '{pattern[:40]}'", pattern not in ctx)

block = build_context_block(max_items_per_category=3)
for pattern in FORBIDDEN_PATTERNS:
    check(f"Context block has no '{pattern[:40]}'", pattern not in block)

# 2. Quality fallback paths
for phrase in ["show it", "what do you recommend", "what is its status",
               "unknown unclear follow-up", "something random"]:
    result = _fallback_data_block(phrase,
        "Ollama OFFLINE\nBeehiiv pending\nYouTube Studio offline\nOpenRouter misconfigured")
    for pattern in FORBIDDEN_PATTERNS:
        check(f"Fallback '{phrase[:30]}' has no '{pattern[:30]}'",
              pattern not in result)

# 3. reject_stale_memory_for_live_answer gate
check("Stale Ollama blocked by gate",
      reject_stale_memory_for_live_answer("Ollama OFFLINE"))
check("Stale Beehiiv blocked by gate",
      reject_stale_memory_for_live_answer("Beehiiv pending"))
check("Clean answer passes gate",
      not reject_stale_memory_for_live_answer("The system has 3 active workers"))

# 4. Active memory contains no stale
mem = load_active_memory(force_refresh=True)
all_text = str(mem)
for marker in ["Ollama", "Beehiiv", "YouTube Studio", "OpenRouter"]:
    if marker in all_text:
        # Only check infrastructure and unfinished systems categories
        check(f"No stale '{marker}' in active memory infrastructure",
              marker not in str(mem.get("infrastructure_problems", [])))
        check(f"No stale '{marker}' in active memory unfinished",
              marker not in str(mem.get("unfinished_systems", [])))

# 5. Bot file analysis
for bot_file in ["telegram_bot.py", "hermes_claude_bot.py", "hermes_status_bot.py"]:
    path = ROOT / bot_file
    if path.exists():
        text = path.read_text()
        has_direct_exec_import = "from lib.hermes_executive_memory" in text
        check(f"{bot_file} does not import executive_memory directly",
              not has_direct_exec_import)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
