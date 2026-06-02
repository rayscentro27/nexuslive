"""
test_daily_operating_cycle_top_revenue_move.py
Tests: format_top_revenue_move uses actual content/monetization assets, not generic text.
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


print("=== test_daily_operating_cycle_top_revenue_move ===\n")

from lib.hermes_daily_operating_cycle import (
    build_daily_operating_plan,
    format_top_revenue_move,
    select_top_revenue_action,
    load_daily_operating_inputs,
)

# ── format_top_revenue_move: structure ────────────────────────────────────
print("-- format_top_revenue_move: structure --")
plan = build_daily_operating_plan()
resp = format_top_revenue_move(plan)

check("non-empty",                                  bool(resp))
check("starts with TODAY'S TOP MONEY MOVE",         resp.startswith("TODAY'S TOP MONEY MOVE"))
check("contains date",                              plan["date"] in resp)
check("contains 'Best move:'",                      "Best move:" in resp)
check("contains 'Why this is first:'",              "Why this is first:" in resp)
check("contains 'Asset involved:'",                 "Asset involved:" in resp)
check("contains 'Next internal step:'",             "Next internal step:" in resp)
check("contains 'Approval needed before:'",         "Approval needed before:" in resp)
check("contains 'Evidence:'",                       "Evidence:" in resp)
check("mentions approval requirement",
      "approval" in resp.lower() or "ray" in resp.lower())

# ── uses actual content asset ─────────────────────────────────────────────
print("\n-- uses actual content/monetization assets --")
inputs = load_daily_operating_inputs()
rev = select_top_revenue_action(inputs)
check("top_revenue: has asset info",     bool(rev.get("action")))
check("top_revenue: evidence not empty", bool(rev.get("evidence")))
check("top_revenue: approval_needed",    "approval" in rev.get("approval_needed", "").lower())

# Verify format uses the asset from the plan
if plan.get("top_revenue", {}).get("asset_name"):
    asset_name = plan["top_revenue"]["asset_name"]
    check("asset name appears in response",
          asset_name[:20] in resp)
else:
    check("no asset: response still structured", "Asset involved:" in resp)

# ── no unsafe actions ─────────────────────────────────────────────────────
print("\n-- no unsafe actions in revenue move --")
UNSAFE_ACTIONS = ["publish now", "send to subscribers", "deploy to production",
                  "spend money", "execute live trade", "apply to affiliate"]
for unsafe in UNSAFE_ACTIONS:
    check(f"no '{unsafe}' in response",
          unsafe.lower() not in resp.lower())

# ── no evidence dump ──────────────────────────────────────────────────────
print("\n-- no evidence dump --")
DUMP_MARKERS = ["artifact_inventory", "handoff dump", "Executive Memory",
                "I can answer from verified", "═══", "HERMES REPORT"]
check("no evidence dump",
      not any(m in resp for m in DUMP_MARKERS))

# ── routing ────────────────────────────────────────────────────────────────
print("\n-- routing: daily_top_revenue_move intent --")
from hermes_command_router.router import run_command
from hermes_command_router.intake import classify_intent

for phrase in [
    "show today's top revenue move",
    "show today's top money move",
    "top revenue move",
    "top money move today",
    "today's top money move",
]:
    intent, _, _ = classify_intent(phrase)
    check(f"classify_intent({phrase!r}) == daily_top_revenue_move",
          intent == "daily_top_revenue_move")
    resp_r = run_command(phrase, source="cli")
    check(f"'{phrase}': non-empty",                    bool(resp_r))
    check(f"'{phrase}': TODAY'S TOP MONEY MOVE",       "TODAY'S TOP MONEY MOVE" in resp_r)
    check(f"'{phrase}': no evidence dump",
          not any(m in resp_r for m in DUMP_MARKERS))

# ── format with no plan argument ─────────────────────────────────────────
print("\n-- format_top_revenue_move with no plan argument --")
resp_no_plan = format_top_revenue_move()
check("works without plan argument",       bool(resp_no_plan))
check("TODAY'S TOP MONEY MOVE header",     "TODAY'S TOP MONEY MOVE" in resp_no_plan)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(FAIL)
