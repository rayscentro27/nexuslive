"""
debug_phase7_cfo_routing.py
Phase 7A — Diagnose why 5 natural-language messages miss the CFO layer.

Traces each test message through: classify_intent → SAFE_REPEATABLE_MEMORY_INTENTS
→ detect_cfo_conversation_need → is_high_priority_cfo_phrase → run_command output.
Writes docs/reports/strategy/phase7a_cfo_routing_debug_<ts>.md
"""
import sys, os
from datetime import datetime
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

TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def _expected_matches(actual: str, expected: str) -> bool:
    return any(word.upper() in actual.upper() for word in expected.upper().split()
               if len(word) > 3)


# ── Test messages ─────────────────────────────────────────────────────────────
MESSAGES = [
    # Expected to fail before Phase 7A fix
    ("I am worried Hermes is becoming a command bot and not a CFO.",
     "RAY, I UNDERSTAND THE CONCERN"),
    ("What should we do about that?",
     "CFO strategic thread (not quality fallback)"),
    ("I don't know the answer, can your scouts figure it out?",
     "I DON'T HAVE VERIFIED EVIDENCE YET"),
    ("Can Hermes find the best affiliate offer for the funding checklist?",
     "Scout dispatch to affiliate_monetization_scout"),
    ("create a prompt for Claude to fix this",
     "IMPLEMENTATION PROMPT"),
    # Expected to work already
    ("show research queue", "RESEARCH QUEUE"),
    ("show scout assignments", "SCOUT ASSIGNMENTS"),
    ("what are you still trying to figure out", "UNRESOLVED QUESTIONS"),
    ("run daily operating cycle", "TODAY'S NEXUS PLAN"),
    ("show approval queue", "APPROVAL QUEUE"),
    ("show memory v2 primary status", "MEMORY V2 PRIMARY"),
    ("show revenue asset packet", "REVENUE ASSET PACKET"),
]

# ── Load routing components ───────────────────────────────────────────────────
from hermes_command_router.intake import classify_intent
from hermes_command_router.router import run_command

# Load CFO detection — may or may not have is_high_priority_cfo_phrase yet
try:
    from lib.hermes_cfo_conversation_layer import (
        detect_cfo_conversation_need,
        classify_cfo_conversation,
    )
    _cfo_available = True
except ImportError as _e:
    _cfo_available = False
    print(f"WARNING: cfo layer import failed: {_e}")

try:
    from lib.hermes_cfo_conversation_layer import is_high_priority_cfo_phrase
    _high_priority_available = True
except ImportError:
    _high_priority_available = False
    def is_high_priority_cfo_phrase(msg: str) -> bool:
        return False

SAFE_REPEATABLE_MEMORY_INTENTS = frozenset({
    "small_talk", "date_time_question", "unknown_handling",
    "memory_sources", "memory_sources_again", "active_operating_rules",
    "memory_v2_preview", "memory_v2_compare", "memory_v2_rules",
    "memory_v2_status", "memory_v2_shadow_status", "memory_v2_live_check",
    "memory_v2_primary_status", "lesson_record", "lesson_pending",
    "lesson_active", "lesson_approve_all", "lesson_approve",
    "lesson_reject", "lesson_deprecate", "lesson_learned",
    "lesson_source", "lesson_gap_generate",
    "daily_operating_cycle", "daily_approval_needed", "daily_continue_while_out",
    "daily_top_revenue_move", "daily_blockers", "thirty_day_revenue_plan",
    "show_revenue_asset_packet", "rescore_after_fixes",
    "fix_revenue_packet_assets", "show_asset_fix_report",
    "show_research_queue", "show_scout_assignments", "show_unresolved_questions",
    "create_implementation_prompt", "show_cfo_notes", "save_cfo_decision",
    "show_approval_queue", "approve_all_pending", "reject_all_pending",
    "knowledge_gap_review",
})

# ── Debug each message ────────────────────────────────────────────────────────
rows = []

print(f"\n=== Phase 7A CFO Routing Debug — {TS} ===\n")

for msg, expected in MESSAGES:
    row = {"message": msg, "expected": expected}

    normalized = msg.strip().lower()

    # Step 1: classify_intent
    try:
        result_tuple = classify_intent(msg)
        intent = result_tuple[0] if result_tuple else "unknown"
        raw_conf = result_tuple[1] if len(result_tuple) > 1 else "?"
        confidence = raw_conf if raw_conf is not None else "?"
    except Exception as exc:
        intent = f"ERROR:{exc!s:.60}"
        confidence = "?"
    row["intent"] = intent
    row["confidence"] = confidence

    # Step 2: Would _try_memory_command catch it?
    row["memory_command_catch"] = intent in SAFE_REPEATABLE_MEMORY_INTENTS

    # Step 3: CFO detection
    if _cfo_available:
        row["detect_cfo"] = detect_cfo_conversation_need(normalized)
        row["cfo_category"] = classify_cfo_conversation(normalized)
    else:
        row["detect_cfo"] = False
        row["cfo_category"] = "unavailable"

    row["high_priority_phrase"] = is_high_priority_cfo_phrase(normalized)
    row["would_reach_cfo"] = row["memory_command_catch"] or row["detect_cfo"] or row["high_priority_phrase"]

    # Step 4: run_command output
    try:
        result = run_command(msg) or ""
        row["output_start"] = result[:200].replace("\n", " ")
        # Detect what kind of response we got
        r = result.upper()
        if r.startswith("RAY, I UNDERSTAND"):
            row["actual_handler"] = "CFO_STANDARD"
        elif r.startswith("I DON'T HAVE VERIFIED"):
            row["actual_handler"] = "CFO_UNKNOWN_DISPATCH"
        elif r.startswith("IMPLEMENTATION PROMPT"):
            row["actual_handler"] = "CFO_IMPL_PROMPT"
        elif "RESEARCH QUEUE" in r[:100]:
            row["actual_handler"] = "RESEARCH_QUEUE_CMD"
        elif "SCOUT ASSIGNMENTS" in r[:100]:
            row["actual_handler"] = "SCOUT_ASSIGN_CMD"
        elif "UNRESOLVED QUESTIONS" in r[:100]:
            row["actual_handler"] = "UNRESOLVED_CMD"
        elif "NEXUS PLAN" in r[:100] or "TODAY'S NEXUS" in r[:100]:
            row["actual_handler"] = "DAILY_CYCLE"
        elif "APPROVAL QUEUE" in r[:100]:
            row["actual_handler"] = "APPROVAL_QUEUE"
        elif "REVENUE ASSET PACKET" in r[:100]:
            row["actual_handler"] = "REVENUE_PACKET"
        elif "MEMORY V2" in r[:100] or "PRIMARY MEMORY" in r[:100]:
            row["actual_handler"] = "MEMORY_V2"
        elif "STRATEGIC RESPONSE" in r[:100] or "FOLLOW-UP" in r[:100]:
            row["actual_handler"] = "CFO_FOLLOWUP"
        else:
            row["actual_handler"] = f"OTHER:{result[:60].replace(chr(10),' ')}"
        row["error"] = None
    except Exception as exc:
        row["output_start"] = ""
        row["actual_handler"] = f"ERROR"
        row["error"] = str(exc)[:120]

    rows.append(row)

    status = "PASS" if _expected_matches(row.get("actual_handler", ""), expected) else "FAIL"
    print(f"[{status}] {msg[:55]!r}")
    print(f"       intent={row['intent']!r}  memory_catch={row['memory_command_catch']}")
    print(f"       detect_cfo={row['detect_cfo']}  high_priority={row['high_priority_phrase']}")
    print(f"       actual={row['actual_handler']!r}")
    print(f"       expected contains: {expected!r}")
    print()


# ── Write report ──────────────────────────────────────────────────────────────
REPORT_DIR = ROOT / "docs" / "reports" / "strategy"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
report_path = REPORT_DIR / f"phase7a_cfo_routing_debug_{TS}.md"

lines = [
    f"# Phase 7A CFO Routing Debug\n",
    f"**Timestamp:** {TS}  \n",
    f"**Purpose:** Diagnose CFO routing failures before Phase 7A fix\n",
    f"\n---\n",
    f"\n## Summary\n",
    f"\n| # | Message (truncated) | Intent | Memory? | detect_cfo | high_priority | actual_handler | PASS? |\n",
    f"|---|---|---|---|---|---|---|---|\n",
]
for i, row in enumerate(rows, 1):
    expected = MESSAGES[i - 1][1]
    ok = "✓" if _expected_matches(row["actual_handler"], expected) else "✗"
    lines.append(
        f"| {i} | {row['message'][:45]!r} | `{row['intent']}` | {row['memory_command_catch']} "
        f"| {row['detect_cfo']} | {row['high_priority_phrase']} "
        f"| `{row['actual_handler']}` | {ok} |\n"
    )

lines += [
    f"\n---\n",
    f"\n## Root Cause\n",
    f"\n`handle_inbound_message()` routing order:\n",
    f"1. `_try_memory_command()` — runs `run_command` only for `SAFE_REPEATABLE_MEMORY_INTENTS`\n",
    f"2. `continuity` dict — exact phrase matching (~80 entries)\n",
    f"3. Swarm followup + agent list\n",
    f"4. `TelegramRouter.route_incoming_message()` → `_conversational_reply()` LLM synthesis\n",
    f"\n**CFO layer** is at the END of `run_command()` but `run_command()` is never reached\n",
    f"for natural-language messages. They go to `_conversational_reply()` which produces\n",
    f"evidence dumps or quality fallbacks.\n",
    f"\n## Fix (Phase 7A)\n",
    f"\nInsert CFO intercept BEFORE `TelegramRouter` call in `handle_inbound_message()`:\n",
    f"```python\n",
    f"# After continuity dict, before TelegramRouter:\n",
    f"from lib.hermes_cfo_conversation_layer import detect_cfo_conversation_need, is_high_priority_cfo_phrase\n",
    f"if detect_cfo_conversation_need(normalized) or is_high_priority_cfo_phrase(normalized):\n",
    f"    result = _run_command(text, source='telegram')\n",
    f"    if result:\n",
    f"        return result\n",
    f"```\n",
]

report_path.write_text("".join(lines))
print(f"\nReport written: {report_path.relative_to(ROOT)}")
