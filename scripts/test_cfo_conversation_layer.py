"""
test_cfo_conversation_layer.py
Tests: core CFO conversation layer functions exist and return expected types.
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


print("=== test_cfo_conversation_layer ===\n")

from lib.hermes_cfo_conversation_layer import (
    detect_cfo_conversation_need,
    classify_cfo_conversation,
    build_cfo_context,
    separate_knowns_unknowns,
    select_cfo_response_strategy,
    build_cfo_response,
    create_scout_tasks_for_unknowns,
    create_implementation_prompt_if_needed,
    format_cfo_response,
    save_cfo_decision_candidate,
    SAFETY_BOUNDARY,
    CFO_CATEGORIES,
)

# ── Module constants ──────────────────────────────────────────────────────────
print("-- module constants --")
check("SAFETY_BOUNDARY is non-empty", bool(SAFETY_BOUNDARY))
check("SAFETY_BOUNDARY mentions Ray approval",
      "ray approval" in SAFETY_BOUNDARY.lower() or "explicit ray" in SAFETY_BOUNDARY.lower())
check("CFO_CATEGORIES is dict", isinstance(CFO_CATEGORIES, dict))
check("CFO_CATEGORIES has required categories",
      all(k in CFO_CATEGORIES for k in [
          "strategic_concern", "hermes_behavior_feedback", "monetization_strategy",
          "implementation_planning", "unknown_answer"
      ]))

# ── detect_cfo_conversation_need ─────────────────────────────────────────────
print("\n-- detect_cfo_conversation_need --")
check("concern message → True",
      detect_cfo_conversation_need("I am worried Hermes is becoming a command bot") is True)
check("strategic question → True",
      detect_cfo_conversation_need("What should we do about our revenue strategy?") is True)
check("empty → False", detect_cfo_conversation_need("") is False)
check("short → False", detect_cfo_conversation_need("ok") is False)
check("exact command → False", detect_cfo_conversation_need("show revenue asset packet") is False)
check("'run daily' command → False", detect_cfo_conversation_need("run daily operating cycle") is False)

# ── classify_cfo_conversation ─────────────────────────────────────────────────
print("\n-- classify_cfo_conversation --")
check("behavior feedback classified correctly",
      classify_cfo_conversation("I don't know what ChatGPT has that Hermes doesn't") == "hermes_behavior_feedback")
check("monetization classified correctly",
      classify_cfo_conversation("How do we make $1000 a week from affiliate revenue?") == "monetization_strategy")
check("implementation classified correctly",
      classify_cfo_conversation("Give me a prompt to implement this feature") == "implementation_planning")
check("returns valid category",
      classify_cfo_conversation("something random") in CFO_CATEGORIES)

# ── build_cfo_context ─────────────────────────────────────────────────────────
print("\n-- build_cfo_context --")
ctx = build_cfo_context("I am worried about revenue")
check("returns dict", isinstance(ctx, dict))
check("has category", "category" in ctx)
check("has memory_v2_active", "memory_v2_active" in ctx)
check("has approval_queue_count", "approval_queue_count" in ctx)

# ── separate_knowns_unknowns ──────────────────────────────────────────────────
print("\n-- separate_knowns_unknowns --")
ctx2 = {"category": "hermes_behavior_feedback"}
ku = separate_knowns_unknowns("Hermes feels like a command bot", ctx2)
check("returns dict with knowns and unknowns", "knowns" in ku and "unknowns" in ku)
check("knowns is list", isinstance(ku["knowns"], list))
check("unknowns is list", isinstance(ku["unknowns"], list))
check("has at least one known for behavior feedback", len(ku["knowns"]) >= 1)

# ── build_cfo_response ────────────────────────────────────────────────────────
print("\n-- build_cfo_response --")
msg = "I am worried Hermes is becoming a command bot and not a CFO"
ctx3 = build_cfo_context(msg)
resp = build_cfo_response(msg, ctx3)
check("returns dict", isinstance(resp, dict))
check("has strategy", "strategy" in resp)
check("has safety_boundary", "safety_boundary" in resp)
check("safety_boundary == SAFETY_BOUNDARY", resp["safety_boundary"] == SAFETY_BOUNDARY)

# ── format_cfo_response ───────────────────────────────────────────────────────
print("\n-- format_cfo_response --")
formatted = format_cfo_response(resp)
check("returns str", isinstance(formatted, str))
check("starts with 'RAY'", formatted.startswith("RAY"))
check("has 'Approval boundary'", "Approval boundary" in formatted)
check("has SAFETY_BOUNDARY text", "without explicit Ray approval" in formatted
      or "ray approval" in formatted.lower())

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
