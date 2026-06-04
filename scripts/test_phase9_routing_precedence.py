"""test_phase9_routing_precedence.py — handle_inbound_message follows the Phase 9 precedence chain."""
import sys
from pathlib import Path

PASS = 0
FAIL = 0


def check(label, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {label}")


source = Path("telegram_bot.py").read_text(encoding="utf-8")
order = [
    "text = _normalize_telegram_command(text) if text else text",
    "memory_reply = self._try_memory_command(normalized_key or normalized)",
    "handle_cfo_shadow_command",
    "if _should_8c(text):",
    "_p7c_intent = _p7c_classify(normalized)",
    "if intent in LEARNING_LOOP_INTENTS:",
    "if intent in APPROVAL_EXACT_INTENTS:",
    "if intent in DAILY_EXACT_INTENTS:",
    "if normalized_key in LAUNCH_PACKET_REVIEW_PHRASES:",
    "if intent in RESEARCH_EXACT_INTENTS:",
    "route = self.classify_message_route(text)",
    "if route == \"chat\":",
    "router = TelegramRouter(",
]

positions = []
for snippet in order:
    pos = source.find(snippet)
    check(f"snippet present: {snippet}", pos >= 0)
    positions.append(pos)

valid_positions = [p for p in positions if p >= 0]
check("snippets appear in ascending order", valid_positions == sorted(valid_positions))
check("memory command pre-check before normalization removed", "# ── Memory command pre-check: route before TelegramRouter / LLM ──────" not in source)

print(f"\nPhase 9 routing precedence: {PASS} pass, {FAIL} fail")
if FAIL:
    sys.exit(1)
